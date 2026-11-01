'use strict';const $=id=>document.getElementById(id);let logged=false;
async function api(url,data){const r=await fetch(url,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined,cache:'no-store'});const d=await r.json();if(!r.ok){const e=new Error(d.error);e.status=r.status;throw e;}return d;}
function el(tag,text){const n=document.createElement(tag);n.textContent=text;return n;}
async function deleteRecords(data,name){
 if(!confirm(`${name} 기록을 삭제할까요? 현재 답안·채점·이탈 기록이 삭제됩니다. 반 전체 삭제 시 시험도 잠깁니다. GitHub 커밋 이력은 별도로 남습니다.`))return;
 try{await api('/api/admin/delete',{...data,confirm:'DELETE'});$('message').textContent='현재 기록을 삭제하고 저장했습니다.';await refresh(true);}catch(e){$('message').textContent=e.message;}
}
async function refresh(force=false){try{const d=await api('/api/admin/status');logged=true;$('storageStatus').textContent=d.storage?.mode==='github'?(d.storage.error?'GitHub 동기화 오류 · 잠시 후 다시 확인하세요.':d.storage.pending?'GitHub 보관 대기 중 · 최종 제출과 점수 수정은 즉시 저장합니다.':'GitHub 보관 확인 완료'):'이 컴퓨터에만 저장 중 · 배포 시 GitHub 연결이 필요합니다.';$('login').hidden=true;$('dashboard').hidden=false;$('classes').replaceChildren();for(const c of d.classes){const card=el('section','');card.className='admin-card';card.append(el('h2',c.name),el('p',c.opened?'공개 중':'잠김'));const code=el('p',`응시 코드: ${c.code}`);card.append(code);const share=el('button','시험 링크·코드 복사');share.onclick=async()=>{try{await navigator.clipboard.writeText(`${c.name} 시험\n${location.origin}/\n응시 코드: ${c.code}`);$('message').textContent='배포할 링크와 코드를 복사했습니다.';}catch{$('message').textContent='복사하지 못했습니다. 표시된 코드를 직접 전달하세요.';}};const toggle=el('button',c.opened?'시험 잠그기':'시험 공개');toggle.className='primary';toggle.onclick=async()=>{if(!confirm(`${c.name} 시험을 ${c.opened?'잠글까요? 미제출 학생은 제출할 수 없게 됩니다.':'공개할까요?'}`))return;try{await api('/api/admin/toggle',{id:c.id,opened:!c.opened});await refresh();}catch(e){$('message').textContent=e.message;}};const remove=el('button','이 반의 학생 기록 삭제');remove.type='button';remove.onclick=()=>deleteRecords({scope:'class',classId:c.id},c.name+' 전체 학생');card.append(share,toggle,remove);$('classes').append(card);}if(force||!$('students').querySelector('details[open]')){
 $('students').replaceChildren();if(!d.students.length)$('students').append(el('p','아직 입장한 학생이 없습니다.'));
 for(const s of d.students){
  const c=d.classes.find(c=>c.id===s.class_id),row=el('section','');row.className='admin-card';
  const count=Object.entries(s.answers).filter(([id,a])=>typeof a==='object'?Object.values(a).some(v=>v.trim()):typeof a==='string'?a.trim():a).length;
  row.append(el('h3',`${c?.name||''} · ${s.student_id} ${s.name}`),el('p',`${s.submitted?'제출 완료':'응시 중'} · 작성 ${count}/16 · 이탈·제한 동작 기록 ${s.events.length}건`));
  if(s.grade)row.append(el('p',`총점 ${s.grade.total}/20점 · 객관식 ${s.grade.objective}/15점 · 서술형 ${s.grade.essay}/5점 (${s.grade.manual?'교사 수정 점수':'자동 제안 · 교사 확인 전'})`));
  const detail=el('details','');detail.append(el('summary','답안·채점 결과 및 기록 확인'));
  if(s.grade){
   for(const item of s.grade.items)detail.append(el('p',`${item.id}번: 학생 답 ${item.answer??'미응답'} / 정답 ${item.correct} · ${item.score?'정답':'오답'} [${item.score}/1점]`));
  }else for(const [id,a] of Object.entries(s.answers))if(id!=='16')detail.append(el('p',`${id}번: ${a}`));
  const essay=s.answers['16'];
  if(essay&&typeof essay==='object'){detail.append(el('p','16번 1) 정부(국가) 차원: '+(essay.government||'미작성')),el('p','16번 2) 시민단체(시민) 차원: '+(essay.citizen||'미작성')));}else detail.append(el('p','16번 이전 통합 답안: '+(essay||'미작성')));
  if(s.grade){
   detail.append(el('p',`서술형 자동 제안 ${s.grade.suggestedEssay}/5점: ${s.grade.reason}`),el('p','자동 제안은 핵심 표현을 활용한 참고용 채점입니다. 의미나 문맥을 완전히 이해하지 못하므로 교사가 확인하고 수정해 주세요.'));
   const form=el('form','');form.className='grading-form';const label=el('label','서술형 최종 점수 (0~5점)');const score=document.createElement('input');score.type='number';score.min='0';score.max='5';score.step='1';score.required=true;score.value=s.grade.essay;label.append(score);
   const noteLabel=el('label','채점 메모');const note=document.createElement('textarea');note.maxLength=2000;note.value=s.grade_note||'';noteLabel.append(note);
   const save=el('button','점수 저장');save.type='submit';save.className='primary';const reset=el('button','자동 제안으로 되돌리기');reset.type='button';
   form.append(label,noteLabel,save,reset);detail.append(form);
   form.onsubmit=async e=>{e.preventDefault();try{await api('/api/admin/grade',{recordId:s.recordId,score:Number(score.value),note:note.value});$('message').textContent='서술형 점수를 저장했습니다.';await refresh(true);}catch(e){$('message').textContent=e.message;}};
   reset.onclick=async()=>{if(!confirm('교사 수정 점수를 지우고 자동 제안 점수로 되돌릴까요?'))return;try{await api('/api/admin/grade',{recordId:s.recordId,score:null,note:note.value});await refresh(true);}catch(e){$('message').textContent=e.message;}};
  }
  for(const event of s.events)detail.append(el('p',`${new Date(event.time*1000).toLocaleString('ko-KR')} · ${event.kind}`));
  row.append(detail);const remove=el('button','이 학생 기록 삭제');remove.type='button';remove.onclick=()=>deleteRecords({scope:'student',recordId:s.recordId},s.student_id+' '+s.name);row.append(remove);$('students').append(row);
 }
}}catch(e){if(e.status===401){logged=false;$('login').hidden=false;$('dashboard').hidden=true;$('classes').replaceChildren();$('students').replaceChildren();}else $('message').textContent=e.message;}}
$('loginForm').onsubmit=async e=>{e.preventDefault();try{await api('/api/admin/login',{password:$('password').value});$('password').value='';$('message').textContent='';await refresh();}catch(e){$('message').textContent=e.message;}};
$('newClass').onsubmit=async e=>{e.preventDefault();try{await api('/api/admin/classes',{name:$('className').value});$('className').value='';await refresh();}catch(e){$('message').textContent=e.message;}};
$('logout').onclick=async()=>{try{await api('/api/admin/logout',{});await refresh();}catch(e){$('message').textContent=e.message;}};$('refresh').onclick=()=>refresh(true);setInterval(()=>{if(logged)refresh();},5000);refresh();
