'use strict';
const $ = id => document.getElementById(id);
const roles = [
  ['Retrieval Agent','Searches the policy knowledge base','rag_lookup'],
  ['Lookup Agent','Reads synthetic appointment records','check_appointment_status'],
  ['Response Composer','Combines available evidence',null],
  ['PolicyComplianceReviewer','Checks the draft against evidence',null],
  ['FinalEditor','Returns a structured review verdict',null]
];
let session = crypto.randomUUID(), busy = false, lastQuery = '', policies = [];
const welcome = $('welcome').cloneNode(true);
function node(tag, className, text) { const n = document.createElement(tag); if(className)n.className=className; if(text!==undefined)n.textContent=text; return n; }
function renderAgents(result) {
  $('agents').replaceChildren();
  roles.forEach(([role,description,tool],index) => {
    const ran = result?.executed_agents.includes(role);
    const item = node('div','agent'+(ran?' ran':''));
    item.append(node('span','agent-icon',ran?'✓':String(index+1).padStart(2,'0')));
    const copy=node('div');
    copy.append(node('strong','',role.replace('PolicyComplianceReviewer','Policy reviewer').replace('FinalEditor','Final editor')));
    let detail=description;
    if(result)detail=result.cache_hit?'Not run · cached response':ran?(tool?(result.executed_tools.includes(tool)?'Tool executed · '+tool:'Task ran · no lookup requested'):'Executed'):'Not executed';
    copy.append(node('small','',detail));item.append(copy);$('agents').append(item);
  });
}
function openPolicy(id){const policy=policies.find(p=>p.id===id);if(!policy)return;$('policyTitle').textContent=policy.title;$('policyText').textContent=policy.text;$('policyDialog').showModal();}
function sourceButton(id){const p=policies.find(x=>x.id===id),b=node('button','source',p?.title||id.replaceAll('_',' '));b.type='button';b.addEventListener('click',()=>openPolicy(id));return b;}
function inspect(result){renderAgents(result);$('runState').textContent=result.cache_hit?'Cache hit · no agents re-executed':result.outcome==='blocked'?'Blocked before agent execution':result.outcome==='budget_exceeded'?'Request budget exceeded':result.outcome==='fallback'?'Completed · clarification or fallback':'Completed · evidence reviewed';$('latency').textContent=result.elapsed_ms<1000?Math.round(result.elapsed_ms)+' ms':(result.elapsed_ms/1000).toFixed(2)+' s';$('cache').textContent=result.cache_hit?'Hit':'Miss';$('budget').textContent=result.budget_units.toLocaleString()+' / 32,000';$('sources').replaceChildren();if(result.response_format.citations.length)result.response_format.citations.forEach(id=>$('sources').append(sourceButton(id)));else $('sources').append(node('p','muted',result.response_format.lookup?'Answer based on the synthetic appointment dataset.':'No policy cited for this response.'));}
function userMessage(text){const m=node('div','message user');m.append(node('div','bubble',text));$('messages').append(m);return m;}
function answerMessage(r){const m=node('div','message assistant');m.append(node('div','message-label','CAREDESK / ASSISTANT'),node('div','bubble',r.response_format.answer));const lookup=r.response_format.lookup;if(lookup?.found){const card=node('div','record-card');for(const [label,value] of [['Appointment',lookup.record_id],['Status',lookup.status],['Recorded fee','₹'+lookup.consultation_fee_inr.toLocaleString('en-IN')]]){const cell=node('div');cell.append(node('small','',label),node('strong','',value));card.append(cell);}m.append(card);}const tags=node('div','answer-meta');if(r.review)tags.append(node('span','tag',r.cache_hit?'Previously reviewed · cached':r.review.approved?'✓ Review approved':'✓ Draft revised'));if(r.outcome!=='answered')tags.append(node('span','tag warning',r.outcome.replaceAll('_',' ')));if(r.masked_input.includes('[PHONE_MASKED]'))tags.append(node('span','tag','Phone number masked'));r.response_format.citations.forEach(id=>tags.append(sourceButton(id)));m.append(tags);const details=node('details');details.style.marginTop='12px';const summary=node('summary','muted','Response details');details.append(summary,node('p','muted','Trace: '+r.trace_id));if(r.review)details.append(node('p','muted',r.review.reason));m.append(details);$('messages').append(m);}
function setBusy(value){busy=value;$('send').disabled=value;$('reset').disabled=value;document.querySelectorAll('[data-query],#repeat').forEach(b=>b.disabled=value);}
async function send(query){query=query.trim();if(!query||busy)return;$('welcome')?.remove();lastQuery=query;const message=userMessage(query.replace(/(?<!\w)(?:\+?91[\s-]?)?[6-9](?:[\s-]?\d){9}(?!\w)/g,'[PHONE_MASKED]'));$('query').value='';setBusy(true);renderAgents();$('latency').textContent=$('cache').textContent=$('budget').textContent='—';$('sources').replaceChildren(node('p','muted','Waiting for this request’s evidence.'));const pending=node('div','pending','Checking clinic evidence and preparing a reviewed answer…');$('messages').append(pending);$('messages').scrollTop=$('messages').scrollHeight;$('runState').textContent='Request running · waiting for actual execution results';try{const response=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,session_id:session})});if(!response.ok)throw new Error('The request could not be completed ('+response.status+'). Please try again.');const result=await response.json();message.querySelector('.bubble').textContent=result.masked_input;pending.remove();answerMessage(result);inspect(result);}catch(error){pending.textContent=error.message||'Connection interrupted. Please try again.';pending.classList.add('error');$('runState').textContent='Request failed · no completion claimed';}finally{setBusy(false);$('messages').scrollTop=$('messages').scrollHeight;$('query').focus();}}
document.addEventListener('click',e=>{const button=e.target.closest('[data-query]');if(button)send(button.dataset.query);});
$('composer').addEventListener('submit',e=>{e.preventDefault();send($('query').value);});
$('query').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();send($('query').value);}});
$('repeat').addEventListener('click',()=>{if(lastQuery)send(lastQuery);else{$('query').focus();$('runState').textContent='Ask a question first, then repeat it to test caching.';}});
$('reset').addEventListener('click',()=>{session=crypto.randomUUID();lastQuery='';$('messages').replaceChildren(welcome.cloneNode(true));renderAgents();$('latency').textContent=$('cache').textContent=$('budget').textContent='—';$('sources').replaceChildren(node('p','muted','Policy references will appear here.'));$('runState').textContent='New session · no previous appointment context';$('query').value='';$('query').focus();});
$('closeDialog').addEventListener('click',()=>$('policyDialog').close());
$('policyDialog').addEventListener('click',e=>{if(e.target===$('policyDialog')){const r=$('policyDialog').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('policyDialog').close();}});
function view(overview){$('overviewView').hidden=!overview;$('chatView').hidden=overview;$('overviewNav').classList.toggle('active',overview);$('chatNav').classList.toggle('active',!overview);}
$('overviewNav').addEventListener('click',()=>view(true));$('chatNav').addEventListener('click',()=>view(false));renderAgents();
Promise.all([fetch('/health').then(r=>{if(!r.ok)throw Error();return r.json();}),fetch('/policies').then(r=>{if(!r.ok)throw Error();return r.json();})]).then(([health,docs])=>{policies=docs;$('health').textContent=health.status==='ok'?'● Backend connected':'Backend unavailable';}).catch(()=>{$('health').textContent='Backend unavailable';$('runState').textContent='Connection unavailable · reload to reconnect';});
