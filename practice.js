(()=>{'use strict';
const $=id=>document.getElementById(id),BATCH_SIZE=10;
let questions=[],index=0,batchIndex=0,correctCount=0,completed=0,correctStreak=0,wrongStreak=0,answered=false,phase='question',outcomes=[];
const el=(tag,text)=>{const node=document.createElement(tag);node.textContent=text;return node;};
async function api(path,data){const response=await fetch(path,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined,cache:'no-store'});const result=await response.json();if(!response.ok)throw Error(result.error);return result;}
const startIndex=()=>batchIndex*BATCH_SIZE;
const endIndex=()=>Math.min(startIndex()+BATCH_SIZE,questions.length);
const batchCount=()=>Math.ceil(questions.length/BATCH_SIZE);
const batchScore=()=>outcomes.slice(startIndex(),endIndex()).filter(Boolean).length;
function progress(){const size=endIndex()-startIndex(),done=Math.max(0,Math.min(size,completed-startIndex()));$('practiceProgress').textContent=`${batchIndex+1}/${batchCount()}묶음 · ${done}/${size}문제 완료 · 이번 정답 ${batchScore()}개`;}
function bringIntoView(node){requestAnimationFrame(()=>{const box=node.getBoundingClientRect();if(box.top<0||box.bottom>innerHeight){node.scrollIntoView({block:box.height>innerHeight?'start':'nearest',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}});}
function reset(){index=0;batchIndex=0;correctCount=0;completed=0;correctStreak=0;wrongStreak=0;outcomes=[];renderQuestion();}
function renderBatchResult(){
 phase='summary';progress();$('practiceQuestions').replaceChildren();
 const size=endIndex()-startIndex(),last=endIndex()===questions.length,card=el('section','');
 card.className='admin-card practice-complete practice-batch-result';card.tabIndex=-1;
 card.append(el('span',`${batchIndex+1}번째 묶음 완료`),el('h2',`${size}문제 중 ${batchScore()}개 맞혔어!`));
 const score=el('p',`${batchScore()} / ${size}`);score.className='batch-score';card.append(score);
 card.append(el('p',last?'끝까지 풀었네! 수고했어.':'잠깐 쉬었다가 다음 묶음으로 가보자.'));
 const history=el('div','');history.className='batch-history';
 for(let i=0;i<=batchIndex;i++){const from=i*BATCH_SIZE,to=Math.min(from+BATCH_SIZE,questions.length),correct=outcomes.slice(from,to).filter(Boolean).length;history.append(el('span',`${i+1}묶음 ${correct}/${to-from}`));}
 card.append(history,el('p',`누적 ${completed}문제 중 ${correctCount}개 정답`));
 const action=el('button',last?'처음부터 다시 풀기':`다음 ${Math.min(BATCH_SIZE,questions.length-endIndex())}문제 풀기`);action.className='primary';action.id='continuePractice';
 action.onclick=()=>{if(last)reset();else{batchIndex++;index=startIndex();renderQuestion();}bringIntoView($('practiceQuestions'));};
 card.append(action);$('practiceQuestions').append(card);card.focus({preventScroll:true});bringIntoView(card);
}
function renderQuestion(){
 phase='question';answered=false;$('practiceQuestions').replaceChildren();$('practiceNotice').textContent='';progress();
 const question=questions[index],card=el('section','');card.className='practice-question admin-card';
 const prompt=el('div','');prompt.className='practice-prompt';prompt.append(el('span',`${batchIndex+1}번째 묶음 · 문제 ${index-startIndex()+1} / ${endIndex()-startIndex()}`),el('h2',question.statement));
 const choices=el('div','');choices.className='ox-choices';prompt.append(choices);
 const answerPanel=el('div','');answerPanel.className='practice-answer';
 const placeholder=el('div','O 또는 X를 고르면 정답과 해설이 여기에 나와.');placeholder.className='feedback-placeholder';
 const feedback=el('div','');feedback.className='practice-feedback';feedback.hidden=true;feedback.tabIndex=-1;feedback.setAttribute('role','status');
 const batchEnd=index+1===endIndex(),next=el('button',batchEnd?`이번 ${endIndex()-startIndex()}문제 결과 보기`:'다음 문제 →');next.type='button';next.className='primary next-practice';next.id='nextPractice';next.hidden=true;
 next.onclick=()=>{if(!answered||phase!=='question')return;if(batchEnd)renderBatchResult();else{index++;renderQuestion();bringIntoView($('practiceQuestions'));}};
 for(const answer of ['O','X']){
  const button=el('button',answer);button.type='button';button.dataset.answer=answer;button.setAttribute('aria-label',`${index+1}번 ${answer} 선택`);
  button.onclick=async()=>{
   if(answered)return;choices.querySelectorAll('button').forEach(b=>b.disabled=true);
   try{
    const result=await api('/api/practice/check',{id:question.id,answer});answered=true;completed++;outcomes[index]=result.isCorrect;
    if(result.isCorrect){correctCount++;correctStreak++;wrongStreak=0;}else{wrongStreak++;correctStreak=0;}progress();
    const count=result.isCorrect?correctStreak:wrongStreak,emojis=el('div','');emojis.className='feedback-emojis';emojis.setAttribute('role','img');emojis.setAttribute('aria-label',`${result.isCorrect?'정답':'오답'} ${count}문제 연속`);
    for(let i=0;i<count;i++){const emoji=el('span',result.isCorrect?'😊':'🤔');emoji.setAttribute('aria-hidden','true');emojis.append(emoji);}
    const badge=el('span',result.isCorrect?'✓ 정답':'다시 확인!');badge.className='feedback-badge';
    const explanation=el('p',result.explanation);explanation.className='answer-explanation';
    feedback.append(badge,emojis,el('p',`정답: ${result.correct}`),explanation,el('p',`관련 자료: ${result.source.file} · 교과서 ${result.source.page}쪽`));
    feedback.classList.toggle('incorrect',!result.isCorrect);placeholder.hidden=true;feedback.hidden=false;next.hidden=false;
    button.setAttribute('aria-pressed','true');choices.querySelector(`[data-answer="${result.correct}"]`).classList.add('answer-correct');if(!result.isCorrect)button.classList.add('answer-incorrect');
    feedback.focus({preventScroll:true});bringIntoView(answerPanel);
   }catch(error){$('practiceNotice').textContent=error.message;choices.querySelectorAll('button').forEach(b=>b.disabled=false);}
  };
  choices.append(button);
 }
 answerPanel.append(placeholder,feedback,next);card.append(prompt,answerPanel);$('practiceQuestions').append(card);
}
async function start(){try{const result=await api('/api/practice');questions=result.questions;if(!questions.length){$('practiceProgress').textContent='공개된 연습문제 0개';$('practiceQuestions').append(el('section','현재 공개된 연습문제가 없습니다.'));return;}renderQuestion();}catch(error){$('practiceNotice').textContent=error.message;}}
start();})();
