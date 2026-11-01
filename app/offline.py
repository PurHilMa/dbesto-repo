"""Server side offline permits and idempotent durable receipt inbox."""
import hashlib
import json
import secrets
import time

def init(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS offline_leases(id TEXT PRIMARY KEY,token_hash TEXT NOT NULL,username TEXT NOT NULL,device TEXT NOT NULL,scope TEXT NOT NULL,issued REAL NOT NULL,expires REAL NOT NULL,revoked INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS offline_inbox(device TEXT NOT NULL,event_id TEXT NOT NULL,username TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,reason TEXT NOT NULL,received REAL NOT NULL,PRIMARY KEY(device,event_id));
    ''')

def revoke(c,username):
    c.execute('UPDATE offline_leases SET revoked=1 WHERE username=?',(username,))

def dispatch(c,user,path,data,auth):
    if path=='/api/offline/lease':
        auth.require(user,'pos')
        device=data.get('device','')
        if not isinstance(device,str) or not 10<=len(device)<=100:
            raise auth.APIError(400,'Identitas perangkat tidak valid.')
        raw=secrets.token_urlsafe(32);identifier=secrets.token_hex(16);now=time.time()
        scope=[o['id'] for o in auth.OUTLETS if auth.allowed(user,o['id'])]
        if not scope:raise auth.APIError(403,'Akun tidak memiliki outlet POS.')
        c.execute('INSERT INTO offline_leases VALUES(?,?,?,?,?,?,?,0)',(identifier,hashlib.sha256(raw.encode()).hexdigest(),user['username'],device,json.dumps(scope),now,now+28800))
        auth.log(c,user['username'],'OFFLINE_LEASE',device)
        return dict(lease=dict(id=identifier,token=raw,device=device,username=user['username'],scope=scope,issued=now,expires=now+28800,unitPrice=30000),outlets=[dict(id=o['id'],name=o['name']) for o in auth.OUTLETS if o['id'] in scope]),None
    if path!='/api/offline/sync':raise auth.APIError(404,'Endpoint tidak tersedia.')
    event=data.get('event');permit=data.get('lease',{})
    if not isinstance(event,dict) or not isinstance(permit,dict):raise auth.APIError(400,'Format event tidak valid.')
    identifier=event.get('id');device=permit.get('device');token=permit.get('token','')
    if not isinstance(identifier,str) or not 10<=len(identifier)<=100 or not isinstance(device,str) or not isinstance(token,str):raise auth.APIError(400,'Identitas event tidak valid.')
    lease=c.execute('SELECT * FROM offline_leases WHERE id=?',(permit.get('id'),)).fetchone()
    if not lease or lease['device']!=device or lease['username']!=user['username'] or not secrets.compare_digest(lease['token_hash'],hashlib.sha256(token.encode()).hexdigest()):
        raise auth.APIError(403,'Izin offline tidak sesuai pengguna/perangkat.')
    payload=json.dumps(event,sort_keys=True,separators=(',',':'))
    previous=c.execute('SELECT * FROM offline_inbox WHERE device=? AND event_id=?',(device,identifier)).fetchone()
    if previous:
        if previous['payload']!=payload:raise auth.APIError(409,'ID transaksi sama mempunyai isi berbeda. Bukti asli dipertahankan.')
        return dict(id=identifier,status=previous['status'],reason=previous['reason'],duplicate=True,receivedAt=previous['received']),None
    reason='';qty=event.get('quantity');cash=event.get('cash');outlet=event.get('outlet');occurred=event.get('occurredAt')
    if lease['revoked']:reason='Izin offline dicabut; perlu pemeriksaan.'
    elif 'pos' not in auth.ROLES[user['role']] or not auth.allowed(user,outlet):reason='Hak POS atau cakupan outlet berubah; perlu pemeriksaan.'
    elif outlet not in json.loads(lease['scope']):reason='Outlet di luar izin offline.'
    elif time.time()>lease['expires']:reason='Sinkronisasi melewati masa izin; perlu pemeriksaan.'
    elif type(occurred) not in (int,float) or not lease['issued']-60<=occurred<=min(lease['expires'],time.time()+60):reason='Waktu transaksi di luar masa izin.'
    elif type(qty)!=int or not 1<=qty<=100 or type(cash)!=int or not qty*30000<=cash<=1000000000 or event.get('amount')!=qty*30000:reason='Jumlah atau nilai transaksi tidak valid.'
    else:
        try:auth.business_date(event.get('businessDate'))
        except auth.APIError:reason='Tanggal bisnis tidak valid.'
    now=time.time();status='EXCEPTION' if reason else 'RECEIVED'
    c.execute('INSERT INTO offline_inbox VALUES(?,?,?,?,?,?,?)',(device,identifier,user['username'],payload,status,reason,now))
    if not reason:
        value=dict(event,actor=user['username'],device=device,status='LOCAL_PENDING',createdAt=event.get('createdAt'),source='OFFLINE_SYNC')
        record_id='offline:'+device+':'+identifier
        value['id']=record_id
        c.execute('INSERT INTO records VALUES(?,?,?,?)',('events',record_id,outlet,json.dumps(value)))
    auth.log(c,user['username'],'OFFLINE_'+status,identifier)
    return dict(id=identifier,status=status,reason=reason,duplicate=False,receivedAt=now),None
