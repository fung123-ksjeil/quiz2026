"""Editable content validation and source-grounded practice explanation drafts."""
import json,re
from pathlib import Path
from grading import KEY, RELATIONSHIP_EXPECTED
ROOT=Path(__file__).resolve().parent
TOPICS=json.loads((ROOT/'reference_topics.json').read_text())
def default_exam():
 questions=json.loads((ROOT/'questions.json').read_text())
 for q in questions:
  q['kind']='choice' if q['options'] else 'essay'
  if q['options']:q['correct']=KEY[q['id']-1]
  else:
   q['rubric']='relationship_broad';q['expected']=dict(RELATIONSHIP_EXPECTED)
   q['keywords']={'government':['대화','외교','경제','협상','회담'],'citizen':['북한','민족','연구','홍보','교육','대화']}
 return questions

def public_question(q):return {k:v for k,v in q.items() if k not in ['correct','expected','keywords','rubric']}
def clean_text(value,label,limit=10000,required=False):
 if not isinstance(value,str) or len(value)>limit or (required and not value.strip()):raise ValueError(label+'을(를) 확인하세요.')
 return value.strip()
def validate_question(data,identifier):
 kind=data.get('kind','choice');points=data.get('points',1)
 if kind not in ['choice','ox','essay'] or type(points) is not int or not 1<=points<=20:raise ValueError('문항 유형과 배점(1~20점)을 확인하세요.')
 q={'id':identifier,'kind':kind,'title':clean_text(data.get('title',''),'문제',1000,True),'body':clean_text(data.get('body',''),'보기 내용'),'points':points,'options':[]}
 if kind!='essay':
  options=['O','X'] if kind=='ox' else data.get('options')
  if not isinstance(options,list) or not 2<=len(options)<=5:raise ValueError('선택지는 2~5개로 입력하세요.')
  q['options']=[clean_text(o,'선택지',2000,True) for o in options]
  if type(data.get('correct')) is not int or not 1<=data['correct']<=len(options):raise ValueError('정답 번호를 확인하세요.')
  q['correct']=data['correct']
  if data.get('optionHeaders') and data.get('optionColumns'):
   headers=data['optionHeaders'];cols=data['optionColumns']
   if not isinstance(headers,list) or len(headers)!=2 or not isinstance(cols,list) or len(cols)!=len(options):raise ValueError('선택지 열 구성을 확인하세요.')
   q['optionHeaders']=[clean_text(x,'열 제목',30,True) for x in headers];q['optionColumns']=[]
   for row in cols:
    if not isinstance(row,list) or len(row)!=2:raise ValueError('선택지 열 구성을 확인하세요.')
    q['optionColumns'].append([clean_text(x,'열 내용',1000,True) for x in row])
 else:
  labels=data.get('labels',['1) 답안','2) 답안']);expected=data.get('expected',{});keywords=data.get('keywords',{})
  if not isinstance(labels,list) or len(labels)!=2 or not isinstance(expected,dict) or not isinstance(keywords,dict):raise ValueError('서술형 입력란을 확인하세요.')
  q['essayFields']=[{'key':key,'label':clean_text(labels[i],'답란 이름',100,True)} for i,key in enumerate(['government','citizen'])]
  q['expected']={k:clean_text(expected.get(k,''),'예상 답안',5000) for k in ['government','citizen']}
  q['keywords']={}
  for k in ['government','citizen']:
   words=keywords.get(k,[])
   if not isinstance(words,list) or len(words)>30:raise ValueError('핵심어는 답란별 30개 이내로 입력하세요.')
   q['keywords'][k]=[clean_text(w,'핵심어',80,True) for w in words]
  q['rubric']='keywords'
 return q

def explanation_draft(statement,correct,topic_id=''):
 statement=clean_text(statement,'O/X 문제',2000,True)
 if correct not in ['O','X']:raise ValueError('정답 O 또는 X를 선택하세요.')
 topic=next((t for t in TOPICS if t['id']==topic_id),None)
 if topic_id and topic is None:raise ValueError('자료 주제를 다시 선택하세요.')
 if topic is None:
  ranked=sorted([(sum(len(w) for w in t['keywords'] if w in statement),t['id'],t) for t in TOPICS],key=lambda x:x[0],reverse=True)
  if not ranked or ranked[0][0]==0:raise ValueError('관련 자료 주제를 선택하세요. 자료에 없는 내용을 자동으로 만들지 않습니다.')
  topic=ranked[0][2]
 text=(f"정답은 {correct}입니다. "+topic['explanation'])
 return {'explanation':text,'topicId':topic['id'],'source':topic['source'],'reviewRequired':True}
