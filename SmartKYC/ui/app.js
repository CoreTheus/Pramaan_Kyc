const $ = id => document.getElementById(id);
const form = $('applicationForm');
let imageData = '', sample = null, current = null, busy = false, parentId = null;
let thresholds = {standard_max: 35, enhanced_max: 70};
const escapeHTML = value => String(value ?? 'Not extracted').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const text = escapeHTML;

async function api(path, body) {
  let response;
  try {
    response = await fetch(path, {method: body === undefined ? 'GET' : 'POST',
      headers: {'Content-Type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(path.includes('verify') ? 270000 : 15000)});
  } catch (error) { throw new Error(error.name === 'TimeoutError' ? 'The request timed out. Check the host before retrying; a case may still finish there.' : 'Cannot reach the host. Check that the server is running and both PCs are on the same WiFi.'); }
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'The host could not complete this request.');
  return data;
}

function showError(error) { $('error').textContent = error.message || error; $('error').hidden = false; }
function clearError() { $('error').hidden = true; }
function setView(queue) {
  $('applicationView').hidden = queue;
  $('queueView').hidden = !queue;
  $('newTab').classList.toggle('active', !queue);
  $('queueTab').classList.toggle('active', queue);
  $('breadcrumb').textContent = queue ? 'Review queue' : 'New application';
  $('pageTitle').textContent = queue ? 'Every decision has a record.' : 'A clear view of every application.';
}

async function connection() {
  try {
    const state = await api('/api/health');
    thresholds = state.thresholds;
    $('connection').textContent = `${state.ollama.ready ? '●' : '○'}  ${state.ollama.message}  ·  Host: ${location.host}  ·  ${state.ollama.model}`;
    $('connection').classList.toggle('warn', !state.ollama.ready);
  } catch (e) { $('connection').textContent = e.message; $('connection').classList.add('warn'); }
}

function readFile(file) {
  return new Promise((resolve, reject) => {
    if (file.size > 10 * 1024 * 1024) return reject(new Error('Image is larger than 10 MB. Choose a smaller photo.'));
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Could not read this file. Try another image.'));
    reader.readAsDataURL(file);
  });
}

function setImage(data, name) {
  imageData = data.split(',')[1];
  $('preview').src = data;
  $('preview').hidden = false;
  $('fileName').textContent = name;
}

function fillInputs(applicant, signals) {
  for (const [key, value] of Object.entries({...applicant, ...signals})) {
    const input = form.elements.namedItem(key);
    if (!input) continue;
    if (input.type === 'checkbox') input.checked = !!value;
    else input.value = value ?? '';
  }
}

async function loadSample(key) {
  if (busy) return;
  clearError();
  try {
    const samples = await api('/api/samples');
    const response = await fetch(`/samples/${key}.png`);
    if (!response.ok) throw new Error('Sample image could not be loaded.');
    const data = await readFile(await response.blob());
    sample = key; parentId = null; current = null;
    fillInputs(samples[key].applicant, samples[key].signals);
    setImage(data, `${key} / fictional sample`);
    $('document').value = '';
    $('parentNote').hidden = true;
    $('result').hidden = true;
    $('emptyState').hidden = false;
    $('rehearsalBox').hidden = false;
    document.querySelectorAll('[data-sample]').forEach(button => button.classList.toggle('selected', button.dataset.sample === key));
    setView(false);
  } catch (e) { showError(e); }
}

function busyState(value) {
  busy = value;
  form.querySelectorAll('input, textarea, button').forEach(input => input.disabled = value);
  document.querySelectorAll('[data-sample], #rehearsalBtn, #newTab, #queueTab').forEach(button => button.disabled = value);
  $('processing').hidden = !value;
  if (value) { $('emptyState').hidden = true; $('result').hidden = true; }
  else if (!current) $('emptyState').hidden = false;
}

function labelSource(source) { return source === 'live_ollama' ? 'LIVE OLLAMA OCR' : 'REHEARSAL · CACHED FIELDS'; }
function badge(risk) { return `<span class="badge ${risk.level.toLowerCase()}">${text(risk.level)} RISK</span>`; }
function formatDate(value) { return new Date(value).toLocaleString([], {dateStyle:'medium',timeStyle:'short'}); }

function renderCase(c) {
  current = c;
  const r = c.risk, v = c.verification;
  const max = Math.max(1, ...r.factors.map(f => Math.abs(f.contribution)));
  const checked = v.checks.filter(check => check.status === 'pass').length;
  const rows = v.checks.map(check => {
    const pair = ['name','dob','address'].includes(check.key);
    return `<tr><td><span class="check-name">${text(check.label)}</span><span class="check-detail">${text(check.detail)}</span></td>${pair ? `<td>${text(c.applicant[check.key])}</td><td>${text(c.fields[check.key])}</td>` : `<td colspan="2">${text(check.key === 'number' ? c.fields.document_number : check.key === 'expiry' ? c.fields.expiry_date || 'Not shown' : c.fields.document_type)}</td>`}<td class="check-${check.status}">${check.status === 'pass' ? '✓ Pass' : check.status === 'fail' ? '× Check' : '— Missing'}</td></tr>`;
  }).join('');
  const fieldLabels = {name:'Name',dob:'Date of birth',document_number:'Document number',document_type:'Document type',address:'Address',expiry_date:'Expiry date'};
  const factors = r.factors.length ? r.factors.map(f => `<div class="factor"><span>${text(f.label)}</span><div class="factor-track"><div class="factor-fill" style="width:${Math.abs(f.contribution)/max*100}%"></div></div><span class="factor-value">${f.contribution >= 0 ? '+' : ''}${f.contribution.toFixed(2)}</span></div>`).join('') : '<p class="hint">No adverse signals were found in the supplied inputs. The score reflects the model’s baseline.</p>';
  $('result').innerHTML = `
    <div class="result-head"><div><div class="case-meta">CASE ${text(c.id)} · ${text(formatDate(c.created_at))}</div><h2>${text(c.applicant.name)}</h2><div class="case-meta">${text(c.status)}${c.parent_id ? ' · Reassessment of '+text(c.parent_id) : ''}</div></div><span class="source ${c.source !== 'live_ollama' ? 'replay' : ''}">${labelSource(c.source)}</span></div>
    <section class="panel risk-panel ${r.level.toLowerCase()}"><div class="risk-top"><div><div class="risk-caption">PROTOTYPE RISK SCORE</div><div class="score">${r.score}<small>/ 100</small></div></div><div><div class="risk-title">${r.level === 'LOW' ? 'Evidence is consistent.' : r.level === 'MEDIUM' ? 'A closer look is needed.' : 'Review the discrepancies.'}</div>${badge(r)}</div></div>
      <div class="meter"><span style="width:${thresholds.standard_max}%"></span><span style="width:${thresholds.enhanced_max-thresholds.standard_max}%"></span><span style="width:${100-thresholds.enhanced_max}%"></span></div><div class="thresholds"><span>Low 0–${thresholds.standard_max}</span><span>Medium ${thresholds.standard_max+1}–${thresholds.enhanced_max}</span><span>High ${thresholds.enhanced_max+1}–100</span></div>
      <div class="route"><div><div class="route-label">RECOMMENDED ROUTE</div><b>${text(r.route)} verification</b></div><span class="step">02</span></div>
      ${r.overrides.map(item => `<div class="override">Policy override: ${text(item)}</div>`).join('')}
      <ul class="action-list">${r.next_steps.map(item => `<li>${text(item)}</li>`).join('')}</ul>
    </section>
    <section class="panel evidence-panel"><div class="panel-heading"><h2>Verification checks</h2><span>${checked} / ${v.checks.length} passed</span></div><table><thead><tr><th>CHECK</th><th>APPLICANT</th><th>DOCUMENT</th><th>RESULT</th></tr></thead><tbody>${rows}</tbody></table>
      <details class="evidence"><summary>Extracted fields & original document</summary><div class="fields-grid">${Object.entries(fieldLabels).map(([key,label]) => `<div class="field-item"><span>${label}</span><b>${text(c.fields[key])}</b></div>`).join('')}</div><p class="hint">Field completeness: ${Math.round(v.completeness*100)}%. This is not calibrated OCR confidence. Number checks validate basic format only.</p><img class="evidence-image" alt="Document evidence for this case" src="data:image/jpeg;base64,${c.image}"></details>
    </section>
    <section class="panel evidence-panel"><div class="panel-heading"><h2>Why this score?</h2><span>Model contributions</span></div>${factors}<p class="hint">Bars show learned coefficient × adverse signal, in log-odds (not score points). Larger values push risk higher. The model was trained on 5,000 synthetic records.</p><details class="evidence"><summary>Model calculation & supplied signals</summary><p class="hint">Baseline ${r.baseline_score}% · Intercept ${r.intercept.toFixed(3)} · Final log-odds ${r.logit.toFixed(3)}<br>Score = 100 × sigmoid(intercept + contributions).</p><div class="signal-list">${Object.entries(c.signals).map(([key,value]) => `${text(key.replaceAll('_',' '))}: <b>${text(value)}</b>`).join('<br>')}</div><p class="hint">Device, behavior, anomaly and history values are demonstration inputs. They are not automatically detected.</p></details></section>
    <section class="panel review-panel"><div class="panel-heading"><h2>Reviewer decision</h2><span class="step">03</span></div><p>The recommendation supports your decision. Record a reason before taking action.</p><form id="reviewForm"><label>Reviewer name<input id="reviewer" maxlength="80" required placeholder="Your name"></label><label>Review note<textarea id="reviewNote" rows="2" maxlength="2000" required placeholder="What did you check, and why this decision?"></textarea></label><div class="review-actions"><button class="primary" data-action="Approved" type="submit">Approve</button><button class="secondary" data-action="Enhanced requested" type="submit">Request enhanced</button><button class="danger" data-action="Flagged for manual review" type="submit">Flag for review</button></div></form><div id="reviewSaved" role="status" hidden></div>
      <div>${c.reviews.map(item => `<div class="history-item"><b>${text(item.action)}</b><span>${text(item.reviewer)} · ${text(formatDate(item.at))}</span><p>${text(item.note)}</p></div>`).join('')}</div>
      <div class="route"><button class="json-link" id="exportBtn">Download case JSON</button><button class="secondary small" id="reassessBtn">Reassess with new evidence</button></div>
    </section>`;
  $('result').hidden = false;
  $('emptyState').hidden = true;
  $('processing').hidden = true;
  $('reviewer').value = sessionStorage.getItem('reviewer') || '';
  $('reviewForm').addEventListener('submit', async event => {
    event.preventDefault(); clearError();
    const action = event.submitter?.dataset.action;
    if (!action) return;
    const reviewer = $('reviewer').value.trim(), note = $('reviewNote').value.trim();
    const buttons = [...$('reviewForm').querySelectorAll('button')];
    buttons.forEach(b => b.disabled = true);
    try {
      const updated = await api('/api/review', {id:c.id, action, reviewer, note});
      sessionStorage.setItem('reviewer', reviewer);
      renderCase(updated);
      $('reviewSaved').textContent = 'Decision saved to local case history.';
      $('reviewSaved').className = 'saved'; $('reviewSaved').hidden = false;
      await refreshQueue();
    } catch(e) { showError(e); } finally { buttons.forEach(b => b.disabled = false); }
  });
  $('exportBtn').onclick = () => {
    const blob = new Blob([JSON.stringify(c,null,2)], {type:'application/json'});
    const url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = `Pramaan-${c.id}.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  $('reassessBtn').onclick = () => {
    parentId = c.id; sample = null;
    fillInputs(c.applicant, c.signals);
    imageData = ''; $('preview').hidden = true; $('document').value = ''; $('fileName').textContent = 'Choose the new document';
    $('parentNote').textContent = `New assessment linked to case ${c.id}. Upload new evidence; the original case remains in history.`;
    $('parentNote').hidden = false; $('rehearsalBox').hidden = true;
    document.querySelectorAll('[data-sample]').forEach(b=>b.classList.remove('selected'));
    window.scrollTo({top:0,behavior:'smooth'});
  };
}

form.addEventListener('submit', async event => {
  event.preventDefault(); if (busy) return; clearError();
  if (!imageData) return showError('Choose an ID document first.');
  const values = new FormData(form);
  const applicant = Object.fromEntries(['name','dob','address'].map(key => [key,values.get(key)]));
  const signals = Object.fromEntries(['device_known','document_anomaly','duplicate_identity'].map(key=>[key,values.has(key)]));
  for (const key of ['failed_attempts','previous_flags','behavior_score']) signals[key] = Number(values.get(key));
  const previous = current; current = null; busyState(true);
  const start = Date.now(); $('elapsed').textContent = '0 seconds';
  const timer = setInterval(() => $('elapsed').textContent = `${Math.round((Date.now()-start)/1000)} seconds`,1000);
  try {
    renderCase(await api('/api/verify',{image:imageData,applicant,signals,parent_id:parentId}));
    await refreshQueue();
  } catch (e) { showError(e); current = previous; if (previous) renderCase(previous); }
  finally { clearInterval(timer); busyState(false); }
});

$('rehearsalBtn').onclick = async () => {
  if (!sample || busy) return;
  clearError(); busyState(true);
  try { renderCase(await api('/api/rehearsal',{scenario:sample})); await refreshQueue(); }
  catch (e) { showError(e); }
  finally { busyState(false); }
};

async function refreshQueue() {
  const items = await api('/api/cases');
  $('queueCount').textContent = items.filter(c=>c.status==='Awaiting review').length;
  const filter = $('queueFilter').value;
  const shown = items.filter(c => filter === 'all' || (filter === 'pending' ? c.status === 'Awaiting review' : c.risk.route === filter));
  $('queueTable').innerHTML = shown.length ? `<table><thead><tr><th>APPLICANT / CASE</th><th>RISK</th><th>ROUTE</th><th>STATUS</th><th>CREATED</th><th></th></tr></thead><tbody>${shown.map(c => `<tr><td><b>${text(c.applicant.name)}</b><span class="queue-sub">${text(c.id)} · ${labelSource(c.source)}</span></td><td>${c.risk.score} / 100<br>${badge(c.risk)}</td><td>${text(c.risk.route)}</td><td>${text(c.status)}</td><td>${text(formatDate(c.created_at))}</td><td><button class="secondary" data-case="${c.id}">Open →</button></td></tr>`).join('')}</tbody></table>` : '<div class="queue-empty">No cases here yet. Assess an application to start the review history.</div>';
  document.querySelectorAll('[data-case]').forEach(button => button.onclick = async () => {
    try {
      clearError(); const c = await api(`/api/cases/${button.dataset.case}`);
      fillInputs(c.applicant, c.signals); setImage('data:image/jpeg;base64,'+c.image, 'Stored document / '+c.id);
      parentId=null; sample=null; $('parentNote').hidden=true; $('rehearsalBox').hidden=true; $('document').value='';
      document.querySelectorAll('[data-sample]').forEach(b=>b.classList.remove('selected'));
      renderCase(c); setView(false);
    }
    catch(e) { showError(e); }
  });
}

$('document').onchange = async event => {
  clearError(); imageData = ''; $('preview').hidden = true;
  const file = event.target.files[0];
  if (!file) { $('fileName').textContent = 'Choose an ID document'; return; }
  try { setImage(await readFile(file), file.name); sample = null; $('rehearsalBox').hidden = true; document.querySelectorAll('[data-sample]').forEach(b=>b.classList.remove('selected')); }
  catch(e) { $('fileName').textContent = 'Choose an ID document'; showError(e); }
};
document.querySelectorAll('[data-sample]').forEach(button => button.onclick = () => loadSample(button.dataset.sample));
$('healthBtn').onclick = connection;
$('newTab').onclick = () => {
  if (busy) return;
  setView(false); clearError(); form.reset(); imageData=''; sample=null; current=null; parentId=null;
  $('preview').hidden=true; $('rehearsalBox').hidden=true; $('parentNote').hidden=true; $('result').hidden=true; $('emptyState').hidden=false;
  $('fileName').textContent='Choose an ID document'; document.querySelectorAll('[data-sample]').forEach(b=>b.classList.remove('selected'));
};
$('queueTab').onclick = async () => { setView(true); clearError(); try { await refreshQueue(); } catch(e) {showError(e);} };
$('refreshQueue').onclick = () => refreshQueue().catch(showError);
$('queueFilter').onchange = () => refreshQueue().catch(showError);
form.elements.dob.max = new Date().toLocaleDateString('en-CA');
connection(); refreshQueue().catch(showError);
