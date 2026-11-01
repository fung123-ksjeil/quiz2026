"""Content CRUD, reference feedback, frozen exams, and encrypted restart coverage."""
import unittest,json,collections
import test_server as base
import test_github_store as remote
from content import TOPICS
class ContentMixin:
 def test_content_workflow(self):
  admin=self.client();student=self.client();new_student=self.client()
  self.assertEqual(self.req(admin,'/api/admin/login',{'password':self.password})[0],200)
  self.assertEqual(self.req(student,'/api/admin/content')[0],401)
  info=json.loads(self.req(admin,'/api/admin/content')[1]);self.assertEqual(len(info['practice']),30)
  self.assertEqual(collections.Counter(q['difficulty'] for q in info['practice']),{'상':5,'중':5,'하':20});self.assertTrue(all(q['active'] for q in info['practice']))
  published=json.loads(self.req(student,'/api/practice')[1])['questions'];self.assertEqual(len(published),30);self.assertNotIn('correct',published[0]);self.assertNotIn('explanation',published[0])
  q=info['practice'][0]
  wrong=json.loads(self.req(student,'/api/practice/check',{'id':q['id'],'answer':'X'})[1]);self.assertFalse(wrong['isCorrect']);self.assertTrue(wrong['explanation']);self.assertEqual(wrong['source']['page'],105)
  self.assertEqual(self.req(admin,'/api/admin/practice/visibility',{'ids':[q['id']]})[0],200)
  self.assertEqual(len(json.loads(self.req(student,'/api/practice')[1])['questions']),1)
  self.assertEqual(self.req(student,'/api/practice/check',{'id':info['practice'][1]['id'],'answer':'O'})[0],404)
  draft=json.loads(self.req(admin,'/api/admin/practice/draft',{'statement':'국제 사회에는 중앙 정부가 있다.','correct':'X','topicId':'central'})[1]);self.assertIn('중앙 정부가 없습니다',draft['explanation']);self.assertEqual(draft['source']['pdfPage'],4)
  p={'statement':'국제 사회에는 중앙 정부가 있다.','correct':'X','topicId':'central','difficulty':'중','active':False,'explanation':draft['explanation']}
  pid=json.loads(self.req(admin,'/api/admin/practice',p)[1])['id'];p.update(id=pid,active=True,explanation='수정한 해설: 중앙 정부는 없습니다.')
  self.assertEqual(self.req(admin,'/api/admin/practice',p)[0],200)
  self.assertEqual(len(json.loads(self.req(student,'/api/practice')[1])['questions']),2)
  self.assertIn('수정한 해설',json.loads(self.req(student,'/api/practice/check',{'id':pid,'answer':'O'})[1])['explanation'])
  self.assertEqual(self.req(admin,'/api/admin/classes',{'name':'코드 지정 반','code':'2468'})[0],200)
  self.assertEqual(self.req(admin,'/api/admin/classes',{'name':'중복 반','code':'2468'})[0],409)
  classes=json.loads(self.req(admin,'/api/admin/status')[1])['classes'];c=next(c for c in classes if c['name']=='코드 지정 반')
  self.assertEqual(self.req(admin,'/api/admin/class-code',{'id':c['id'],'code':'1357'})[0],200)
  self.assertEqual(self.req(admin,'/api/admin/class-code',{'id':c['id'],'code':'12'})[0],400)
  self.assertEqual(self.req(admin,'/api/admin/toggle',{'id':c['id'],'opened':True})[0],200)
  self.assertEqual(self.req(student,'/api/join',{'code':'1357','studentId':'2001','name':'기존학생'})[0],200)
  original=json.loads(self.req(student,'/api/exam')[1])['questions'];self.assertEqual(len(original),16);self.assertNotIn('correct',original[0])
  edited={**info['exam'][0],'correct':2,'title':'수정한 1번 문항'}
  self.assertEqual(self.req(admin,'/api/admin/exam',edited)[0],409)
  self.assertEqual(self.req(admin,'/api/admin/toggle',{'id':c['id'],'opened':False})[0],200)
  self.assertEqual(self.req(admin,'/api/admin/exam',edited)[0],200)
  added={'kind':'ox','title':'추가한 O/X 시험 문항','body':'','points':2,'correct':1}
  added_id=json.loads(self.req(admin,'/api/admin/exam',added)[1])['id']
  self.assertEqual(self.req(admin,'/api/admin/toggle',{'id':c['id'],'opened':True})[0],200)
  self.assertEqual(len(json.loads(self.req(student,'/api/exam')[1])['questions']),16)
  self.assertEqual(self.req(new_student,'/api/join',{'code':'1357','studentId':'2002','name':'새학생'})[0],200)
  new_exam=json.loads(self.req(new_student,'/api/exam')[1])['questions'];self.assertEqual(len(new_exam),17);self.assertEqual(new_exam[0]['title'],'수정한 1번 문항')
  answers={str(q['id']):q['correct'] if q['options'] else {'government':'대화와 경제 교류','citizen':'북한을 이해하고 같은 민족임을 알린다.'} for q in info['exam']}
  self.assertEqual(self.req(student,'/api/submit',{'answers':answers,'studentId':'   ','name':'수정한 이름'})[0],400)
  self.assertEqual(self.req(student,'/api/submit',{'answers':answers,'studentId':'002001','name':'수정한 이름'})[0],200)
  self.assertEqual(self.req(student,'/api/submit',{'answers':answers,'studentId':'002001','name':'제출 후 변경'})[0],409)
  new_answers={**answers,'1':2,str(added_id):1};self.assertEqual(self.req(new_student,'/api/submit',{'answers':new_answers})[0],200)
  rows=json.loads(self.req(admin,'/api/admin/status')[1])['students'];old=next(s for s in rows if s['student_id']=='002001');new=next(s for s in rows if s['student_id']=='2002');self.assertEqual(old['grade']['total'],20);self.assertEqual(new['grade']['total'],22);self.assertEqual(old['name'],'수정한 이름');self.assertRegex(old['submittedAtKst'],r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
  self.assertEqual(self.req(self.client(),'/api/admin/scores.xlsx')[0],401)
  export=self.req(admin,'/api/admin/scores.xlsx?classId='+c['id']);self.assertEqual(export[0],200)
  from test_scores import read_workbook
  rows=read_workbook(export[1]);self.assertEqual(rows[0][:2],['학번','이름']);by_id={r[0]:r for r in rows[1:]};self.assertEqual(by_id['002001'][1],'수정한 이름');self.assertEqual(by_id['002001'][rows[0].index('제출 시각 (한국 시간)')],old['submittedAtKst']);self.assertEqual(by_id['002001'][rows[0].index('총점')],20);self.assertEqual(by_id['2002'][rows[0].index('총점')],22)
  self.assertEqual(self.req(admin,'/api/admin/scores.xlsx?classId=missing')[0],404)
  self.proc.terminate();self.proc.wait();type(self).start()
  self.assertEqual(self.req(admin,'/api/admin/login',{'password':self.password})[0],200)
  after=json.loads(self.req(admin,'/api/admin/content')[1]);self.assertEqual(after['exam'][0]['correct'],2);self.assertEqual(len(after['exam']),17);self.assertEqual(len(after['practice']),31)
  rows=json.loads(self.req(admin,'/api/admin/status')[1])['students'];self.assertEqual(next(s for s in rows if s['student_id']=='002001')['grade']['total'],20)
  self.assertEqual(len(json.loads(self.req(student,'/api/practice')[1])['questions']),2)
  self.assertEqual(self.req(student,'/api/admin/class-delete',{'id':c['id'],'expectedCount':2,'deleteRecords':True,'confirm':'DELETE_CLASS'})[0],401)
  self.assertEqual(self.req(admin,'/api/admin/class-delete',{'id':c['id'],'expectedCount':2,'deleteRecords':True})[0],400)
  self.assertEqual(self.req(admin,'/api/admin/class-delete',{'id':c['id'],'expectedCount':0,'deleteRecords':True,'confirm':'DELETE_CLASS'})[0],409)
  self.assertEqual(self.req(admin,'/api/admin/class-delete',{'id':c['id'],'expectedCount':2,'deleteRecords':False,'confirm':'DELETE_CLASS'})[0],409)
  self.assertEqual(len(json.loads(self.req(admin,'/api/admin/status')[1])['students']),2)
  self.assertEqual(json.loads(self.req(admin,'/api/admin/class-delete',{'id':c['id'],'expectedCount':2,'deleteRecords':True,'confirm':'DELETE_CLASS'})[1])['deletedRecords'],2)
  self.assertEqual(self.req(student,'/api/exam')[0],401)
  self.assertEqual(self.req(admin,'/api/admin/classes',{'name':'빈 반','code':'9999'})[0],200)
  empty=json.loads(self.req(admin,'/api/admin/status')[1])['classes'][0]
  self.assertEqual(self.req(admin,'/api/admin/class-delete',{'id':empty['id'],'expectedCount':0,'deleteRecords':False,'confirm':'DELETE_CLASS'})[0],200)
  self.proc.terminate();self.proc.wait();type(self).start()
  self.assertEqual(self.req(admin,'/api/admin/login',{'password':self.password})[0],200)
  clean=json.loads(self.req(admin,'/api/admin/status')[1]);self.assertEqual(clean['students'],[]);self.assertEqual(clean['classes'],[])
  self.assertEqual(len(json.loads(self.req(admin,'/api/admin/content')[1])['exam']),17)
class LocalContentTests(ContentMixin,base.ExamTests):
 test_lifecycle=None
class GitHubContentTests(ContentMixin,remote.GitHubPersistenceTests):
 test_lifecycle=None
 test_remote_write_failure=None
if __name__=='__main__':unittest.main(verbosity=2)
