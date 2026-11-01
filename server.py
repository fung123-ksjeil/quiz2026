"""Run with ADMIN_PASSWORD set. No external dependencies."""
from contextlib import contextmanager
from github_store import GitHubStore, StorageError
import os, sqlite3, json, secrets, hashlib, hmac, time, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from http.cookies import SimpleCookie
from grading import grade, FIELDS
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('QUIZ_DATA_DIR',str(ROOT/'.data')));DATA.mkdir(parents=True,exist_ok=True)
PASSWORD=os.environ.get('ADMIN_PASSWORD','')
if PASSWORD:
 if len(PASSWORD)<6:raise SystemExit('ADMIN_PASSWORD must contain at least 6 characters.')
 SALT=secrets.token_bytes(16)
 PASSWORD_HASH=hashlib.pbkdf2_hmac('sha256',PASSWORD.encode(),SALT,200000)
else:
 if not (ROOT/'admin_auth.json').is_file():raise SystemExit('Set ADMIN_PASSWORD in the hosting service environment settings.')
 auth=json.loads((ROOT/'admin_auth.json').read_text())
 SALT=bytes.fromhex(auth['salt']);PASSWORD_HASH=bytes.fromhex(auth['hash'])
del PASSWORD
QUESTIONS=json.loads((ROOT/'questions.json').read_text())
DB=DATA/'exam.sqlite3'
with sqlite3.connect(DB) as db:
 db.executescript('''CREATE TABLE IF NOT EXISTS classes(id TEXT PRIMARY KEY,name TEXT NOT NULL,code TEXT UNIQUE NOT NULL,opened INTEGER DEFAULT 0);
 CREATE TABLE IF NOT EXISTS students(token TEXT PRIMARY KEY,class_id TEXT,student_id TEXT,name TEXT,answers TEXT DEFAULT '{}',submitted TEXT,events TEXT DEFAULT '[]',updated REAL);
 ''')
 # Additive migration preserves existing data.
 columns={r[1] for r in db.execute('PRAGMA table_info(students)')}
 if 'essay_score' not in columns:db.execute('ALTER TABLE students ADD COLUMN essay_score INTEGER')
 if 'grade_note' not in columns:db.execute("ALTER TABLE students ADD COLUMN grade_note TEXT DEFAULT ''")
 if 'created_at' not in columns:db.execute('ALTER TABLE students ADD COLUMN created_at REAL')
 db.execute('UPDATE students SET created_at=COALESCE(updated,?) WHERE created_at IS NULL',(time.time(),))
SESSIONS={};ATTEMPTS={};LOCK=threading.Lock()
def connect():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row;return db
DATABASE_LOCK=threading.RLock()
STORE=GitHubStore()
if os.environ.get('RENDER') and not STORE.enabled:raise SystemExit('Set GITHUB_DATA_REPO and GITHUB_DATA_TOKEN before deploying on a temporary Render filesystem.')
DIRTY=False
PENDING_SUBMISSIONS=set()
LAST_STORAGE_ERROR=False

TABLE_COLUMNS={
 'classes':['id','name','code','opened'],
 'students':['rowid','token','class_id','student_id','name','answers','submitted','events','updated','essay_score','grade_note','created_at']
}
def snapshot(db):
 return {'version':1,'savedAt':time.time(),**{table:[dict(r) for r in db.execute('SELECT '+','.join(cols)+' FROM '+table)] for table,cols in TABLE_COLUMNS.items()}}

def allocate_code(db):
 used={r['code'] for r in db.execute('SELECT code FROM classes')}
 available=[str(n) for n in range(1000,10000) if str(n) not in used]
 if not available:raise StorageError('No four-digit class codes remain.')
 return secrets.choice(available)

def normalize_codes(db):
 # Preserve class IDs and existing four-digit codes; update only legacy codes.
 for row in list(db.execute('SELECT id,code FROM classes')):
  if len(row['code'])!=4 or any(c not in '0123456789' for c in row['code']):
   db.execute('UPDATE classes SET code=? WHERE id=?',(allocate_code(db),row['id']))

def persist(db):
 global DIRTY,LAST_STORAGE_ERROR
 STORE.save(snapshot(db));DIRTY=False;LAST_STORAGE_ERROR=False;PENDING_SUBMISSIONS.clear()

# The remote snapshot is authoritative on startup. Never start empty after a remote failure.
if STORE.enabled:
 try:
  saved=STORE.load()
  with connect() as db:
   if saved is not None:
    for table,cols in TABLE_COLUMNS.items():
     db.execute('DELETE FROM '+table)
     for row in saved[table]:
      db.execute('INSERT INTO '+table+'('+','.join(cols)+') VALUES('+','.join('?' for _ in cols)+')',[row.get(c) for c in cols])
   normalize_codes(db);db.commit();persist(db)
 except StorageError as e:raise SystemExit(str(e)) from None
else:
 with connect() as db:normalize_codes(db)

def sync_worker():
 global LAST_STORAGE_ERROR
 while True:
  time.sleep(60)
  with DATABASE_LOCK:
   with connect() as db:
    if DIRTY:
     try:persist(db)
     except StorageError:LAST_STORAGE_ERROR=True
if STORE.enabled:threading.Thread(target=sync_worker,daemon=True).start()

@contextmanager
def request_database(handler):
 global DIRTY
 with DATABASE_LOCK:
  db=connect();handler._defer=True;handler._pending=None
  try:
   before=db.total_changes
   yield db
   changed=db.total_changes>before
   if changed:DIRTY=True
   db.commit()
   # Classes, final submissions and manual grades must reach GitHub before success.
   if STORE.enabled and handler._force_sync:persist(db)
   handler._defer=False
   if handler._pending:handler.send(*handler._pending)
  except Exception:
   db.rollback();handler._defer=False;handler._pending=None;raise
  finally:db.close()

class HTTPError(Exception):
 def __init__(self,status,message):self.status=status;self.message=message
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass # do not log credentials, tokens or student details
 def headers_common(self):
  self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Frame-Options','DENY')
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
 def send(self,status,obj,cookie=None):
  if getattr(self,'_defer',False):self._pending=(status,obj,cookie);return
  b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status);self.headers_common();self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)))
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(b)
 def token(self,key):
  c=SimpleCookie()
  try:c.load(self.headers.get('Cookie',''));return c[key].value if key in c else ''
  except:return ''
 def cookie(self,key,value,maxage=28800):
  return f'{key}={value}; HttpOnly; SameSite=Strict; Path=/; Max-Age={maxage}'+('; Secure' if os.environ.get('COOKIE_SECURE')=='1' else '')
 def admin(self):
  with LOCK:valid=SESSIONS.get(self.token('admin'),0)>time.time()
  if not valid:raise HTTPError(401,'관리자 로그인이 필요합니다.')
 def student(self,db,require_open=True):
  s=db.execute('SELECT students.*,classes.opened FROM students JOIN classes ON classes.id=students.class_id WHERE token=?',(self.token('student'),)).fetchone()
  if not s:raise HTTPError(401,'응시 코드로 입장해 주세요.')
  if require_open and not s['opened']:raise HTTPError(423,'선생님이 시험지를 잠갔습니다.')
  return s
 def do_GET(self):self.handle_request(False)
 def do_POST(self):self.handle_request(True)
 def handle_request(self,post):
  try:
   path=self.path.split('?')[0]
   self._force_sync=post and path in ['/api/admin/classes','/api/admin/toggle','/api/admin/grade','/api/submit','/api/admin/delete']
   data={}
   if post:
    # Reject cross-origin browser writes, including login CSRF.
    if self.headers.get('Sec-Fetch-Site')=='cross-site':raise HTTPError(403,'다른 사이트에서 요청할 수 없습니다.')
    origin=self.headers.get('Origin')
    if origin and origin.split('://',1)[-1]!=self.headers.get('Host'):raise HTTPError(403,'요청 출처가 올바르지 않습니다.')
    if self.headers.get_content_type()!='application/json':raise HTTPError(415,'JSON 요청이 필요합니다.')
    n=int(self.headers.get('Content-Length','0'))
    if n>100000 or n<=0:raise HTTPError(400,'요청 크기가 올바르지 않습니다.')
    data=json.loads(self.rfile.read(n))
    if not isinstance(data,dict):raise HTTPError(400,'잘못된 요청입니다.')
   if not post and path=='/health':return self.send(200,{'ok':True})
   with request_database(self) as db:
    if post and path=='/api/admin/login':
     ip=self.client_address[0];now=time.time()
     with LOCK:
      hits=[t for t in ATTEMPTS.get(ip,[]) if now-t<600];ATTEMPTS[ip]=hits
      if len(hits)>=10:raise HTTPError(429,'로그인 시도가 많습니다. 10분 후 다시 시도하세요.')
      hits.append(now)
     p=data.get('password','')
     if not isinstance(p,str) or len(p)>1000 or not hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',p.encode(),SALT,200000),PASSWORD_HASH):raise HTTPError(401,'비밀번호가 올바르지 않습니다.')
     token=secrets.token_urlsafe(32)
     with LOCK:SESSIONS[token]=now+28800;ATTEMPTS.pop(ip,None)
     return self.send(200,{'ok':True},self.cookie('admin',token))
    if path.startswith('/api/admin/'):
     self.admin()
     if post and path=='/api/admin/logout':
      with LOCK:SESSIONS.pop(self.token('admin'),None)
      return self.send(200,{'ok':True},self.cookie('admin','',0))
     if post and path=='/api/admin/classes':
      name=data.get('name','')
      if not isinstance(name,str) or not name.strip() or len(name)>60:raise HTTPError(400,'반 이름을 입력하세요 (60자 이내).')
      db.execute('INSERT INTO classes(id,name,code) VALUES(?,?,?)',(secrets.token_hex(8),name.strip(),allocate_code(db)))
      return self.send(200,{'ok':True})
     if post and path=='/api/admin/toggle':
      if type(data.get('opened')) is not bool:raise HTTPError(400,'공개 상태가 올바르지 않습니다.')
      if db.execute('UPDATE classes SET opened=? WHERE id=?',(int(data['opened']),data.get('id'))).rowcount!=1:raise HTTPError(404,'반을 찾을 수 없습니다.')
      return self.send(200,{'ok':True})
     if post and path=='/api/admin/grade':
      score=data.get('score');record=data.get('recordId');note=data.get('note','')
      if type(record) is not int or (score is not None and (type(score) is not int or not 0<=score<=5)) or not isinstance(note,str) or len(note)>2000:raise HTTPError(400,'서술형 점수는 0~5점 정수로 입력하세요.')
      student=db.execute('SELECT submitted FROM students WHERE rowid=?',(record,)).fetchone()
      if not student:raise HTTPError(404,'학생을 찾을 수 없습니다.')
      if not student['submitted']:raise HTTPError(409,'제출 후 채점할 수 있습니다.')
      db.execute('UPDATE students SET essay_score=?,grade_note=? WHERE rowid=?',(score,note,record))
      return self.send(200,{'ok':True})
     if post and path=='/api/admin/delete':
      if data.get('confirm')!='DELETE':raise HTTPError(400,'삭제 확인이 필요합니다.')
      if data.get('scope')=='student' and type(data.get('recordId')) is int:
       count=db.execute('DELETE FROM students WHERE rowid=?',(data['recordId'],)).rowcount
      elif data.get('scope')=='class' and isinstance(data.get('classId'),str):
       db.execute('UPDATE classes SET opened=0 WHERE id=?',(data['classId'],))
       count=db.execute('DELETE FROM students WHERE class_id=?',(data['classId'],)).rowcount
      else:raise HTTPError(400,'삭제 대상을 선택하세요.')
      return self.send(200,{'ok':True,'deleted':count})
     if not post and path=='/api/admin/status':
      classes=[dict(r) for r in db.execute('SELECT * FROM classes ORDER BY rowid')]
      students=[dict(r) for r in db.execute('SELECT rowid AS recordId,class_id,student_id,name,answers,submitted,events,updated,essay_score,grade_note FROM students ORDER BY updated DESC')]
      for s in students:
       s['answers']=json.loads(s['answers']);s['events']=json.loads(s['events']);s['grade']=grade(s['answers'],s['essay_score']) if s['submitted'] else None
      return self.send(200,{'classes':classes,'students':students,'storage':{'mode':'github' if STORE.enabled else 'local','pending':DIRTY,'error':LAST_STORAGE_ERROR}})
    if post and path=='/api/join':
     c=db.execute('SELECT * FROM classes WHERE code=?',(data.get('code'),)).fetchone()
     if not c:raise HTTPError(403,'응시 코드가 올바르지 않습니다.')
     if not c['opened']:raise HTTPError(423,'아직 공개되지 않았거나 잠긴 시험입니다.')
     sid=data.get('studentId','');name=data.get('name','')
     if not all(isinstance(x,str) and x.strip() and len(x)<=40 for x in [sid,name]):raise HTTPError(400,'학번과 이름을 입력하세요 (40자 이내).')
     old=db.execute('SELECT * FROM students WHERE token=? AND class_id=?',(self.token('student'),c['id'])).fetchone()
     if old:return self.send(200,{'ok':True})
     token=secrets.token_urlsafe(32);db.execute('INSERT INTO students(rowid,token,class_id,student_id,name,updated,created_at) VALUES(?,?,?,?,?,?,?)',(secrets.randbits(52),token,c['id'],sid.strip(),name.strip(),time.time(),time.time()))
     return self.send(200,{'ok':True},self.cookie('student',token))
    if not post and path=='/api/exam':
     s=self.student(db)
     return self.send(200,{'questions':QUESTIONS if not s['submitted'] else [],'answers':{} if s['submitted'] else json.loads(s['answers']),'name':s['name'],'studentId':s['student_id'],'submitted':s['submitted'],'pendingSync':s['token'] in PENDING_SUBMISSIONS})
    if post and path in ['/api/answers','/api/submit','/api/event']:
     s=self.student(db)
     if s['submitted']:
      if path=='/api/submit' and data.get('answers')==json.loads(s['answers']):return self.send(200,{'ok':True})
      raise HTTPError(409,'이미 제출한 답안입니다.')
     if path=='/api/event':
      kind=data.get('kind')
      if kind not in ['화면 이탈','복사 시도','인쇄 시도','캡처 단축키','전체 화면 종료']:raise HTTPError(400,'잘못된 기록입니다.')
      events=json.loads(s['events']);events.append({'kind':kind,'time':time.time()});db.execute('UPDATE students SET events=? WHERE token=?',(json.dumps(events[-500:]),s['token']))
     else:
      answers=data.get('answers')
      if not isinstance(answers,dict) or any(k not in [str(q['id']) for q in QUESTIONS] for k in answers):raise HTTPError(400,'답안 형식이 올바르지 않습니다.')
      for q in QUESTIONS:
       a=answers.get(str(q['id']))
       if a is None:continue
       if q['options']:
        if type(a) is not int or not 1<=a<=5:raise HTTPError(400,'선택 답안이 올바르지 않습니다.')
       elif isinstance(a,dict):
        if set(a)-set(FIELDS) or any(not isinstance(v,str) or len(v)>10000 for v in a.values()):raise HTTPError(400,'서술형 답안이 올바르지 않습니다.')
       elif not isinstance(a,str) or len(a)>10000:raise HTTPError(400,'서술형 답안이 올바르지 않습니다.')
      submitted=None
      if path=='/api/submit':
       if any(answers.get(str(q['id'])) in [None,''] or isinstance(answers.get(str(q['id'])),str) and not answers[str(q['id'])].strip() for q in QUESTIONS):raise HTTPError(400,'모든 문항을 작성해 주세요.')
       essay=answers.get('16')
       if isinstance(essay,dict) and any(not essay.get(k,'').strip() for k in FIELDS):raise HTTPError(400,'16번의 두 답안을 모두 작성해 주세요.')
       submitted=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
      if submitted and STORE.enabled:PENDING_SUBMISSIONS.add(s['token'])
      db.execute('UPDATE students SET answers=?,submitted=?,updated=? WHERE token=?',(json.dumps(answers,ensure_ascii=False),submitted,time.time(),s['token']))
     return self.send(200,{'ok':True})
   # Only these files are public. Never serve questions.json, SQLite, source, or legacy HTML.
   files={'/':'index.html','/admin':'admin.html','/practice':'practice.html','/app.js':'app.js','/admin.js':'admin.js','/style.css':'style.css'}
   if not post and path in files:
    file=ROOT/files[path];b=file.read_bytes();self.send_response(200);self.headers_common();self.send_header('Content-Type',{'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8'}[file.suffix[1:]]);self.send_header('Content-Length',str(len(b)));self.end_headers();return self.wfile.write(b)
   raise HTTPError(404,'찾을 수 없습니다.')
  except StorageError:self.send(503,{'error':'GitHub 보관을 확인하지 못했습니다. 잠시 후 다시 시도하세요. 답안은 이 서버에 임시 저장되어 있습니다.'})
  except HTTPError as e:self.send(e.status,{'error':e.message})
  except (ValueError,TypeError):self.send(400,{'error':'잘못된 요청입니다.'})
  except Exception:self.send(500,{'error':'서버 오류가 발생했습니다. 다시 시도하세요.'})
if __name__=='__main__':
 print('Exam server ready. Administrator: /admin',flush=True)
 ThreadingHTTPServer((os.environ.get('HOST','127.0.0.1'),int(os.environ.get('PORT','8000'))),Handler).serve_forever()
