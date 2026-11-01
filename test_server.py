import urllib.parse
from grading import grade, essay_suggestion
import unittest,subprocess,tempfile,socket,os,secrets,json,time,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
class ExamTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.password=secrets.token_urlsafe(24)
  with socket.socket() as s:s.bind(('127.0.0.1',0));cls.port=s.getsockname()[1]
  cls.base=f'http://127.0.0.1:{cls.port}';cls.start()
 @classmethod
 def start(cls):
  cls.proc=subprocess.Popen(['python3','server.py'],cwd=Path(__file__).parent,env={**os.environ,'ADMIN_PASSWORD':cls.password,'QUIZ_DATA_DIR':cls.tmp.name,'PORT':str(cls.port)},stdout=subprocess.DEVNULL)
  for _ in range(100):
   try:urllib.request.urlopen(cls.base,timeout=.2);return
   except (OSError,urllib.error.URLError):time.sleep(.05)
  raise RuntimeError('Server did not start')
 @classmethod
 def tearDownClass(cls):cls.proc.terminate();cls.proc.wait();cls.tmp.cleanup()
 def client(self):return urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def req(self,c,path,data=None,headers=None):
  req=urllib.request.Request(self.base+urllib.parse.quote(path),data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json',**(headers or {})})
  try:
   with c.open(req) as r:return r.status,r.read()
  except urllib.error.HTTPError as e:return e.code,e.read()
 def test_lifecycle(self):
  admin=self.client();student=self.client();other=self.client()
  self.assertEqual(self.req(student,'/api/admin/status')[0],401)
  self.assertEqual(self.req(admin,'/api/admin/login',{'password':'wrong'})[0],401)
  self.assertEqual(self.req(admin,'/api/admin/login',{'password':self.password}, {'Origin':'https://evil.test'})[0],403)
  self.assertEqual(self.req(admin,'/api/admin/login',{'password':self.password})[0],200)
  for name in ['1반','2반']:self.assertEqual(self.req(admin,'/api/admin/classes',{'name':name})[0],200)
  d=json.loads(self.req(admin,'/api/admin/status')[1]);c1,c2=d['classes']
  join={'code':c1['code'],'studentId':'1001','name':'학생'}
  self.assertEqual(self.req(student,'/api/join',join)[0],423)
  self.assertEqual(self.req(student,'/api/exam')[0],401)
  for path in ['/questions.json','/6단원_온라인시험지.html','/.data/exam.sqlite3','/server.py','/grading.py','/admin_auth.json','/../questions.json']:self.assertEqual(self.req(student,path)[0],404)
  self.assertNotIn('국가 간 경쟁',self.req(student,'/')[1].decode())
  self.assertEqual(self.req(admin,'/api/admin/toggle',{'id':c1['id'],'opened':True})[0],200)
  self.assertEqual(self.req(student,'/api/join',join)[0],200)
  self.assertEqual(self.req(other,'/api/join',{**join,'code':c2['code']})[0],423)
  exam=json.loads(self.req(student,'/api/exam')[1]);self.assertEqual(len(exam['questions']),16)
  self.assertEqual(self.req(student,'/api/answers',{'answers':{'1':6}})[0],400)
  self.assertEqual(self.req(student,'/api/answers',{'answers':{'1':True}})[0],400)
  self.assertEqual(self.req(student,'/api/submit',{'answers':{'1':1}})[0],400)
  self.assertEqual(self.req(student,'/api/answers',{'answers':{'1':2}})[0],200)
  self.assertEqual(self.req(student,'/api/event',{'kind':'화면 이탈'})[0],200)
  self.assertEqual(self.req(admin,'/api/admin/toggle',{'id':c1['id'],'opened':False})[0],200)
  for path,data in [('/api/exam',None),('/api/answers',{'answers':{}}),('/api/submit',{'answers':{}})]:self.assertEqual(self.req(student,path,data)[0],423)
  self.assertEqual(self.req(admin,'/api/admin/toggle',{'id':c1['id'],'opened':True})[0],200)
  self.assertEqual(json.loads(self.req(student,'/api/exam')[1])['answers'],{'1':2})
  answers={str(i):1 for i in range(1,16)};answers['16']={'government':'북한 정부와 대화를 지속하고 경제적 교류를 한다.','citizen':'북한을 바로 알기 위해 연구하고 같은 민족임을 알린다.'}
  self.assertEqual(self.req(student,'/api/submit',{'answers':answers})[0],200)
  self.assertEqual(json.loads(self.req(student,'/api/exam')[1])['questions'],[])
  self.assertEqual(self.req(student,'/api/answers',{'answers':answers})[0],409)
  d=json.loads(self.req(admin,'/api/admin/status')[1]);self.assertEqual(d['students'][0]['answers'],answers);self.assertEqual(len(d['students'][0]['events']),1)
  record=d['students'][0]['recordId']
  self.assertEqual(d['students'][0]['grade']['suggestedEssay'],5)
  self.assertEqual(self.req(other,'/api/admin/grade',{'recordId':record,'score':4})[0],401)
  for bad in [6,-1,3.5,True,'5']:
   self.assertEqual(self.req(admin,'/api/admin/grade',{'recordId':record,'score':bad})[0],400)
  self.assertEqual(self.req(admin,'/api/admin/grade',{'recordId':record,'score':4,'note':'교사 확인'})[0],200)
  d=json.loads(self.req(admin,'/api/admin/status')[1]);g=d['students'][0]['grade']
  self.assertTrue(g['manual']);self.assertEqual(g['essay'],4);self.assertEqual(g['total'],g['objective']+4)
  self.assertIn('준비',self.req(other,'/practice')[1].decode())
  self.proc.terminate();self.proc.wait();type(self).start()
  self.assertEqual(self.req(admin,'/api/admin/status')[0],401)
  self.assertEqual(self.req(admin,'/api/admin/login',{'password':self.password})[0],200)
  after=json.loads(self.req(admin,'/api/admin/status')[1])['students']
  self.assertEqual(len(after),1);self.assertEqual(after[0]['grade']['essay'],4);self.assertEqual(after[0]['grade_note'],'교사 확인')
  self.assertEqual(self.req(admin,'/api/admin/grade',{'recordId':record,'score':None})[0],200)
  self.assertEqual(json.loads(self.req(admin,'/api/admin/status')[1])['students'][0]['grade']['essay'],5)
  self.assertEqual(self.req(admin,'/api/admin/logout',{})[0],200)
  self.assertEqual(self.req(admin,'/api/admin/status')[0],401)
class GradingTests(unittest.TestCase):
 def test_rubric(self):
  cases=[({},0),({'government':'작성','citizen':'작성'},3),({'government':'대화한다','citizen':'노력한다'},4),({'government':'경제적 활동을 함께한다','citizen':'북한을 바로 알기 위해 노력한다'},5),({'government':'대화한다'},2)]
  for answer,score in cases:self.assertEqual(essay_suggestion(answer)[0],score)
  key=[1,1,5,3,1,2,5,4,3,1,1,5,4,2,2];answers={str(i+1):a for i,a in enumerate(key)};answers['16']={'government':'외교 관계를 맺는다','citizen':'정부에 평화를 위한 대화를 요구한다'}
  self.assertEqual(grade(answers)['total'],20)
  self.assertEqual(grade(answers,0)['total'],15)
if __name__=='__main__':unittest.main(verbosity=2)
