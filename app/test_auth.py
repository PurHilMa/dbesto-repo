import http.cookiejar
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
import time

import auth
from server import Handler, LocalServer

class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        auth.DATABASE=Path(cls.temp.name)/'test.sqlite3'
        auth.init()
        cls.server=LocalServer(('127.0.0.1',0),Handler)
        cls.url='http://127.0.0.1:'+str(cls.server.server_port)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.temp.cleanup()

    def client(self):
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self,client,path,data=None,csrf=''):
        request=urllib.request.Request(self.url+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json','X-CSRF-Token':csrf})
        try:
            response=client.open(request)
        except urllib.error.HTTPError as error:
            response=error
        with response:
            body=response.read()
            return response.status,json.loads(body) if response.headers.get_content_type()=='application/json' else body

    def login(self,name):
        client=self.client();status,result=self.call(client,'/api/login',dict(username=name,password='EbmDemo!2026'))
        self.assertEqual(status,200);return client,result['csrf']

    def test_unauthenticated_and_private_files(self):
        self.assertEqual(self.call(self.client(),'/api/outlets')[0],401)
        for path in ['/auth.py','/server.py','/../.runtime/ebm.sqlite3','/server-output.log']:
            self.assertEqual(self.call(self.client(),path)[0],404)

    def test_cashier_scope_and_permission(self):
        client,csrf=self.login('kasir')
        rows=self.call(client,'/api/outlets')[1]['data']
        self.assertEqual([o['id'] for o in rows],['EBM-001'])
        self.assertNotIn('sales',rows[0])
        self.assertEqual(self.call(client,'/api/users')[0],403)
        self.assertEqual(self.call(client,'/api/reviews')[0],403)
        sale=dict(outlet='EBM-002',quantity=1,cash=30000)
        self.assertEqual(self.call(client,'/api/events',sale,csrf)[0],403)
        sale['outlet']='EBM-001'
        self.assertEqual(self.call(client,'/api/events',sale)[0],403)
        status,result=self.call(client,'/api/events',sale,csrf)
        self.assertEqual(status,200);self.assertEqual(result['data']['actor'],'kasir')

    def test_spv_review_and_ceo_readonly(self):
        client,csrf=self.login('spv')
        review=dict(outlet='EBM-003',finding='Penyebab contoh cukup panjang',action='Tindakan contoh cukup panjang')
        self.assertEqual(self.call(client,'/api/reviews',review,csrf)[0],403)
        review['outlet']='EBM-002'
        self.assertEqual(self.call(client,'/api/reviews',review,csrf)[0],200)
        ceo,token=self.login('ceo')
        self.assertEqual(self.call(ceo,'/api/reviews')[0],200)
        self.assertEqual(self.call(ceo,'/api/reviews',review,token)[0],403)

    def test_revocation_and_logout(self):
        user,token=self.login('acm');admin,csrf=self.login('admin')
        self.assertEqual(self.call(admin,'/api/users',dict(username='acm',role='ACM',scope=['EBM-001'],active=False),csrf)[0],200)
        self.assertEqual(self.call(user,'/api/session')[0],401)
        self.call(admin,'/api/users',dict(username='acm',role='ACM',scope=['EBM-001','EBM-002'],active=True),csrf)
        self.assertEqual(self.call(admin,'/api/logout',{},csrf)[0],200)
        self.assertEqual(self.call(admin,'/api/users')[0],401)

    def test_password_change_revokes_all_sessions(self):
        one,csrf=self.login('finance');two,_=self.login('finance')
        self.assertEqual(self.call(one,'/api/password',dict(current='EbmDemo!2026',password='ChangedDemo!2026'),csrf)[0],200)
        self.assertEqual(self.call(two,'/api/session')[0],401)
        self.assertEqual(self.call(one,'/api/session')[0],401)

    def test_lockout(self):
        client=self.client()
        for _ in range(5):
            self.assertEqual(self.call(client,'/api/login',dict(username='gudang',password='wrong'))[0],401)
        self.assertEqual(self.call(client,'/api/login',dict(username='gudang',password='EbmDemo!2026'))[0],429)

    def test_expiry(self):
        client,_=self.login('mgr')
        with auth.connect() as c:
            c.execute('UPDATE sessions SET last_seen=0 WHERE username=?',('mgr',))
        self.assertEqual(self.call(client,'/api/session')[0],401)

    def test_offline_receipt_idempotency_and_scope(self):
        client,csrf=self.login('kasir');spv,_=self.login('spv')
        status,result=self.call(client,'/api/offline/lease',dict(device='device-test-001'),csrf)
        self.assertEqual(status,200);lease=result['lease']
        self.assertEqual(lease['scope'],['EBM-001'])
        before=self.call(spv,'/api/outlets')[1]['data'][0]
        event=dict(id='offline-event-001',outlet='EBM-001',quantity=2,cash=100000,amount=60000,businessDate='2026-10-31',occurredAt=time.time(),createdAt='2026-11-01T00:00:00Z')
        payload=dict(lease=lease,event=event)
        first=self.call(client,'/api/offline/sync',payload,csrf)
        self.assertEqual(first[0],200);self.assertEqual(first[1]['status'],'RECEIVED')
        again=self.call(client,'/api/offline/sync',payload,csrf)
        self.assertTrue(again[1]['duplicate'])
        after=self.call(spv,'/api/outlets')[1]['data'][0]
        self.assertEqual(after['sales']-before['sales'],60000)
        self.assertEqual(after['tc']-before['tc'],1)
        changed=dict(event,quantity=3,amount=90000)
        self.assertEqual(self.call(client,'/api/offline/sync',dict(lease=lease,event=changed),csrf)[0],409)
        forbidden=dict(event,id='offline-event-002',outlet='EBM-003')
        result=self.call(client,'/api/offline/sync',dict(lease=lease,event=forbidden),csrf)[1]
        self.assertEqual(result['status'],'EXCEPTION')
        wrong=dict(lease,device='other-device')
        self.assertEqual(self.call(client,'/api/offline/sync',dict(lease=wrong,event=event),csrf)[0],403)
        ceo,ceo_csrf=self.login('ceo')
        self.assertEqual(self.call(ceo,'/api/offline/lease',dict(device='device-test-002'),ceo_csrf)[0],403)

    def test_offline_revoked_and_expired_preserved(self):
        client,csrf=self.login('kasir')
        lease=self.call(client,'/api/offline/lease',dict(device='device-test-003'),csrf)[1]['lease']
        with auth.connect() as c:c.execute('UPDATE offline_leases SET expires=0 WHERE id=?',(lease['id'],))
        event=dict(id='offline-expired-001',outlet='EBM-001',quantity=1,cash=30000,amount=30000,businessDate='2026-10-31',occurredAt=time.time())
        self.assertEqual(self.call(client,'/api/offline/sync',dict(lease=lease,event=event),csrf)[1]['status'],'EXCEPTION')
        lease=self.call(client,'/api/offline/lease',dict(device='device-test-003'),csrf)[1]['lease']
        admin,admin_csrf=self.login('admin')
        self.call(admin,'/api/users',dict(username='kasir',role='SPV',scope=['EBM-001'],active=True),admin_csrf)
        client,csrf=self.login('kasir')
        event['id']='offline-revoked-001'
        result=self.call(client,'/api/offline/sync',dict(lease=lease,event=event),csrf)[1]
        self.assertEqual(result['status'],'EXCEPTION')
        with auth.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM offline_inbox WHERE event_id=?',(event['id'],)).fetchone()[0],1)
        self.call(admin,'/api/users',dict(username='kasir',role='KASIR',scope=['EBM-001'],active=True),admin_csrf)

    def test_assistant_scope_freshness_and_permissions(self):
        spv,csrf=self.login('spv')
        def ask(client,token,q):
            status,result=self.call(client,'/api/assistant',dict(question=q,businessDate='2026-10-31'),token)
            self.assertEqual(status,200);return result['answer']
        text=ask(spv,csrf,'Ringkas omset')
        self.assertIn('Resto Contoh A',text);self.assertNotIn('Resto Contoh C',text)
        self.assertIn('cakupan akses',ask(spv,csrf,'Omset EBM-003'))
        cashier,token=self.login('kasir')
        self.assertIn('tidak mempunyai izin',ask(cashier,token,'Review SPV'))
        self.assertIn('belum tersedia',ask(spv,csrf,'Berapa NPM bulan ini?'))
        self.assertEqual(self.call(self.client(),'/api/assistant',dict(question='omset'))[0],401)
        self.assertEqual(self.call(spv,'/api/assistant',dict(question='omset'))[0],403)
        before=ask(spv,csrf,'Omset resto A')
        self.call(cashier,'/api/events',dict(outlet='EBM-001',quantity=1,cash=30000),token)
        after=ask(spv,csrf,'Omset resto A')
        self.assertNotEqual(before,after)

    def test_cashier_updates_dashboard_by_outlet_and_date(self):
        cashier,csrf=self.login('kasir');spv,_=self.login('spv')
        path='/api/outlets?date=2026-10-31'
        before=self.call(spv,path)[1]['data']
        status,event=self.call(cashier,'/api/events',dict(outlet='EBM-001',quantity=3,cash=100000,businessDate='2026-10-31'),csrf)
        self.assertEqual(status,200)
        after=self.call(spv,path)[1]['data']
        self.assertEqual(after[0]['sales']-before[0]['sales'],90000)
        self.assertEqual(after[0]['tc']-before[0]['tc'],1)
        self.assertEqual(after[1],before[1])
        self.assertEqual(self.call(spv,path)[1]['data'],after)
        other=self.call(spv,'/api/outlets?date=2026-11-02')[1]['data']
        self.assertEqual(other[0]['sales'],0)
        self.assertEqual(other[0]['tc'],0)
        self.assertEqual(self.call(cashier,'/api/events',dict(outlet='EBM-001',quantity=1,cash=30000,businessDate='bad'),csrf)[0],400)

if __name__=='__main__':
    unittest.main()
