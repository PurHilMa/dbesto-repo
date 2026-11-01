"""Local simulation identity, scoped permissions and durable records."""
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
import assistant
import offline
from pathlib import Path
from datetime import date
from urllib.parse import urlsplit, parse_qs

DEMO_DATE = '2026-10-31'

def business_date(value):
    try:
        if not isinstance(value,str) or date.fromisoformat(value).isoformat()!=value:
            raise ValueError()
        return value
    except (ValueError,TypeError):
        raise APIError(400,'Tanggal bisnis harus berformat YYYY-MM-DD.')

DATABASE = Path(__file__).resolve().parent.parent / '.runtime' / 'ebm.sqlite3'
ROLES = {
    'ADMIN': ['overview','review.read','review.write','pos','sync','modules','users'],
    'CEO': ['overview','review.read','sync','modules'],
    'MGR': ['overview','review.read','sync','modules'],
    'ACM': ['overview','review.read','sync','modules'],
    'SPV': ['overview','review.read','review.write','sync','modules'],
    'KASIR': ['pos','sync','modules'],
    'FINANCE': ['overview','sync','modules'],
    'GUDANG': ['modules'],
}
OUTLETS = [
    dict(id='EBM-001',name='Resto Contoh A',sales=2860000,target=3500000,tc=94,cogs=68.2),
    dict(id='EBM-002',name='Resto Contoh B',sales=4180000,target=4000000,tc=128,cogs=66.5),
    dict(id='EBM-003',name='Resto Contoh C',sales=3240000,target=3600000,tc=108,cogs=71.4),
]

class Connection(sqlite3.Connection):
    def __exit__(self,*args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()

def connect():
    c = sqlite3.connect(DATABASE, timeout=10,factory=Connection)
    c.row_factory = sqlite3.Row
    return c

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(),salt=salt.encode(),n=16384,r=8,p=1).hex()
    return salt + ':' + value

def matches(password, stored):
    return hmac.compare_digest(password_hash(password,stored.split(':')[0]),stored)

def init():
    DATABASE.parent.mkdir(exist_ok=True)
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,name TEXT NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL,scope TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,failures INTEGER NOT NULL DEFAULT 0,locked_until REAL NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,username TEXT NOT NULL,csrf TEXT NOT NULL,created REAL NOT NULL,last_seen REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS records(kind TEXT NOT NULL,id TEXT NOT NULL,outlet TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(kind,id));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,at REAL NOT NULL,actor TEXT NOT NULL,event TEXT NOT NULL,detail TEXT NOT NULL);
        ''')
        offline.init(c)
        for username,name,role,scope in [
            ('admin','Administrator Lokal','ADMIN','*'),('ceo','Direktur Sales','CEO','*'),
            ('mgr','Manager Contoh','MGR','*'),('acm','ACM Contoh','ACM','EBM-001,EBM-002'),
            ('spv','SPV Contoh','SPV','EBM-001,EBM-002'),('kasir','Kasir Resto A','KASIR','EBM-001'),
            ('finance','Finance Contoh','FINANCE','*'),('gudang','Gudang Contoh','GUDANG','')]:
            if not c.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone():
                c.execute('INSERT INTO users(username,name,password,role,scope) VALUES(?,?,?,?,?)',(username,name,password_hash('EbmDemo!2026'),role,scope))

def public(user):
    return dict(username=user['username'],name=user['name'],role=user['role'],scope=user['scope'].split(',') if user['scope'] else [],permissions=ROLES[user['role']],active=bool(user['active']))

def allowed(user,outlet):
    return user['scope']=='*' or outlet in user['scope'].split(',')

def log(c,actor,event,detail=''):
    c.execute('INSERT INTO audit(at,actor,event,detail) VALUES(?,?,?,?)',(time.time(),actor,event,detail))

class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message

def require(user,permission):
    if permission not in ROLES[user['role']]:
        raise APIError(403,'Anda tidak memiliki izin untuk tindakan ini.')

def authenticate(c, token):
    key=hashlib.sha256(token.encode()).hexdigest()
    session=c.execute('SELECT * FROM sessions WHERE token=?',(key,)).fetchone()
    now=time.time()
    if not session or now-session['last_seen']>1800 or now-session['created']>43200:
        c.execute('DELETE FROM sessions WHERE token=?',(key,))
        raise APIError(401,'Sesi berakhir. Silakan masuk kembali.')
    user=c.execute('SELECT * FROM users WHERE username=?',(session['username'],)).fetchone()
    if not user or not user['active']:
        raise APIError(401,'Akun tidak aktif. Silakan hubungi administrator.')
    c.execute('UPDATE sessions SET last_seen=? WHERE token=?',(now,key))
    return user,session

def handle(method,path,data,token,csrf):
    # Errors are committed too, so failed-login counters and audit survive.
    c=connect()
    try:
        c.execute('BEGIN IMMEDIATE')
        result,cookie=dispatch(c,method,path,data,token,csrf)
        c.commit()
        return result,cookie
    except APIError:
        c.commit()
        raise
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def dispatch(c,method,path,data,token,csrf):
    query=parse_qs(urlsplit(path).query)
    path=urlsplit(path).path
    selected_date=business_date(query.get('date',[DEMO_DATE])[0])
    if path=='/api/login' and method=='POST':
        username=str(data.get('username','')).strip().lower()
        password=str(data.get('password',''))
        user=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
        now=time.time()
        if user and user['locked_until']>now:
            raise APIError(429,'Terlalu banyak percobaan. Coba lagi setelah 15 menit.')
        valid=matches(password,user['password'] if user else password_hash('dummy'))
        if not user or not valid or not user['active']:
            if user:
                failures=user['failures']+1 if user['locked_until']==0 else 1
                c.execute('UPDATE users SET failures=?,locked_until=? WHERE username=?',(failures,now+900 if failures>=5 else 0,username))
            log(c,username[:64],'LOGIN_FAILED')
            raise APIError(401,'Username atau kata sandi salah, atau akun tidak aktif.')
        c.execute('UPDATE users SET failures=0,locked_until=0 WHERE username=?',(username,))
        c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(token.encode()).hexdigest(),))
        raw=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(32)
        c.execute('INSERT INTO sessions VALUES(?,?,?,?,?)',(hashlib.sha256(raw.encode()).hexdigest(),username,csrf,now,now))
        log(c,username,'LOGIN')
        return dict(user=public(user),csrf=csrf),raw
    user,session=authenticate(c,token)
    if method!='GET' and not hmac.compare_digest(csrf,session['csrf']):
        raise APIError(403,'Token sesi tidak sesuai. Muat ulang halaman.')
    if path=='/api/session' and method=='GET':
        return dict(user=public(user),csrf=session['csrf']),None
    if path.startswith('/api/offline/') and method=='POST':
        import sys
        return offline.dispatch(c,user,path,data,sys.modules[__name__])
    if path=='/api/assistant' and method=='POST':
        question=data.get('question','')
        if not isinstance(question,str) or not 1<=len(question.strip())<=1000:
            raise APIError(400,'Pertanyaan harus 1–1000 karakter.')
        day=business_date(data.get('businessDate',DEMO_DATE))
        import re
        mentioned=re.findall(r'\b\d{4}-\d{2}-\d{2}\b',question)
        if len(set(mentioned))>1:
            return dict(answer='Perbandingan beberapa tanggal belum didukung. Tanyakan satu tanggal bisnis setiap kali.',sources=[],businessDate=day,mode='local_rules'),None
        if mentioned: day=business_date(mentioned[0])
        rows=[];events=[];reviews=[]
        permissions=ROLES[user['role']]
        if set(permissions)&{'overview','review.read','pos','sync'}:
            rows=dispatch(c,'GET','/api/outlets?date='+day,{},token,csrf)[0]['data']
        if 'sync' in permissions:
            events=dispatch(c,'GET','/api/events?date='+day,{},token,csrf)[0]['data']
        if 'review.read' in permissions:
            reviews=dispatch(c,'GET','/api/reviews?date='+day,{},token,csrf)[0]['data']
        log(c,user['username'],'ASSISTANT_QUERY',day)
        return assistant.answer(question,day,public(user),rows,events,reviews),None
    if path=='/api/logout' and method=='POST':
        offline.revoke(c,user['username'])
        c.execute('DELETE FROM sessions WHERE token=?',(session['token'],));log(c,user['username'],'LOGOUT')
        return dict(ok=True),''
    if path=='/api/password' and method=='POST':
        if not matches(str(data.get('current','')),user['password']):
            raise APIError(400,'Kata sandi saat ini tidak sesuai.')
        password=str(data.get('password',''))
        if not 12<=len(password)<=128:
            raise APIError(400,'Kata sandi baru harus 12–128 karakter.')
        c.execute('UPDATE users SET password=? WHERE username=?',(password_hash(password),user['username']))
        c.execute('DELETE FROM sessions WHERE username=?',(user['username'],));log(c,user['username'],'PASSWORD_CHANGED')
        offline.revoke(c,user['username'])
        return dict(ok=True),''
    if path=='/api/outlets' and method=='GET':
        if not set(ROLES[user['role']]) & {'overview','review.read','pos','sync'}:
            raise APIError(403,'Data outlet tidak tersedia untuk peran ini.')
        rows=[o.copy() for o in OUTLETS if allowed(user,o['id'])]
        totals={o['id']:[0,0] for o in rows}
        for record in c.execute("SELECT outlet,data FROM records WHERE kind='events'"):
            event=json.loads(record['data'])
            if record['outlet'] in totals and event.get('businessDate',DEMO_DATE)==selected_date:
                totals[record['outlet']][0]+=event['amount']
                totals[record['outlet']][1]+=1
        for row in rows:
            base_sales=row['sales'] if selected_date==DEMO_DATE else 0
            base_tc=row['tc'] if selected_date==DEMO_DATE else 0
            row.update(baselineSales=base_sales,baselineTC=base_tc,addedSales=totals[row['id']][0],addedTC=totals[row['id']][1],businessDate=selected_date)
            row['sales']=base_sales+row['addedSales']
            row['tc']=base_tc+row['addedTC']
        if 'overview' not in ROLES[user['role']] and 'review.read' not in ROLES[user['role']]:
            rows=[dict(id=o['id'],name=o['name']) for o in rows]
        return dict(data=rows),None
    if path in ('/api/events','/api/reviews'):
        kind=path.split('/')[-1]
        require(user,('sync' if kind=='events' else 'review.read') if method=='GET' else ('pos' if kind=='events' else 'review.write'))
        if method=='GET':
            return dict(data=[json.loads(r['data']) for r in c.execute('SELECT * FROM records WHERE kind=?',(kind,)) if allowed(user,r['outlet']) and json.loads(r['data']).get('businessDate',DEMO_DATE)==selected_date]),None
        if method=='POST':
            outlet=data.get('outlet')
            posting_date=business_date(data.get('businessDate',DEMO_DATE))
            if outlet not in [o['id'] for o in OUTLETS] or not allowed(user,outlet):
                raise APIError(403,'Outlet berada di luar penugasan Anda.')
            if kind=='events':
                qty=data.get('quantity'); cash=data.get('cash')
                if type(qty)!=int or not 1<=qty<=100 or type(cash)!=int or not qty*30000<=cash<=1000000000:
                    raise APIError(400,'Jumlah atau pembayaran tidak valid.')
                value=dict(id=secrets.token_hex(16),outlet=outlet,quantity=qty,amount=qty*30000,cash=cash,status='LOCAL_PENDING',createdAt=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),actor=user['username'])
            else:
                finding=str(data.get('finding','')).strip();action=str(data.get('action','')).strip()
                if not 10<=len(finding)<=2000 or not 10<=len(action)<=2000:
                    raise APIError(400,'Temuan dan tindakan harus 10–2000 karakter.')
                value=dict(id=outlet+':'+posting_date,outlet=outlet,finding=finding,action=action,status='LOCAL_DRAFT',savedAt=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),actor=user['username'])
            value['businessDate']=posting_date
            c.execute('INSERT INTO records VALUES(?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data',(kind,value['id'],outlet,json.dumps(value)))
            log(c,user['username'],'SAVE_'+kind.upper(),outlet)
            return dict(data=value),None
    if path=='/api/users':
        require(user,'users')
        if method=='GET':
            return dict(data=[public(u) for u in c.execute('SELECT * FROM users ORDER BY username')],roles=ROLES),None
        if method=='POST':
            username=str(data.get('username','')).lower().strip();role=data.get('role');scope=data.get('scope',[])
            if username==user['username']:
                raise APIError(400,'Administrator tidak dapat mengubah akses akunnya sendiri.')
            if not c.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone() or role not in ROLES or not isinstance(scope,list) or not all(s in ['*','EBM-001','EBM-002','EBM-003'] for s in scope):
                raise APIError(400,'Pengguna, peran atau cakupan tidak valid.')
            if type(data.get('active'))!=bool:
                raise APIError(400,'Status akun tidak valid.')
            c.execute('UPDATE users SET role=?,scope=?,active=? WHERE username=?',(role,','.join(scope),int(data['active']),username))
            c.execute('DELETE FROM sessions WHERE username=?',(username,));log(c,user['username'],'USER_ACCESS_CHANGED',username)
            offline.revoke(c,username)
            return dict(ok=True),None
    if path=='/api/audit' and method=='GET':
        require(user,'users')
        return dict(data=[dict(r) for r in c.execute('SELECT at,actor,event,detail FROM audit ORDER BY id DESC LIMIT 50')]),None
    raise APIError(404,'Endpoint tidak tersedia.')
