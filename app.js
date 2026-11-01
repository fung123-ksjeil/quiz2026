'use strict';
const $=id=>document.getElementById(id);let questions=[],state={answers:{}},active=false,rendered=false,timer,dirty=false,saving=false;
async function api(url,data){const r=await fetch(url,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined,cache:'no-store'});const v=await r.json();if(!r.ok){const e=new Error(v.error);e.status=r.status;throw e;}return v;}
function hidePaper(message){active=false;rendered=false;$('questions').replaceChildren();$('nav').replaceChildren();$('workspace').hidden=true;$('entry').hidden=true;$('locked').hidden=false;$('lockMessage').textContent=message;$('privacy').hidden=true;}
function hasAnswer(q){const a=state.answers[q.id];return q.options.length?Number.isInteger(a):q.essayFields?q.essayFields.every(f=>typeof a?.[f.key]==='string'&&a[f.key].trim()):typeof a==='string'&&!!a.trim();}
function progress(){const count=questions.filter(hasAnswer).length;$('count').textContent=`${count} / ${questions.length}문항 작성`;$('progress').max=questions.length;$('progress').value=count;questions.forEach(q=>$(`nav${q.id}`)?.classList.toggle('done',hasAnswer(q)));}
function save(){dirty=true;$('saveStatus').textContent='저장 중…';progress();clearTimeout(timer);timer=setTimeout(flush,350);}
async function flush(){if(!dirty||saving||!active)return;saving=true;const snapshot=JSON.stringify(state.answers);try{await api('/api/answers',{answers:JSON.parse(snapshot)});dirty=JSON.stringify(state.answers)!==snapshot;$('saveStatus').textContent=dirty?'저장 중…':'서버 임시 저장 완료 · 최종 제출 시 보관';}catch(e){$('saveStatus').textContent='저장 실패 · 연결 후 자동 재시도';if([401,423,409].includes(e.status))hidePaper(e.message);}finally{saving=false;if(dirty&&active)timer=setTimeout(flush,1500);}}
function render(){
 const circles=['①','②','③','④','⑤'];
 for(const q of questions){
  const field=document.createElement('fieldset');field.id=`q${q.id}`;
  const legend=document.createElement('legend');
  const n=document.createElement('span');n.className='num';n.textContent=`QUESTION ${String(q.id).padStart(2,'0')}`;
  const points=document.createElement('span');points.className='points';points.textContent=` [${q.points??(q.id===16?5:1)}점]`;
  legend.append(n,document.createTextNode(q.title),points);field.append(legend);
  const area=document.createElement('div');
  if(q.body){
   const passage=document.createElement('p');passage.className='passage';passage.textContent=q.body;
   if(q.id===12&&q.body.includes('이것')){const parts=q.body.split('이것');passage.textContent=parts[0];const u=document.createElement('u');u.textContent='이것';passage.append(u,document.createTextNode(parts.slice(1).join('이것')));}
   area.append(passage);
  }
  if(q.options.length){
   if(q.optionHeaders){
    const heading=document.createElement('div');heading.className='option-heading';heading.setAttribute('aria-hidden','true');
    heading.append(document.createElement('span'));
    for(const title of q.optionHeaders){const cell=document.createElement('span');cell.textContent=title;heading.append(cell);}
    area.append(heading);
   }
   q.options.forEach((option,i)=>{
    const label=document.createElement('label');label.className='option'+(q.optionColumns?' paired-option':'');
    const input=document.createElement('input');input.type='radio';input.name=`answer${q.id}`;input.value=i+1;input.checked=state.answers[q.id]===i+1;
    input.addEventListener('change',()=>{state.answers[q.id]=i+1;save();});
    const number=document.createElement('span');number.className='choice-number';number.textContent=circles[i];
    label.append(input,number);
    if(q.optionColumns){q.optionColumns[i].forEach((text,column)=>{const cell=document.createElement('span');cell.textContent=text;label.append(cell);});input.setAttribute('aria-label',`${i+1}번, ${q.optionHeaders.map((h,j)=>h+' '+q.optionColumns[i][j]).join(', ')}`);}
    else{const text=document.createElement('span');text.textContent=option;label.append(text);}
    area.append(label);
   });
  }else{
   const current=state.answers[q.id];
   if(typeof current==='string'&&current.trim()){const legacy=document.createElement('p');legacy.className='passage';legacy.textContent='이전에 작성한 통합 답안: '+current+' — 아래 두 입력란으로 나누어 작성해 주세요.';area.append(legacy);}
   for(const f of q.essayFields){
    const label=document.createElement('label');label.className='essay-label';label.textContent=f.label;
    const input=document.createElement('textarea');input.name=`answer${q.id}_${f.key}`;input.value=typeof current==='object'?current?.[f.key]||'':'';input.maxLength=10000;input.placeholder=f.label+'에 대한 답안을 입력하세요.';
    input.addEventListener('input',()=>{if(!state.answers[q.id]||typeof state.answers[q.id]!=='object')state.answers[q.id]={};state.answers[q.id][f.key]=input.value;save();});label.append(input);area.append(label);
   }
  }
  field.append(area);$('questions').append(field);
  const link=document.createElement('a');link.href=`#q${q.id}`;link.textContent=q.id;link.id=`nav${q.id}`;link.setAttribute('aria-label',`${q.id}번 문항`);$('nav').append(link);
 }
 progress();
}
async function load(){try{const d=await api('/api/exam');$('entry').hidden=true;$('locked').hidden=true;$('notice').textContent='';if(d.submitted){$('resultMessage').textContent=d.pendingSync?'답안은 서버에 접수되었지만 GitHub 보관 확인을 기다리고 있습니다. 이 창을 유지하고 선생님께 알려주세요.':'답안 제출과 보관이 완료되었습니다. 제출 후에는 문항과 답안을 다시 열 수 없습니다.';active=false;$('workspace').hidden=true;$('privacy').hidden=true;$('result').hidden=false;$('questions').replaceChildren();return;}questions=d.questions;if(!dirty)state.answers=d.answers;active=true;$('result').hidden=true;$('workspace').hidden=false;$('studentInfo').textContent=`${d.studentId} · ${d.name}`;if(!rendered){$('questions').replaceChildren();$('nav').replaceChildren();render();rendered=true;}$('saveStatus').textContent=dirty?'아직 저장하지 않은 답안이 있습니다.':'서버 임시 저장 완료 · 최종 제출 시 보관';if(dirty)flush();}catch(e){if(e.status===401){active=false;$('entry').hidden=false;$('workspace').hidden=true;$('locked').hidden=true;}else hidePaper(e.status===423?e.message:'연결을 확인할 수 없어 시험 화면을 잠갔습니다.');}}
$('join').addEventListener('submit',async e=>{e.preventDefault();try{await api('/api/join',{code:$('code').value.trim(),studentId:$('studentId').value,name:$('studentName').value});dirty=false;state.answers={};await load();}catch(e){$('notice').textContent=e.message;}});
$('exam').addEventListener('submit',async e=>{e.preventDefault();if(questions.some(q=>!hasAnswer(q))){$('notice').textContent='모든 문항에 답해 주세요.';return;}if(!confirm('최종 제출할까요? 제출 후에는 수정하거나 시험지를 다시 볼 수 없습니다.'))return;try{clearTimeout(timer);await api('/api/submit',{answers:state.answers});dirty=false;await load();}catch(e){$('notice').textContent=e.message;if(e.status===423)hidePaper(e.message);}});
$('retry').onclick=load;$('fullscreen').onclick=async()=>{try{await document.documentElement.requestFullscreen();}catch{$('notice').textContent='이 브라우저에서는 전체 화면을 사용할 수 없습니다.';}};
let lastEvent=0;
function record(kind){if(!active)return;const now=Date.now();if(now-lastEvent<1000)return;lastEvent=now;api('/api/event',{kind}).catch(()=>{});}
function conceal(){if(!active)return;$('privacy').hidden=false;record('화면 이탈');}
document.addEventListener('visibilitychange',()=>{if(document.hidden)conceal();});window.addEventListener('blur',conceal);
$('resume').onclick=()=>{$('privacy').hidden=true;load();};
document.addEventListener('fullscreenchange',()=>{if(active&&!document.fullscreenElement){record('전체 화면 종료');$('privacy').hidden=false;}});
for(const event of ['copy','cut','contextmenu','dragstart'])document.addEventListener(event,e=>{if(active){e.preventDefault();record('복사 시도');}});
document.addEventListener('paste',e=>{if(active)e.preventDefault();});
document.addEventListener('keydown',e=>{if(!active)return;const k=e.key.toLowerCase();if((e.ctrlKey||e.metaKey)&&['c','x','s','p','u'].includes(k)||e.key==='PrintScreen'){e.preventDefault();record(e.key==='PrintScreen'?'캡처 단축키':k==='p'?'인쇄 시도':'복사 시도');}});
window.addEventListener('beforeprint',()=>{if(active)record('인쇄 시도');});window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
setInterval(load,3000);load();

api('/api/catalog').then(d=>{$('choiceCount').textContent=`객관식 ${d.choice}문항`;$('essayCount').textContent=`서술형 ${d.essay}문항`;}).catch(()=>{});
