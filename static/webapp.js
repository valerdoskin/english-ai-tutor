// English AI Tutor Web App
let tg = null;
let userId = null;
let userLevel = null;
let testState = null;
let lessonState = null;
let dialogueState = null;
let mediaRecorder = null;
let audioChunks = [];

// Инициализация Telegram Web App
function initTelegram() {
    if (window.Telegram && window.Telegram.WebApp) {
        tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        tg.setHeaderColor('#0f172a');
        tg.setBackgroundColor('#0f172a');
        userId = tg.initDataUnsafe?.user?.id || null;
        if (userId) {
            loadProfile();
        }
    }
}

// Показать уведомление
function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// Переключение видов
function showView(view) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    document.getElementById('view-' + view).classList.remove('hidden');
    document.querySelectorAll('.nav-item').forEach(n => {
        n.classList.toggle('active', n.dataset.view === view);
    });
    // Загружаем контент при открытии
    if (view === 'test') loadTest();
    if (view === 'lessons') loadLessons();
    if (view === 'podcasts') loadPodcasts();
    if (view === 'dialogue') loadDialogue();
}

// Загрузка профиля
async function loadProfile() {
    try {
        const res = await fetch(`/api/profile?user_id=${userId}`);
        const data = await res.json();
        if (data.level) {
            userLevel = data.level;
            document.getElementById('userLevel').textContent = `Level: ${data.level}`;
        }
    } catch (e) {
        console.error('Profile error:', e);
    }
}

// ============ ТЕСТ УРОВНЯ ============
async function loadTest() {
    const content = document.getElementById('test-content');
    if (testState && testState.questions) {
        renderTestQuestion();
        return;
    }
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Generating your test...</p>
        </div>`;
    try {
        const res = await fetch(`/api/test/start?user_id=${userId}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        testState = data;
        renderTestQuestion();
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load test. Please try again.</p></div>`;
    }
}

function renderTestQuestion() {
    const content = document.getElementById('test-content');
    const q = testState.questions[testState.current];
    if (!q) {
        // Тест завершён
        submitTest();
        return;
    }
    const progress = ((testState.current) / testState.questions.length) * 100;
    content.innerHTML = `
        <div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div>
        <div class="card">
            <p style="color:var(--text-muted);font-size:13px;margin-bottom:8px">Question ${testState.current + 1} of ${testState.questions.length}</p>
            <h3>${q.question}</h3>
            <div style="margin-top:16px">
                ${q.options.map((opt, i) => `
                    <button class="option" onclick="selectAnswer(${i})">${opt}</button>
                `).join('')}
            </div>
        </div>`;
}

async function selectAnswer(index) {
    const q = testState.questions[testState.current];
    q.selected = index;
    testState.current++;
    if (testState.current < testState.questions.length) {
        renderTestQuestion();
    } else {
        submitTest();
    }
}

async function submitTest() {
    const content = document.getElementById('test-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Evaluating your answers...</p>
        </div>`;
    try {
        const res = await fetch('/api/test/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, answers: testState.questions })
        });
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        userLevel = data.level;
        document.getElementById('userLevel').textContent = `Level: ${data.level}`;
        content.innerHTML = `
            <div class="card" style="text-align:center">
                <h3 style="font-size:24px;margin-bottom:8px">🎉 Your Level</h3>
                <div class="level-badge" style="font-size:20px;padding:8px 20px">${data.level}</div>
                <p style="margin-top:16px">${data.description}</p>
                <p style="margin-top:8px;color:var(--text-muted)">Score: ${data.score}%</p>
            </div>
            <button class="btn btn-primary" onclick="showView('lessons')">📚 Start Lessons</button>
            <button class="btn btn-secondary" onclick="showView('home')">🏠 Home</button>`;
        testState = null;
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to submit test.</p></div>`;
    }
}

// ============ УРОКИ ============
async function loadLessons() {
    const content = document.getElementById('lessons-content');
    content.innerHTML = `
        <div class="card">
            <h3>📚 AI Lessons</h3>
            <p>Choose a topic and I'll generate a lesson for your level.</p>
            <input class="input" id="lesson-topic" placeholder="Enter a topic (e.g. Travel, Food, Business)">
            <button class="btn btn-primary" onclick="generateLesson()">Generate Lesson</button>
        </div>
        <div id="lesson-result"></div>`;
}

async function generateLesson() {
    const topic = document.getElementById('lesson-topic').value.trim();
    if (!topic) { showToast('Please enter a topic'); return; }
    const result = document.getElementById('lesson-result');
    result.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Generating your lesson...</p>
        </div>`;
    try {
        const res = await fetch('/api/lesson/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, topic })
        });
        const data = await res.json();
        if (data.error) {
            result.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        result.innerHTML = `
            <div class="card">
                <h3>${data.title}</h3>
                <p style="margin-bottom:12px">${data.introduction}</p>
                <div style="margin-bottom:12px">
                    ${data.vocabulary.map(v => `<span class="tag vocab">${v}</span>`).join('')}
                </div>
                <div class="result-box">${data.explanation}</div>
                <h3 style="margin:12px 0 8px">✍️ Exercise</h3>
                <div class="result-box">${data.exercise}</div>
                <button class="btn btn-secondary" onclick="showView('dialogue')">🎤 Practice Speaking</button>
            </div>`;
    } catch (e) {
        result.innerHTML = `<div class="card"><p class="error-text">Failed to generate lesson.</p></div>`;
    }
}

// ============ ПОДКАСТЫ ============
async function loadPodcasts() {
    const content = document.getElementById('podcasts-content');
    content.innerHTML = `
        <div class="card">
            <h3>🎧 AI Podcasts</h3>
            <p>Generate an audio podcast on any topic you're interested in.</p>
            <input class="input" id="podcast-topic" placeholder="Enter a topic (e.g. Space, History, Sports)">
            <button class="btn btn-primary" onclick="generatePodcast()">Generate Podcast</button>
        </div>
        <div id="podcast-result"></div>`;
}

async function generatePodcast() {
    const topic = document.getElementById('podcast-topic').value.trim();
    if (!topic) { showToast('Please enter a topic'); return; }
    const result = document.getElementById('podcast-result');
    result.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Generating your podcast...</p>
        </div>`;
    try {
        const res = await fetch('/api/podcast/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, topic })
        });
        const data = await res.json();
        if (data.error) {
            result.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        result.innerHTML = `
            <div class="card">
                <h3>🎧 ${data.title}</h3>
                <p style="margin-bottom:12px">${data.summary}</p>
                <audio class="audio-player" controls src="${data.audio_url}"></audio>
                <div class="result-box">${data.transcript}</div>
            </div>`;
    } catch (e) {
        result.innerHTML = `<div class="card"><p class="error-text">Failed to generate podcast.</p></div>`;
    }
}

// ============ АУДИО ДИАЛОГ ============
async function loadDialogue() {
    const content = document.getElementById('dialogue-content');
    dialogueState = { messages: [] };
    content.innerHTML = `
        <div class="card">
            <h3>🎤 Voice Dialogue</h3>
            <p>Press the mic and speak. I'll transcribe, correct, and reply!</p>
        </div>
        <div class="chat-area" id="chat-area"></div>
        <button class="mic-btn" id="mic-btn" onclick="toggleRecording()">🎤</button>
        <p style="text-align:center;color:var(--text-muted);font-size:12px" id="mic-status">Tap to start speaking</p>`;
}

function addChatMessage(text, type) {
    const area = document.getElementById('chat-area');
    if (!area) return;
    const div = document.createElement('div');
    div.className = 'chat-bubble ' + (type === 'user' ? 'chat-user' : 'chat-bot');
    div.textContent = text;
    area.appendChild(div);
    area.scrollTop = area.scrollHeight;
}

async function toggleRecording() {
    const btn = document.getElementById('mic-btn');
    const status = document.getElementById('mic-status');
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        // Начать запись
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
            mediaRecorder.onstop = () => sendAudio();
            mediaRecorder.start();
            btn.classList.add('recording');
            btn.textContent = '⏹';
            status.textContent = 'Recording... tap to stop';
        } catch (e) {
            showToast('Microphone access denied');
        }
    } else {
        // Остановить запись
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(t => t.stop());
        btn.classList.remove('recording');
        btn.textContent = '🎤';
        status.textContent = 'Processing...';
    }
}

async function sendAudio() {
    const blob = new Blob(audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio', blob, 'speech.webm');
    formData.append('user_id', userId);
    addChatMessage('🎤 (voice message)', 'user');
    try {
        const res = await fetch('/api/dialogue/voice', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.error) {
            addChatMessage('❌ ' + data.error, 'bot');
            document.getElementById('mic-status').textContent = 'Tap to start speaking';
            return;
        }
        if (data.transcript) {
            addChatMessage('🗣 You said: "' + data.transcript + '"', 'user');
        }
        if (data.corrections && data.corrections.length > 0) {
            addChatMessage('📝 Corrections: ' + data.corrections.join('; '), 'bot');
        }
        addChatMessage('🤖 ' + data.reply, 'bot');
        if (data.audio_url) {
            const audio = new Audio(data.audio_url);
            audio.play();
        }
        document.getElementById('mic-status').textContent = 'Tap to start speaking';
    } catch (e) {
        addChatMessage('❌ Failed to process audio', 'bot');
        document.getElementById('mic-status').textContent = 'Tap to start speaking';
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', initTelegram);
