// ── STATE ──
let sessions    = JSON.parse(sessionStorage.getItem('medai_sessions') || '[]');
let activeId    = null;
let pendingFile = null; // { type, name, dataUrl? }

// ── INIT ──
renderHistory();

// ── SIDEBAR (MOBILE) ──
function openSidebar() {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('overlay').classList.add('show');
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('overlay').classList.remove('show');
}

// ── SYMPTOM CHIPS ──
function addSymptom(s) {
  const inp = document.getElementById('symptoms');
  if (inp.value.includes(s)) return;
  inp.value = inp.value.trim() ? inp.value.trim() + ', ' + s : s;
  inp.focus();
}

// ── FILE HANDLER ──
function handleFile(e, type) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    pendingFile = {
      type,
      name: file.name,
      dataUrl: type === 'image' ? ev.target.result : null
    };
    // Highlight the icon button
    const btn = type === 'image'
      ? document.getElementById('imageFile').closest('.icon-btn')
      : document.getElementById('docFile').closest('.icon-btn');
    btn.style.borderColor = 'var(--blue)';
    btn.style.background  = 'var(--blue-light)';
    btn.querySelector('svg').style.stroke = 'var(--blue)';
  };
  if (type === 'image') reader.readAsDataURL(file);
  else reader.readAsText(file);
}

// ── NEW CHAT ──
function newChat() {
  activeId = null;
  document.getElementById('symptoms').value = '';
  document.getElementById('sessionTitle').textContent = 'Symptom Analysis';
  clearStream();
  pendingFile = null;
  resetFileButtons();
  closeSidebar();
}

function clearStream() {
  document.getElementById('resultStream').innerHTML = `
    <div class="stream-empty" id="streamEmpty">
      <div class="stream-empty-icon">
        <svg viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
      </div>
      <strong>No analysis yet</strong>
      <p>Enter your symptoms above, upload an image<br>or medical file, then click Analyze.</p>
    </div>`;
}

function resetFileButtons() {
  ['imageFile', 'docFile'].forEach(id => {
    const btn = document.getElementById(id).closest('.icon-btn');
    btn.style.borderColor = '';
    btn.style.background  = '';
    btn.querySelector('svg').style.stroke = '';
    document.getElementById(id).value = '';
  });
}

// ── LOAD SESSION ──
function loadSession(id) {
  const sess = sessions.find(s => s.id === id);
  if (!sess) return;
  activeId = id;
  document.getElementById('sessionTitle').textContent = sess.title;
  const stream = document.getElementById('resultStream');
  stream.innerHTML = '';
  sess.messages.forEach(m => stream.insertAdjacentHTML('beforeend', renderMsg(m)));
  stream.scrollTop = stream.scrollHeight;
  renderHistory();
  closeSidebar();
}

// ── DELETE SESSION ──
function deleteSession(e, id) {
  e.stopPropagation();
  sessions = sessions.filter(s => s.id !== id);
  saveToStorage();
  if (activeId === id) newChat();
  renderHistory();
}

// ── RENDER HISTORY ──
function renderHistory() {
  const list = document.getElementById('historyList');
  if (sessions.length === 0) {
    list.innerHTML = `
      <div class="history-empty" id="historyEmpty">
        <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        No sessions yet.<br>Start your first analysis.
      </div>`;
    return;
  }
  list.innerHTML = sessions.slice().reverse().map(s => `
    <div class="history-item ${s.id === activeId ? 'active' : ''}" onclick="loadSession('${s.id}')">
      <div class="history-item-title">${esc(s.title)}</div>
      <div class="history-item-meta">
        <span class="history-item-dot"></span>
        ${s.time}
      </div>
      <button class="history-item-delete" onclick="deleteSession(event,'${s.id}')" title="Delete">
        <svg viewBox="0 0 24 24">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6l-1 14H6L5 6"/>
          <path d="M10 11v6"/><path d="M14 11v6"/>
          <path d="M9 6V4h6v2"/>
        </svg>
      </button>
    </div>`).join('');
}

// ── RENDER MESSAGE ──
function renderMsg(m) {
  if (m.role === 'user') {
    let attachHtml = '';
    if (m.image) attachHtml += `<div class="attach-preview"><img src="${m.image}" alt="uploaded"></div>`;
    if (m.file)  attachHtml += `
      <div class="file-attach">
        <svg viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        ${esc(m.file)}
      </div>`;
    return `
      <div class="msg msg-user">
        <div>
          <div class="bubble-user">${esc(m.text)}${attachHtml}</div>
          <div class="msg-time">${m.time}</div>
        </div>
      </div>`;
  }

  if (m.role === 'ai') {
    return `
      <div class="msg msg-ai">
        <div class="bubble-ai">
          <div class="result-card">
            <div class="result-card-top">
              <div class="result-tag">
                <span class="result-tag-dot"></span>Condition identified
              </div>
              <div class="result-disease">${esc(m.disease)}</div>
            </div>
            <div class="result-card-bot">

              <div class="result-meta-lbl">Confidence</div>
              <div class="result-meta-val">
                ${m.confidence}%
              </div>

              <div class="result-meta-lbl">Symptoms analyzed</div>
              <div class="result-meta-val">
                ${esc(m.symptoms)}
              </div>

              <div class="result-meta-lbl">Description</div>
              <div class="result-meta-val">
                ${esc(m.description)}
              </div>

              <div class="result-meta-lbl">Severity</div>
            <div class="result-meta-val">
               ${esc(m.severity)}
            </div>

            <div class="result-meta-lbl">Recommended Doctor</div>
            <div class="result-meta-val">
              ${esc(m.doctor_type)}
          </div>

              <div class="result-meta-lbl">
                Precautions
              </div>

              <ul class="precaution-list">
                ${m.precautions
                  .map(p => `<li>${esc(p)}</li>`)
                  .join("")}
              </ul>

              <div class="result-disclaimer">
                AI result for informational use only.
                Consult a licensed physician.
              </div>
                  <button class="pdf-btn" onclick="downloadReport()">
                      📄 Download Report
                  </button>
            </div>
          </div>

          <div class="msg-time">${m.time}</div>
        </div>
      </div>`;
}

  if (m.role === 'error') {
    return `
      <div class="msg msg-ai">
        <div class="bubble-ai">
          <div class="error-bubble">
            <div class="error-title">${esc(m.title)}</div>
            <div class="error-msg">${esc(m.text)}</div>
          </div>
          <div class="msg-time">${m.time}</div>
        </div>
      </div>`;
  }
  return '';
}

// ── SESSION STORAGE ──
function saveToStorage() {
  sessionStorage.setItem('medai_sessions', JSON.stringify(sessions));
}

// ── TIME ──
function now() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ── MAIN ANALYZE ──
async function runAnalysis() {
  const inp    = document.getElementById('symptoms');
  const stream = document.getElementById('resultStream');
  const btn    = document.getElementById('runBtn');
  const raw    = inp.value.trim();

  if (!raw && !pendingFile) {
    appendError(stream, 'Nothing to analyze', 'Enter symptoms or upload an image/file first.');
    return;
  }

  // Remove empty state
  document.getElementById('streamEmpty')?.remove();

  // User message
  const userMsg = {
    role:  'user',
    text:  raw || '(file/image only)',
    image: pendingFile?.type === 'image' ? pendingFile.dataUrl : null,
    file:  pendingFile?.type === 'doc'   ? pendingFile.name   : null,
    time:  now()
  };
  stream.insertAdjacentHTML('beforeend', renderMsg(userMsg));
  stream.scrollTop = stream.scrollHeight;

  // Loading bubble
  const loadId = 'load-' + Date.now();
  stream.insertAdjacentHTML('beforeend', `
    <div class="msg msg-ai" id="${loadId}">
      <div class="bubble-ai">
        <div class="loading-bubble">
          <div class="ios-spinner"></div>
          <p>Analyzing symptoms…</p>
        </div>
      </div>
    </div>`);
  stream.scrollTop = stream.scrollHeight;
  btn.disabled = true;

  // Session setup
  if (!activeId) {
    activeId = 'sess-' + Date.now();
    const title = raw
      ? raw.split(',')[0].trim().replace(/^\w/, c => c.toUpperCase())
      : (pendingFile?.name || 'New session');
    sessions.push({ id: activeId, title, time: now(), messages: [] });
    document.getElementById('sessionTitle').textContent = title;
  }
  const sess = sessions.find(s => s.id === activeId);
  sess.messages.push(userMsg);

  try {
    // const symptoms = raw
    //   ? raw.split(/[,;]/).map(s => s.trim().toLowerCase()).filter(Boolean)
    //   : ['image_analysis'];

    // const res = await fetch('http://127.0.0.1:8000/predict', {
    //   method:  'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body:    JSON.stringify({ symptoms })
    // });
    const res = await fetch('http://127.0.0.1:8000/predict-text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
    text: raw
    })
  });

    if (!res.ok) throw new Error('server');
    const data = await res.json();
    if (!data.predicted_disease) throw new Error('empty');

    document.getElementById(loadId)?.remove();

  //   const aiMsg = {
  //     role: 'ai',
  //     disease: data.predicted_disease,
  //     confidence: data.confidence,
  //     description: data.description,
  //     precautions: data.precautions,
  //     symptoms: symptoms.join(', '),
  //     time: now()
  // };
   const aiMsg = {
   role: 'ai',
   disease: data.predicted_disease,
    confidence: data.confidence,
    description: data.description,
    severity: data.severity,
    doctor_type: data.doctor_type,
    precautions: data.precautions,
    symptoms: data.detected_symptoms.join(', '),
    time: now()
  };    
stream.insertAdjacentHTML('beforeend', renderMsg(aiMsg));
    stream.scrollTop = stream.scrollHeight;
    sess.messages.push(aiMsg);

    const history = JSON.parse(
  localStorage.getItem("predictionHistory") || "[]"
);

history.unshift({
  disease: data.predicted_disease,
  confidence: data.confidence,
  symptoms: data.detected_symptoms.join(", "),
  time: now()
});

localStorage.setItem(
  "predictionHistory",
  JSON.stringify(history)
);

  } catch (err) {
    document.getElementById(loadId)?.remove();
    const errMsg = err instanceof TypeError
      ? 'Cannot reach backend. Ensure FastAPI is running on localhost:8000.'
      : 'Analysis failed. Please try again.';
    const errObj = { role: 'error', title: 'Analysis failed', text: errMsg, time: now() };
    stream.insertAdjacentHTML('beforeend', renderMsg(errObj));
    stream.scrollTop = stream.scrollHeight;
    sess.messages.push(errObj);

  } finally {
    btn.disabled = false;
    saveToStorage();
    renderHistory();
    inp.value   = '';
    pendingFile = null;
    resetFileButtons();
  }
}

function appendError(stream, title, text) {
  document.getElementById('streamEmpty')?.remove();
  stream.insertAdjacentHTML('beforeend', renderMsg({ role: 'error', title, text, time: now() }));
  stream.scrollTop = stream.scrollHeight;
}

// ── ESCAPE HTML ──
function esc(t = '') {
  return String(t).replace(/[&<>"']/g, m => (
    { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'": '&#039;' }[m]
  ));
}

// ── ENTER KEY ──
document.getElementById('symptoms').addEventListener('keypress', e => {
  if (e.key === 'Enter') runAnalysis();
});
function downloadReport() {

  const { jsPDF } = window.jspdf;

  const doc = new jsPDF();

  const disease =
    document.querySelector(".result-disease")?.innerText || "";

  doc.setFontSize(18);
  doc.text("Smart Healthcare AI Report", 20, 20);

  doc.setFontSize(12);
  doc.text("Disease: " + disease, 20, 40);

  doc.save("health-report.pdf");
}
function startVoice() {

  const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    alert("Speech Recognition not supported");
    return;
  }

  const recognition =
    new SpeechRecognition();

  recognition.lang = "en-US";

  recognition.start();

  recognition.onresult = function(event) {

    const text =
      event.results[0][0].transcript;

    document.getElementById("symptoms").value =
      text;
  };

  recognition.onerror = function(event) {
  console.log("Voice Error:", event.error);
  alert("Voice Error: " + event.error);
};
  
}