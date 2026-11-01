"""Teacher-only answer key and transparent, editable heuristic essay suggestions."""
import re
KEY=[1,1,5,3,1,2,5,4,3,1,1,5,4,2,2]
FIELDS=('government','citizen')
def essay_parts(answer):
 if isinstance(answer,dict):return {key:answer.get(key,'') for key in FIELDS}
 return {'government':'','citizen':''}
def aligned(text,side):
 text=re.sub(r'\s+','',text)
 if side=='government':
  return any(w in text for w in ['대화','협상','외교','회담','경제협력','경제적활동','경제활동','경제교류','경제적교류','경제협동','공동경제','교역','무역','교류협력','남북교류'])
 return (any(w in text for w in ['북한','남북','동포']) and any(w in text for w in ['이해','알기','알아','알리','연구','교육','인식','같은민족','한민족','같은동포','바로알','민족이라는'])) or ('정부' in text and any(w in text for w in ['대화','평화','협상']) and any(w in text for w in ['요구','촉구','요청','건의']))
def essay_suggestion(answer):
 if isinstance(answer,str) and answer.strip():return 3,'이전 형식의 통합 답안입니다. 교사가 두 차원의 내용을 확인해 주세요.'
 parts=essay_parts(answer);written=[bool(parts[k].strip()) for k in FIELDS];matches=[aligned(parts[k],k) if written[i] else False for i,k in enumerate(FIELDS)]
 if all(written):
  if all(matches):return 5,'두 차원 모두 예상 답안의 핵심 표현과 연결됩니다. 문맥을 확인해 주세요.'
  if any(matches):return 4,'두 차원을 작성했고 한 차원에서 예상 답안의 핵심 표현이 확인됩니다.'
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
   if q.get('rubric','international')=='international':suggestion,reason=essay_suggestion(answer)
   else:
    parts=essay_parts(answer);written=[bool(parts[k].strip()) for k in FIELDS]
    hits=[any(word.replace(' ','') in parts[k].replace(' ','') for word in q.get('keywords',{}).get(k,[])) for k in FIELDS]
    suggestion=(5 if all(hits) else 4 if any(hits) else 3) if all(written) else (2 if any(hits) else 1) if any(written) else 0
    reason='두 답란의 작성 여부와 교사가 입력한 핵심어를 기준으로 제안했습니다. 예상 답안과 문맥을 교사가 확인해 주세요.'
   suggestion=round(suggestion*points/5)
   edited=manual_scores.get(identifier,manual if q['id']==16 else None)
   final=min(points,max(0,edited)) if edited is not None else suggestion
   essays.append({'id':q['id'],'suggested':suggestion,'score':final,'maximum':points,'manual':edited is not None,'reason':reason,'expected':q.get('expected',{}),'fields':q.get('essayFields',[{'key':'government','label':'1) 답안'},{'key':'citizen','label':'2) 답안'}])})
 objective=sum(i['score'] for i in items);essay=sum(e['score'] for e in essays)
 return {'items':items,'essays':essays,'objective':objective,'objectiveMaximum':sum(i['maximum'] for i in items),'essay':essay,'essayMaximum':sum(e['maximum'] for e in essays),'suggestedEssay':sum(e['suggested'] for e in essays),'manual':any(e['manual'] for e in essays),'reason':' '.join(e['reason'] for e in essays),'total':objective+essay,'maximum':sum(q.get('points',1) for q in questions)}
