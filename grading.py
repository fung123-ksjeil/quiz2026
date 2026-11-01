"""Teacher-only answer key and transparent, editable heuristic essay suggestions."""
import re
KEY=[1,1,5,3,1,2,5,4,3,1,1,5,4,2,2]
FIELDS=('government','citizen')
def essay_parts(answer):
 if isinstance(answer,dict):return {key:answer.get(key,'') for key in FIELDS}
 return {'government':'','citizen':''}
RELATIONSHIP_EXPECTED={
 'government':'우리나라 정부가 북한과의 관계 개선을 위해 노력한다는 취지이면 폭넓게 인정합니다. 대화·협상·외교·교류·협력·인도적 지원·공동 사업·긴장 완화·신뢰 형성 등 다양한 방법을 인정하며 같은 표현을 쓸 필요는 없습니다.',
 'citizen':'우리 시민 또는 시민단체가 국내외 활동을 통해 북한과의 관계 개선을 위해 노력한다는 취지이면 폭넓게 인정합니다. 이해·연구·교육·홍보·편견 해소·민간 교류·문화·체육 활동·모금·기부·지원·캠페인·정부에 평화적 해결 요구 등 다양한 방법을 인정합니다.'
}
def relationship_question(question):
 if question.get('options'):return False
 if question.get('rubric') in ['international','relationship_broad']:return True
 return question.get('id')==16 and '북한' in question.get('body','') and any(w in question.get('title','') for w in ['갈등','남북','관계'])

def aligned(text,side):
 # Both answer fields already supply the actor and North-Korea context. Do not
 # require students to repeat those nouns or reproduce the example wording.
 text=re.sub(r'[^가-힣a-zA-Z0-9]','',text)
 if side=='citizen' and re.search(r'(?:정부|국가)(?:가|는)',text) and not any(w in text for w in ['시민','단체','민간','요구','요청','촉구','건의','청원','참여','돕','도와']):return False
 if side=='government' and re.search(r'(?:시민|시민단체|시민들|민간단체)(?:가|는|이)',text) and not any(w in text for w in ['정부','국가','우리나라']):return False
 # Explicitly rejecting cooperation or advocating hostility is not a positive
 # relationship-improvement proposal. This remains a transparent heuristic.
 check=re.sub(r'(공격|전쟁|무력|폭력|도발)(?:을|를)?(?:하지않고|하지말고|하지않으며|대신|없이)','',text)
 check=re.sub(r'(대화|협상|교류|협력|지원|외교)(?:을|를|는|도)?(?:중단|거부|끊|차단)(?:하지않|지않|하지말|지말)',r'\1',check)
 negative=[r'(?:대화|협상|교류|협력|지원|외교)(?:을|를|는|도)?(?:하지않|하지말|안하|거부|끊|금지|차단|필요없)',r'(?:관계|사이)(?:를|가)?(?:악화|단절)',r'(?:공격|전쟁|무력통일|침공)(?:을|를)?(?:하|해|해야|준비|시작|일으|진행)',r'북한(?:을|를)(?:없애|공격|침공|무너뜨)',r'친해질필요없']
 if any(re.search(pattern,check) for pattern in negative):return False
 goals=['관계개선','관계회복','관계를개선','관계를회복','관계가좋','관계가나아','사이를좋','좋은사이','좋은관계','친해지','친해져','친해질','친하게','가까워지','다가가','다가간','우호','친선','친목','화해','화합','공존','평화','통일','긴장완화','갈등완화','갈등해결','오해를풀','오해를줄','신뢰를쌓','신뢰를형성','신뢰구축','믿음을쌓']
 if any(word in text for word in goals):return True
 if re.search(r'(?:관계|사이).{0,6}(?:좋|개선|회복|가까|나아)',text):return True
 if re.search(r'(?:긴장|갈등|분쟁).{0,8}(?:낮추|줄이|줄여|완화|해소|해결)',text):return True
 actions=['대화','협상','협의','외교','회담','교류','지원','원조','협력','협동','소통','교역','무역','인도적지원','이산가족상봉','공동사업','서로돕','도와주','도와준','도움을주','도움을준','도움을제공','돕는다','돕기','모금','기부','봉사','캠페인','평화행진']
 if any(word in text for word in actions):return True
 topics=['북한','남북','동포','민족','상대','서로','역사','문화','통일']
 learning=['이해','존중','알기','알아','알리','알려','연구','교육','공부','배우','배워','홍보','편견을버','편견을없','편견없이','인식개선']
 if any(word in text for word in topics) and any(word in text for word in learning):return True
 objects=['경제','식량','쌀','식품','의약품','약품','의료','보건','구호','재난','물품','문화','스포츠','체육','축구','경기','음악','예술','공연','학생','청소년','인도적','이산가족']
 efforts=['지원','보내','보낸','제공','돕','도와','도움','함께','같이','공동','개최','주최','연다','열어','열고','교환','방문','초청','만남','왕래']
 return any(word in text for word in objects) and any(word in text for word in efforts)
def essay_suggestion(answer):
 if isinstance(answer,str) and answer.strip():return 3,'이전 형식의 통합 답안입니다. 교사가 두 차원의 내용을 확인해 주세요.'
 parts=essay_parts(answer);written=[bool(parts[k].strip()) for k in FIELDS];matches=[aligned(parts[k],k) if written[i] else False for i,k in enumerate(FIELDS)]
 if all(written):
  if all(matches):return 5,'정부와 시민 두 차원 모두 관계 개선을 위한 노력의 취지로 폭넓게 인정했습니다. 교사가 문맥을 최종 확인해 주세요.'
  if any(matches):return 4,'두 차원을 작성했고 한 차원에서 관계 개선을 위한 노력의 취지가 확인됩니다. 다양한 다른 표현도 교사가 인정할 수 있습니다.'
  return 3,'두 차원 모두 작성하여 기본 3점을 제안합니다. 다른 타당한 표현은 교사가 상향 조정할 수 있습니다.'
 if any(written):return (2 if any(matches) else 1),'한 차원만 작성했습니다. 교사가 내용을 확인해 주세요.'
 return 0,'두 차원의 답안이 비어 있습니다.'
def grade(answers,manual=None,questions=None,manual_scores=None):
 if questions is None:
  questions=[{'id':i+1,'options':['']*5,'correct':key,'points':1} for i,key in enumerate(KEY)]+[{'id':16,'options':[],'points':5,'rubric':'international'}]
 items=[];essays=[];manual_scores=manual_scores or {}
 for q in questions:
  identifier=str(q['id']);points=q.get('points',1)
  if q.get('options'):
   items.append({'id':q['id'],'answer':answers.get(identifier),'correct':q['correct'],'score':points if answers.get(identifier)==q['correct'] else 0,'maximum':points})
  else:
   answer=answers.get(identifier)
   if relationship_question(q):suggestion,reason=essay_suggestion(answer)
   else:
    parts=essay_parts(answer);written=[bool(parts[k].strip()) for k in FIELDS]
    hits=[any(word.replace(' ','') in parts[k].replace(' ','') for word in q.get('keywords',{}).get(k,[])) for k in FIELDS]
    suggestion=(5 if all(hits) else 4 if any(hits) else 3) if all(written) else (2 if any(hits) else 1) if any(written) else 0
    reason='두 답란의 작성 여부와 교사가 입력한 핵심어를 기준으로 제안했습니다. 예상 답안과 문맥을 교사가 확인해 주세요.'
   suggestion=round(suggestion*points/5)
   edited=manual_scores.get(identifier,manual if q['id']==16 else None)
   final=min(points,max(0,edited)) if edited is not None else suggestion
   essays.append({'id':q['id'],'suggested':suggestion,'score':final,'maximum':points,'manual':edited is not None,'reason':reason,'expected':RELATIONSHIP_EXPECTED if relationship_question(q) else q.get('expected',{}),'fields':q.get('essayFields',[{'key':'government','label':'1) 답안'},{'key':'citizen','label':'2) 답안'}])})
 objective=sum(i['score'] for i in items);essay=sum(e['score'] for e in essays)
 return {'items':items,'essays':essays,'objective':objective,'objectiveMaximum':sum(i['maximum'] for i in items),'essay':essay,'essayMaximum':sum(e['maximum'] for e in essays),'suggestedEssay':sum(e['suggested'] for e in essays),'manual':any(e['manual'] for e in essays),'reason':' '.join(e['reason'] for e in essays),'total':objective+essay,'maximum':sum(q.get('points',1) for q in questions)}
