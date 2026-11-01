import unittest,copy
from grading import aligned,essay_suggestion,grade,RELATIONSHIP_EXPECTED
from content import default_exam
class RelationshipGradingTests(unittest.TestCase):
 def test_broad_government_efforts(self):
  for answer in ['북한과 관계가 좋아지도록 여러 정책을 시도한다.','북한에 쌀과 의약품을 보내준다.','북한을 지원한다.','필요한 도움을 준다.','남북이 함께 체육 경기를 연다.','남북 사이의 긴장을 낮추려고 노력한다.','북한과 신뢰를 쌓고 관계를 회복한다.','인도적 지원 사업을 추진한다.','북한 정부와 대화를 지속한다.','경제적 활동을 함께한다.','서로 도와주며 친하게 지내려고 한다.']:
   with self.subTest(answer=answer):self.assertTrue(aligned(answer,'government'))
 def test_broad_citizen_efforts_without_repeating_subject(self):
  for answer in ['국내외에서 관계 개선 캠페인을 연다.','평화 집회에 참여한다.','식량을 보내는 모금과 기부를 한다.','스포츠 경기를 같이한다.','민간 문화 교류를 늘린다.','북한 사회를 공부하고 알려준다.','서로를 이해하고 존중한다.','같은 민족이라는 생각으로 관계 개선을 시도한다.','정부에 대화와 협상을 촉구한다.']:
   with self.subTest(answer=answer):self.assertTrue(aligned(answer,'citizen'))
 def test_opposite_intent_and_wrong_actor_not_full_credit(self):
  self.assertFalse(aligned('북한을 공격해야 한다.','government'))
  self.assertFalse(aligned('대화를 하지 않고 교류를 끊는다.','government'))
  self.assertFalse(aligned('정부가 외교 활동을 한다.','citizen'))
  self.assertFalse(aligned('시민단체가 캠페인을 한다.','government'))
  self.assertTrue(aligned('공격하지 않고 대화와 협력으로 해결한다.','government'))
  self.assertTrue(aligned('교류를 끊지 않고 대화를 이어간다.','government'))
 def test_five_point_student_friendly_rubric(self):
  self.assertEqual(essay_suggestion({'government':'식량과 의약품을 보내준다.','citizen':'관계 개선 캠페인을 연다.'})[0],5)
  self.assertEqual(essay_suggestion({'government':'관계를 좋게 하려고 노력한다.','citizen':'작성'})[0],4)
  self.assertEqual(essay_suggestion({'government':'작성','citizen':'작성'})[0],3)
 def test_saved_q16_keyword_version_and_manual_scores(self):
  exam=default_exam();exam[-1]['rubric']='keywords';exam[-1]['keywords']={'government':['정상회담'],'citizen':['역사연구']}
  answers={'16':{'government':'북한에 식량을 지원한다.','citizen':'평화 캠페인에 참여한다.'}}
  result=grade(answers,questions=exam);self.assertEqual(result['essay'],5);self.assertEqual(result['essays'][0]['expected'],RELATIONSHIP_EXPECTED)
  manual=grade(answers,questions=exam,manual_scores={'16':4});self.assertEqual(manual['essay'],4);self.assertEqual(manual['suggestedEssay'],5)
  unrelated=copy.deepcopy(exam[-1]);unrelated['title']='수학의 원리';unrelated['body']='분수와 방정식을 설명하시오.'
  self.assertEqual(grade(answers,questions=[unrelated])['essay'],3)
class RubricMigrationTests(unittest.TestCase):
 def test_existing_record_and_teacher_override_are_preserved(self):
  import tempfile,subprocess,os,secrets,sqlite3,json
  from pathlib import Path
  with tempfile.TemporaryDirectory() as folder:
   env={**os.environ,'ADMIN_PASSWORD':secrets.token_urlsafe(20),'QUIZ_DATA_DIR':folder,'GITHUB_DATA_REPO':'','GITHUB_DATA_TOKEN':'','RENDER':''}
   command=['python3','-c','import server'];subprocess.run(command,cwd=Path(__file__).parent,env=env,check=True)
   exam=default_exam();exam[-1]['rubric']='keywords';exam[-1]['expected']={'government':'외교','citizen':'북한 연구'}
   answers={'16':{'government':'북한에 식량을 지원한다.','citizen':'관계 개선 캠페인을 한다.'}}
   with sqlite3.connect(Path(folder)/'exam.sqlite3') as db:
    db.execute("DELETE FROM settings WHERE key='relationship_rubric_v2'")
    db.execute("UPDATE settings SET value=? WHERE key='exam'",(json.dumps(exam,ensure_ascii=False),))
    db.execute("INSERT INTO classes VALUES('c','기존 반','1234',0)")
    db.execute("INSERT INTO students(token,class_id,student_id,name,answers,submitted,exam_json,manual_scores) VALUES(?,?,?,?,?,?,?,?)",('test','c','1001','학생',json.dumps(answers), '2026-11-01T00:00:00Z',json.dumps(exam),json.dumps({'16':4})))
   subprocess.run(command,cwd=Path(__file__).parent,env=env,check=True)
   with sqlite3.connect(Path(folder)/'exam.sqlite3') as db:
    current=json.loads(db.execute("SELECT value FROM settings WHERE key='exam'").fetchone()[0]);self.assertEqual(current[-1]['expected'],RELATIONSHIP_EXPECTED)
    row=db.execute("SELECT answers,exam_json,manual_scores FROM students WHERE token='test'").fetchone();frozen=json.loads(row[1]);self.assertEqual(frozen[-1]['expected'],exam[-1]['expected'])
    result=grade(json.loads(row[0]),questions=frozen,manual_scores=json.loads(row[2]));self.assertEqual(result['essay'],4);self.assertEqual(result['suggestedEssay'],5)
if __name__=='__main__':unittest.main(verbosity=2)
