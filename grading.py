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
def grade(answers,manual=None):
 items=[{'id':i+1,'answer':answers.get(str(i+1)),'correct':key,'score':int(answers.get(str(i+1))==key)} for i,key in enumerate(KEY)]
 objective=sum(q['score'] for q in items);suggestion,reason=essay_suggestion(answers.get('16'));essay=manual if manual is not None else suggestion
 return {'items':items,'objective':objective,'suggestedEssay':suggestion,'essay':essay,'manual':manual is not None,'reason':reason,'total':objective+essay,'maximum':20}
