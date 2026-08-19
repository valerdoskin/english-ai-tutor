// English AI Tutor Web App
let tg = null;
let userId = null;
let userLevel = null;
let userStats = null;
let testState = null;
let grammarState = null;
let listeningState = null;
let speakingState = null;
let dailyState = null;
let mediaRecorder = null;
let audioChunks = [];

// Инициализация Telegram Web App
function initTelegram() {
    if (window.Telegram && window.Telegram.WebApp) {
        tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        tg.setHeaderColor('#0b1120');
        tg.setBackgroundColor('#0b1120');
        userId = tg.initDataUnsafe?.user?.id || null;
        if (userId) {
            loadProfile();
            loadStats();
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

// Показать XP popup
function showXpPopup(xp) {
    const popup = document.createElement('div');
    popup.className = 'xp-popup';
    popup.textContent = `+${xp} XP`;
    document.body.appendChild(popup);
    setTimeout(() => popup.remove(), 1500);
}

// Показать конфетти
function showConfetti() {
    const colors = ['#38bdf8', '#818cf8', '#34d399', '#fbbf24', '#f87171'];
    for (let i = 0; i < 20; i++) {
        const piece = document.createElement('div');
        piece.className = 'confetti-piece';
        piece.style.left = Math.random() * 100 + 'vw';
        piece.style.top = '50%';
        piece.style.background = colors[Math.floor(Math.random() * colors.length)];
        piece.style.animationDelay = Math.random() * 0.5 + 's';
        document.body.appendChild(piece);
        setTimeout(() => piece.remove(), 2500);
    }
}

// Переключение видов
function showView(view) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    document.getElementById('view-' + view).classList.remove('hidden');
    document.querySelectorAll('.nav-item').forEach(n => {
        n.classList.toggle('active', n.dataset.view === view);
    });
    if (view === 'test') loadTest();
    if (view === 'lessons') loadLessons();
    if (view === 'grammar') loadGrammar();
    if (view === 'listening') loadListening();
    if (view === 'speaking') loadSpeaking();
    if (view === 'daily') loadDaily();
    if (view === 'achievements') loadAchievements();
    window.scrollTo(0, 0);
}

// Загрузка профиля
async function loadProfile() {
    try {
        const res = await fetch(`/api/profile?user_id=${userId}`);
        const data = await res.json();
        if (data.level) {
            userLevel = data.level;
            document.getElementById('userLevel').textContent = `Level: ${data.level}`;
            document.getElementById('levelChip').textContent = `Level: ${data.level}`;
        }
    } catch (e) {
        console.error('Profile error:', e);
    }
}

// Загрузка статистики
async function loadStats() {
    try {
        const res = await fetch(`/api/stats?user_id=${userId}`);
        const data = await res.json();
        if (data.ok && data.stats) {
            userStats = data.stats;
            document.getElementById('statXp').textContent = data.stats.xp || 0;
            document.getElementById('statStreak').textContent = data.stats.streak || 0;
            document.getElementById('statRank').textContent = (data.stats.rank_icon ? data.stats.rank_icon + ' ' : '') + (data.stats.rank || 'Bronze');
            document.getElementById('statLessons').textContent = data.stats.completed_lessons || 0;
            if (data.stats.level) {
                userLevel = data.stats.level;
                document.getElementById('userLevel').textContent = `Level: ${data.stats.level}`;
                document.getElementById('levelChip').textContent = `Level: ${data.stats.level}`;
            }
            // Прогресс до следующего ранга
            const rp = document.getElementById('rankProgress');
            if (data.stats.xp_to_next_rank !== undefined && data.stats.xp_to_next_rank > 0) {
                const xp = data.stats.xp || 0;
                const toNext = data.stats.xp_to_next_rank;
                const total = xp + toNext;
                const pct = total > 0 ? Math.min(100, Math.round((xp / total) * 100)) : 0;
                document.getElementById('rankProgressFill').style.width = pct + '%';
                document.getElementById('rankProgressText').textContent = `${xp}/${total} XP to next rank`;
                rp.style.display = 'block';
            } else {
                rp.style.display = 'none';
            }
        }
    } catch (e) {
        console.error('Stats error:', e);
    }
}

// ============ ТЕСТ УРОВНЯ ============
async function loadTest() {
    const content = document.getElementById('test-content');
    if (testState && testState.question) {
        renderTestQuestion();
        return;
    }
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Generating your test...</p>
        </div>`;
    try {
        const res = await fetch(`/api/adaptive-test/start?user_id=${userId}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        testState = { question: data.question, current: data.current, total: data.total, answers: [] };
        renderTestQuestion();
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load test. Please try again.</p></div>`;
    }
}

function renderTestQuestion() {
    const content = document.getElementById('test-content');
    const q = testState.question;
    if (!q) {
        submitTest();
        return;
    }
    const progress = ((testState.current - 1) / testState.total) * 100;
    content.innerHTML = `
        <div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div>
        <div class="card">
            <p style="color:var(--text-muted);font-size:13px;margin-bottom:8px">Question ${testState.current} of ${testState.total}</p>
            <h3>${q.question}</h3>
            <div style="margin-top:16px">
                ${q.options.map((opt, i) => `
                    <button class="option" onclick="selectAnswer(${i})">${opt}</button>
                `).join('')}
            </div>
        </div>`;
}

async function selectAnswer(index) {
    const q = testState.question;
    testState.answers.push({ question: q.question, selected: index });
    const content = document.getElementById('test-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading next question...</p>
        </div>`;
    try {
        const res = await fetch('/api/adaptive-test/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, selected: index })
        });
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        if (data.finished || data.done) {
            testState.question = null;
            submitTest();
        } else {
            testState.question = data.question;
            testState.current = data.current;
            renderTestQuestion();
        }
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to submit answer.</p></div>`;
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
        const res = await fetch('/api/adaptive-test/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        const result = data.result || data;
        userLevel = result.level;
        document.getElementById('userLevel').textContent = `Level: ${result.level}`;
        document.getElementById('levelChip').textContent = `Level: ${result.level}`;
        showConfetti();
        showXpPopup(result.xp || 50);
        content.innerHTML = `
            <div class="card" style="text-align:center;animation:scaleIn 0.4s ease">
                <h3 style="font-size:24px;margin-bottom:8px">🎉 Your Level</h3>
                <div class="level-badge" style="font-size:20px;padding:8px 20px">${result.level}</div>
                <p style="margin-top:16px">${result.description}</p>
                <p style="margin-top:8px;color:var(--text-muted)">Score: ${result.score}%</p>
            </div>
            ${result.skill_report ? `
            <div class="card">
                <h3>📊 Skill Report</h3>
                ${Object.entries(result.skill_report).map(([skill, info]) => {
                    const pct = typeof info === 'object' ? (info.percent || 0) : info;
                    return `
                    <div class="skill-bar">
                        <div class="skill-name">${skill}</div>
                        <div class="skill-track"><div class="skill-fill" style="width:${pct}%"></div></div>
                        <div class="skill-value">${pct}%</div>
                    </div>`;
                }).join('')}
            </div>` : ''}
            ${result.recommendations ? `
            <div class="card">
                <h3>💡 Recommendations</h3>
                ${Array.isArray(result.recommendations) ? result.recommendations.map(r => `<p style="margin-bottom:6px">• ${r}</p>`).join('') : `<p>${result.recommendations}</p>`}
            </div>` : ''}
            <button class="btn btn-primary" onclick="showView('lessons')">📚 Start Lessons</button>
            <button class="btn btn-secondary" onclick="showView('home')">🏠 Home</button>`;
        testState = null;
        loadStats();
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to submit test.</p></div>`;
    }
}

// ============ УРОКИ (Learning Path) ============
async function loadLessons() {
    const content = document.getElementById('lessons-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading your curriculum...</p>
        </div>`;
    try {
        const res = await fetch(`/api/modules?user_id=${userId}&level=${userLevel || 'A2'}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        const modules = data.modules || [];
        let totalLessons = 0;
        let completedLessons = 0;
        modules.forEach(m => {
            totalLessons += m.lessons_count || 0;
            completedLessons += m.completed_count || 0;
        });
        const totalProgress = totalLessons > 0 ? Math.round((completedLessons / totalLessons) * 100) : 0;
        document.getElementById('pathProgress').style.width = totalProgress + '%';
        document.getElementById('pathProgressText').textContent = `${totalProgress}% complete`;

        content.innerHTML = `
            <div class="card" style="background:linear-gradient(135deg,rgba(56,189,248,0.1),rgba(129,140,248,0.1));border-color:var(--accent)">
                <h3>📚 Your Learning Path</h3>
                <p>Level: <span class="level-badge">${userLevel || 'A2'}</span></p>
                <div class="progress-bar" style="margin-top:12px"><div class="progress-fill" style="width:${totalProgress}%"></div></div>
                <p style="font-size:12px;color:var(--accent);font-weight:600">${completedLessons}/${totalLessons} lessons completed</p>
            </div>
            <div style="margin-top:16px">
                ${modules.map(m => `
                    <div class="module-card" onclick="openModule(${m.id})">
                        <div class="module-title">${m.icon || '📘'} ${m.title}</div>
                        <div class="module-desc">${m.description || ''}</div>
                        <div class="progress-bar" style="margin-top:8px"><div class="progress-fill" style="width:${m.progress || 0}%"></div></div>
                        <div class="module-progress">${m.completed_count || 0}/${m.lessons_count || 0} lessons · ${m.progress || 0}%</div>
                        ${m.task ? `<div class="tag grammar" style="margin-top:8px">🎯 ${m.task}</div>` : ''}
                    </div>
                `).join('')}
            </div>`;
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load curriculum.</p></div>`;
    }
}

async function openModule(moduleId) {
    const content = document.getElementById('lessons-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading module...</p>
        </div>`;
    try {
        const res = await fetch(`/api/modules/${moduleId}?user_id=${userId}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        const module = data.module;
        content.innerHTML = `
            <button class="btn btn-secondary" onclick="loadLessons()">← Back to Modules</button>
            <div class="card">
                <h3>${module.icon || '📘'} ${module.title}</h3>
                <p>${module.description || ''}</p>
                ${module.task ? `<div class="tag grammar" style="margin-top:8px">🎯 ${module.task}</div>` : ''}
            </div>
            <div class="section-title">Lessons</div>
            ${(module.lessons || []).map(l => `
                <div class="module-card" onclick="openLesson(${l.id})">
                    <div class="module-title">${l.completed ? '✅' : '📖'} ${l.title}</div>
                    <div class="module-desc">${l.type || l.lesson_type || 'lesson'}</div>
                    ${l.completed ? `<div class="module-progress">Completed ${l.score ? '· Score: ' + l.score + '%' : ''}</div>` : ''}
                </div>
            `).join('')}
            <button class="btn btn-primary" onclick="loadNextLesson()">⚡ Continue Learning</button>`;
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load module.</p></div>`;
    }
}

async function openLesson(lessonId) {
    const content = document.getElementById('lessons-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading lesson...</p>
        </div>`;
    try {
        const res = await fetch(`/api/lessons/${lessonId}?user_id=${userId}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        const lesson = data.lesson;
        const c = lesson.content || {};
        const contentHtml = typeof c === 'string' ? c : `
            ${c.introduction ? `<p style="margin-bottom:12px">${c.introduction}</p>` : ''}
            ${c.explanation ? `<div class="result-box" style="margin-bottom:12px">${c.explanation}</div>` : ''}
            ${c.examples && c.examples.length ? `
                <div style="margin-bottom:12px">
                    ${c.examples.map(e => `<div class="result-box" style="margin-bottom:8px">${e}</div>`).join('')}
                </div>` : ''}
            ${c.exercise ? `<div class="tag grammar" style="margin-bottom:8px">✏️ ${c.exercise}</div>` : ''}
            ${c.task ? `<div class="tag vocab" style="margin-bottom:8px">🎯 ${c.task}</div>` : ''}`;
        content.innerHTML = `
            <button class="btn btn-secondary" onclick="loadLessons()">← Back</button>
            <div class="card">
                <h3>📖 ${lesson.title}</h3>
                <div class="result-box">${contentHtml}</div>
            </div>
            <button class="btn btn-success" onclick="completeLesson(${lessonId})">✅ Mark as Complete</button>`;
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load lesson.</p></div>`;
    }
}

async function completeLesson(lessonId) {
    const content = document.getElementById('lessons-content');
    try {
        const res = await fetch(`/api/lessons/${lessonId}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, score: 90 })
        });
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        showConfetti();
        showXpPopup(data.xp || 20);
        content.innerHTML = `
            <div class="card" style="text-align:center;animation:scaleIn 0.4s ease">
                <h3 style="font-size:24px;margin-bottom:8px">🎉 Lesson Complete!</h3>
                <p style="font-size:18px;font-weight:700;color:var(--accent)">+${data.xp || 20} XP</p>
                <p style="margin-top:8px">Rank: ${data.rank || 'Bronze'}</p>
            </div>
            <button class="btn btn-primary" onclick="loadNextLesson()">⚡ Next Lesson</button>
            <button class="btn btn-secondary" onclick="loadLessons()">📚 All Modules</button>`;
        loadStats();
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to complete lesson.</p></div>`;
    }
}

async function loadNextLesson() {
    const content = document.getElementById('lessons-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Finding your next lesson...</p>
        </div>`;
    try {
        const res = await fetch(`/api/next-lesson?user_id=${userId}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        const lesson = data.next_lesson;
        if (!lesson) {
            content.innerHTML = `
                <div class="card" style="text-align:center">
                    <h3>🎉 All lessons complete!</h3>
                    <p>You've finished all available lessons. Great job!</p>
                </div>`;
            return;
        }
        content.innerHTML = `
            <button class="btn btn-secondary" onclick="loadLessons()">← Back</button>
            <div class="card">
                <h3>📖 ${lesson.title}</h3>
                <p style="color:var(--text-muted);font-size:13px">Module: ${lesson.module_title}</p>
                <div class="tag grammar" style="margin-top:8px">${lesson.type || 'lesson'}</div>
            </div>
            <button class="btn btn-success" onclick="completeLesson(${lesson.lesson_id})">✅ Mark as Complete</button>`;
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load next lesson.</p></div>`;
    }
}

// ============ ГРАММАТИКА ============
async function loadGrammar() {
    const content = document.getElementById('grammar-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading grammar topics...</p>
        </div>`;
    try {
        const res = await fetch(`/api/grammar/topics?user_id=${userId}&level=${userLevel || 'A2'}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        content.innerHTML = `
            <div class="tab-bar">
                <div class="tab active" onclick="loadGrammar()">Topics</div>
                <div class="tab" onclick="loadGrammarLesson()">Practice</div>
            </div>
            ${data.topics.map(t => `
                <div class="module-card" onclick="loadGrammarLesson('${t.topic}')">
                    <div class="module-title">📖 ${t.topic}</div>
                    <div class="module-desc">${t.explanation}</div>
                </div>
            `).join('')}`;
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load grammar topics.</p></div>`;
    }
}

async function loadGrammarLesson(topic) {
    const content = document.getElementById('grammar-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Generating grammar lesson...</p>
        </div>`;
    try {
        const url = `/api/grammar/lesson?user_id=${userId}&level=${userLevel || 'A2'}${topic ? '&topic=' + encodeURIComponent(topic) : ''}`;
        const res = await fetch(url);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        const lesson = data.lesson;
        grammarState = { lesson, currentExercise: 0, correct: 0, total: lesson.exercises.length };
        renderGrammarLesson();
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to generate grammar lesson.</p></div>`;
    }
}

function renderGrammarLesson() {
    const content = document.getElementById('grammar-content');
    const lesson = grammarState.lesson;
    const ex = lesson.exercises[grammarState.currentExercise];
    const progress = (grammarState.currentExercise / grammarState.total) * 100;

    let exerciseHtml = '';
    if (ex.type === 'multiple_choice') {
        exerciseHtml = `
            <div class="card">
                <h3>${ex.instruction}</h3>
                <p style="margin:12px 0">${ex.sentence}</p>
                <div>
                    ${ex.options.map((opt, i) => `
                        <button class="option" onclick="checkGrammarAnswer(${i})">${opt}</button>
                    `).join('')}
                </div>
                ${ex.hint ? `<p style="font-size:12px;color:var(--text-muted);margin-top:8px">💡 ${ex.hint}</p>` : ''}
            </div>`;
    } else if (ex.type === 'fill_blank') {
        exerciseHtml = `
            <div class="card">
                <h3>${ex.instruction}</h3>
                <p style="margin:12px 0">${ex.sentence}</p>
                <input class="input" id="grammar-answer" placeholder="Type your answer...">
                ${ex.hint ? `<p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">💡 ${ex.hint}</p>` : ''}
                <button class="btn btn-primary" onclick="checkGrammarFill()">Check Answer</button>
            </div>`;
    } else if (ex.type === 'reorder') {
        exerciseHtml = `
            <div class="card">
                <h3>${ex.instruction}</h3>
                <p style="margin:12px 0">${ex.words.join(' ')}</p>
                <input class="input" id="grammar-answer" placeholder="Type the correct order...">
                ${ex.hint ? `<p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">💡 ${ex.hint}</p>` : ''}
                <button class="btn btn-primary" onclick="checkGrammarFill()">Check Answer</button>
            </div>`;
    } else {
        exerciseHtml = `
            <div class="card">
                <h3>${ex.instruction}</h3>
                <p style="margin:12px 0">${ex.sentence || ''}</p>
                <input class="input" id="grammar-answer" placeholder="Type your answer...">
                <button class="btn btn-primary" onclick="checkGrammarFill()">Check Answer</button>
            </div>`;
    }

    content.innerHTML = `
        <button class="btn btn-secondary" onclick="loadGrammar()">← Back to Topics</button>
        <div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div>
        <div class="card">
            <h3>📖 ${lesson.topic}</h3>
            <div class="result-box">${lesson.explanation}</div>
            <div style="margin-bottom:12px">
                ${lesson.examples.map(e => `<div class="result-box" style="margin-bottom:8px">${e}</div>`).join('')}
            </div>
        </div>
        <div class="section-title">Exercise ${grammarState.currentExercise + 1} of ${grammarState.total}</div>
        ${exerciseHtml}
        <div id="grammar-feedback"></div>`;
}

async function checkGrammarAnswer(index) {
    const ex = grammarState.lesson.exercises[grammarState.currentExercise];
    const res = await fetch('/api/grammar/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exercise: ex, answer: index })
    });
    const data = await res.json();
    if (data.correct) {
        grammarState.correct++;
        showToast('✅ Correct!');
        nextGrammarExercise();
    } else {
        showToast('❌ Try again!');
    }
}

async function checkGrammarFill() {
    const answer = document.getElementById('grammar-answer').value.trim();
    if (!answer) { showToast('Please type an answer'); return; }
    const ex = grammarState.lesson.exercises[grammarState.currentExercise];
    const res = await fetch('/api/grammar/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exercise: ex, answer })
    });
    const data = await res.json();
    if (data.correct) {
        grammarState.correct++;
        showToast('✅ Correct!');
        nextGrammarExercise();
    } else {
        showToast('❌ Try again!');
    }
}

function nextGrammarExercise() {
    grammarState.currentExercise++;
    if (grammarState.currentExercise >= grammarState.total) {
        const score = Math.round((grammarState.correct / grammarState.total) * 100);
        const content = document.getElementById('grammar-content');
        showConfetti();
        showXpPopup(score >= 80 ? 20 : 10);
        content.innerHTML = `
            <button class="btn btn-secondary" onclick="loadGrammar()">← Back to Topics</button>
            <div class="card" style="text-align:center;animation:scaleIn 0.4s ease">
                <h3 style="font-size:24px;margin-bottom:8px">🎉 Lesson Complete!</h3>
                <p style="font-size:18px;font-weight:700;color:var(--accent)">Score: ${score}%</p>
                <p style="margin-top:8px">${score >= 80 ? 'Excellent work! You mastered this topic!' : 'Good effort! Keep practicing!'}</p>
            </div>
            <button class="btn btn-primary" onclick="loadGrammarLesson()">📖 Next Topic</button>`;
        loadStats();
    } else {
        renderGrammarLesson();
    }
}

// ============ АУДИРОВАНИЕ ============
async function loadListening() {
    const content = document.getElementById('listening-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading listening topics...</p>
        </div>`;
    try {
        const res = await fetch(`/api/listening/topics?user_id=${userId}&level=${userLevel || 'A2'}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        content.innerHTML = `
            <div class="tab-bar">
                <div class="tab active" onclick="loadListening()">Topics</div>
                <div class="tab" onclick="loadListeningLesson()">Practice</div>
            </div>
            ${data.topics.map(t => `
                <div class="module-card" onclick="loadListeningLesson('${t.topic}')">
                    <div class="module-title">🎧 ${t.topic}</div>
                    <div class="module-desc">Listening comprehension practice</div>
                </div>
            `).join('')}`;
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load listening topics.</p></div>`;
    }
}

async function loadListeningLesson(topic) {
    const content = document.getElementById('listening-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Generating listening lesson...</p>
        </div>`;
    try {
        const url = `/api/listening/lesson?user_id=${userId}&level=${userLevel || 'A2'}${topic ? '&topic=' + encodeURIComponent(topic) : ''}`;
        const res = await fetch(url);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        const lesson = data.lesson;
        listeningState = { lesson, currentQuestion: 0, correct: 0, total: lesson.questions.length };
        renderListeningLesson();
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to generate listening lesson.</p></div>`;
    }
}

function renderListeningLesson() {
    const content = document.getElementById('listening-content');
    const lesson = listeningState.lesson;
    const q = lesson.questions[listeningState.currentQuestion];
    const progress = (listeningState.currentQuestion / listeningState.total) * 100;

    let questionHtml = '';
    if (q.type === 'multiple_choice') {
        questionHtml = `
            <div class="card">
                <h3>${q.question}</h3>
                <div style="margin-top:12px">
                    ${q.options.map((opt, i) => `
                        <button class="option" onclick="checkListeningAnswer(${i})">${opt}</button>
                    `).join('')}
                </div>
            </div>`;
    } else if (q.type === 'true_false') {
        questionHtml = `
            <div class="card">
                <h3>${q.question}</h3>
                <div style="margin-top:12px">
                    <button class="option" onclick="checkListeningAnswer(true)">✅ True</button>
                    <button class="option" onclick="checkListeningAnswer(false)">❌ False</button>
                </div>
            </div>`;
    } else {
        questionHtml = `
            <div class="card">
                <h3>${q.question}</h3>
                <input class="input" id="listening-answer" placeholder="Type your answer...">
                <button class="btn btn-primary" onclick="checkListeningFill()">Check Answer</button>
            </div>`;
    }

    content.innerHTML = `
        <button class="btn btn-secondary" onclick="loadListening()">← Back to Topics</button>
        <div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div>
        <div class="card">
            <h3>🎧 ${lesson.topic}</h3>
            <p style="color:var(--text-muted);font-size:13px;margin-bottom:12px">Listen carefully and answer the questions</p>
            <div class="result-box">${lesson.transcript}</div>
        </div>
        <div class="section-title">Question ${listeningState.currentQuestion + 1} of ${listeningState.total}</div>
        ${questionHtml}
        <div id="listening-feedback"></div>`;
}

async function checkListeningAnswer(answer) {
    const q = listeningState.lesson.questions[listeningState.currentQuestion];
    const res = await fetch('/api/listening/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, answer })
    });
    const data = await res.json();
    if (data.correct) {
        listeningState.correct++;
        showToast('✅ Correct!');
        nextListeningQuestion();
    } else {
        showToast('❌ Try again!');
    }
}

async function checkListeningFill() {
    const answer = document.getElementById('listening-answer').value.trim();
    if (!answer) { showToast('Please type an answer'); return; }
    const q = listeningState.lesson.questions[listeningState.currentQuestion];
    const res = await fetch('/api/listening/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, answer })
    });
    const data = await res.json();
    if (data.correct) {
        listeningState.correct++;
        showToast('✅ Correct!');
        nextListeningQuestion();
    } else {
        showToast('❌ Try again!');
    }
}

function nextListeningQuestion() {
    listeningState.currentQuestion++;
    if (listeningState.currentQuestion >= listeningState.total) {
        const score = Math.round((listeningState.correct / listeningState.total) * 100);
        const content = document.getElementById('listening-content');
        showConfetti();
        showXpPopup(score >= 80 ? 20 : 10);
        content.innerHTML = `
            <button class="btn btn-secondary" onclick="loadListening()">← Back to Topics</button>
            <div class="card" style="text-align:center;animation:scaleIn 0.4s ease">
                <h3 style="font-size:24px;margin-bottom:8px">🎉 Listening Complete!</h3>
                <p style="font-size:18px;font-weight:700;color:var(--accent)">Score: ${score}%</p>
                <p style="margin-top:8px">${score >= 80 ? 'Great listening skills!' : 'Keep practicing your listening!'}</p>
            </div>
            <button class="btn btn-primary" onclick="loadListeningLesson()">🎧 Next Topic</button>`;
        loadStats();
    } else {
        renderListeningLesson();
    }
}

// ============ РАЗГОВОРНАЯ ПРАКТИКА ============
async function loadSpeaking() {
    const content = document.getElementById('speaking-content');
    content.innerHTML = `
        <div class="tab-bar">
            <div class="tab active" onclick="loadSpeaking()">Role-plays</div>
            <div class="tab" onclick="loadSpeakingPictures()">Pictures</div>
            <div class="tab" onclick="loadSpeakingDialogue()">Chat</div>
        </div>
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading role-play scenarios...</p>
        </div>`;
    try {
        const res = await fetch(`/api/speaking/roleplay?user_id=${userId}&level=${userLevel || 'A2'}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        content.innerHTML = `
            <div class="tab-bar">
                <div class="tab active" onclick="loadSpeaking()">Role-plays</div>
                <div class="tab" onclick="loadSpeakingPictures()">Pictures</div>
                <div class="tab" onclick="loadSpeakingDialogue()">Chat</div>
            </div>
            ${data.scenarios.map(s => `
                <div class="module-card" onclick="startRolePlay('${s.id}')">
                    <div class="module-title">🎭 ${s.title}</div>
                    <div class="module-desc">${s.description}</div>
                    <div class="tag speaking" style="margin-top:8px">${s.ai_role}</div>
                </div>
            `).join('')}`;
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load role-play scenarios.</p></div>`;
    }
}

async function startRolePlay(scenarioId) {
    const content = document.getElementById('speaking-content');
    try {
        const res = await fetch(`/api/speaking/roleplay?user_id=${userId}&level=${userLevel || 'A2'}`);
        const data = await res.json();
        const scenario = data.scenarios.find(s => s.id === scenarioId);
        if (!scenario) { showToast('Scenario not found'); return; }
        speakingState = { mode: 'roleplay', scenario, messages: [] };
        content.innerHTML = `
            <button class="btn btn-secondary" onclick="loadSpeaking()">← Back</button>
            <div class="card">
                <h3>🎭 ${scenario.title}</h3>
                <p>${scenario.description}</p>
                <div class="tag speaking" style="margin-top:8px">${scenario.ai_role}</div>
                <div style="margin-top:12px">
                    ${scenario.tips.map(t => `<div class="tag vocab">💡 ${t}</div>`).join('')}
                </div>
            </div>
            <div class="chat-area" id="speaking-chat"></div>
            <div class="card">
                <input class="input" id="speaking-input" placeholder="Type your response...">
                <button class="btn btn-primary" onclick="sendSpeakingMessage()">Send</button>
            </div>`;
        addSpeakingMessage(scenario.starter, 'bot');
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to start role-play.</p></div>`;
    }
}

function addSpeakingMessage(text, type) {
    const area = document.getElementById('speaking-chat');
    if (!area) return;
    const div = document.createElement('div');
    div.className = 'chat-bubble ' + (type === 'user' ? 'chat-user' : 'chat-bot');
    div.textContent = text;
    area.appendChild(div);
    area.scrollTop = area.scrollHeight;
}

async function sendSpeakingMessage() {
    const input = document.getElementById('speaking-input');
    const text = input.value.trim();
    if (!text) { showToast('Please type a message'); return; }
    input.value = '';
    addSpeakingMessage(text, 'user');
    speakingState.messages.push({ role: 'user', content: text });
    try {
        const res = await fetch('/api/speaking/dialogue', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                text,
                history: speakingState.messages,
                scenario: speakingState.scenario
            })
        });
        const data = await res.json();
        if (data.error) {
            addSpeakingMessage('❌ ' + data.error, 'bot');
            return;
        }
        if (data.corrections && data.corrections.length > 0) {
            addSpeakingMessage('📝 Corrections: ' + data.corrections.join('; '), 'bot');
        }
        addSpeakingMessage('🤖 ' + data.reply, 'bot');
        if (data.feedback) {
            addSpeakingMessage('💬 ' + data.feedback, 'bot');
        }
        speakingState.messages.push({ role: 'assistant', content: data.reply });
    } catch (e) {
        addSpeakingMessage('❌ Failed to send message', 'bot');
    }
}

async function loadSpeakingPictures() {
    const content = document.getElementById('speaking-content');
    content.innerHTML = `
        <div class="tab-bar">
            <div class="tab" onclick="loadSpeaking()">Role-plays</div>
            <div class="tab active" onclick="loadSpeakingPictures()">Pictures</div>
            <div class="tab" onclick="loadSpeakingDialogue()">Chat</div>
        </div>
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading picture topics...</p>
        </div>`;
    try {
        const res = await fetch(`/api/speaking/pictures?user_id=${userId}&level=${userLevel || 'A2'}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        content.innerHTML = `
            <div class="tab-bar">
                <div class="tab" onclick="loadSpeaking()">Role-plays</div>
                <div class="tab active" onclick="loadSpeakingPictures()">Pictures</div>
                <div class="tab" onclick="loadSpeakingDialogue()">Chat</div>
            </div>
            ${data.topics.map(t => `
                <div class="module-card" onclick="startPictureDescription('${t.id}')">
                    <div class="module-title">🖼️ ${t.title}</div>
                    <div class="module-desc">${t.description}</div>
                </div>
            `).join('')}`;
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load picture topics.</p></div>`;
    }
}

async function startPictureDescription(topicId) {
    const content = document.getElementById('speaking-content');
    try {
        const res = await fetch(`/api/speaking/picture?user_id=${userId}&level=${userLevel || 'A2'}&topic_id=${topicId}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        const topic = data.topic;
        content.innerHTML = `
            <button class="btn btn-secondary" onclick="loadSpeakingPictures()">← Back</button>
            <div class="card">
                <h3>🖼️ ${topic.title}</h3>
                <p>${topic.description}</p>
            </div>
            <div class="card">
                <textarea class="input" id="picture-desc" placeholder="Describe the picture in English..."></textarea>
                <button class="btn btn-primary" onclick="evaluatePictureDescription()">Submit Description</button>
            </div>
            <div id="picture-feedback"></div>`;
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load picture.</p></div>`;
    }
}

async function evaluatePictureDescription() {
    const desc = document.getElementById('picture-desc').value.trim();
    if (!desc) { showToast('Please describe the picture'); return; }
    const feedback = document.getElementById('picture-feedback');
    feedback.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Evaluating your description...</p>
        </div>`;
    try {
        const res = await fetch('/api/speaking/picture/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, description: desc, topic: { title: 'Picture' } })
        });
        const data = await res.json();
        if (data.error) {
            feedback.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        showConfetti();
        showXpPopup(data.score >= 80 ? 20 : 10);
        feedback.innerHTML = `
            <div class="card" style="text-align:center;animation:scaleIn 0.4s ease">
                <h3 style="font-size:24px;margin-bottom:8px">📊 Score</h3>
                <p style="font-size:18px;font-weight:700;color:var(--accent)">${data.score}/100</p>
                <p style="margin-top:8px">${data.feedback}</p>
            </div>
            ${data.suggestions && data.suggestions.length > 0 ? `
            <div class="card">
                <h3>💡 Suggestions</h3>
                ${data.suggestions.map(s => `<div class="tag vocab">${s}</div>`).join('')}
            </div>` : ''}
            ${data.corrections && data.corrections.length > 0 ? `
            <div class="card">
                <h3>📝 Corrections</h3>
                ${data.corrections.map(c => `<div class="correction">${c}</div>`).join('')}
            </div>` : ''}`;
        loadStats();
    } catch (e) {
        feedback.innerHTML = `<div class="card"><p class="error-text">Failed to evaluate description.</p></div>`;
    }
}

async function loadSpeakingDialogue() {
    const content = document.getElementById('speaking-content');
    speakingState = { mode: 'dialogue', messages: [] };
    content.innerHTML = `
        <div class="tab-bar">
            <div class="tab" onclick="loadSpeaking()">Role-plays</div>
            <div class="tab" onclick="loadSpeakingPictures()">Pictures</div>
            <div class="tab active" onclick="loadSpeakingDialogue()">Chat</div>
        </div>
        <div class="card">
            <h3>💬 Free Conversation</h3>
            <p>Chat with your AI tutor. Get corrections and feedback in real-time.</p>
        </div>
        <div class="chat-area" id="speaking-chat"></div>
        <div class="card">
            <input class="input" id="speaking-input" placeholder="Type your message...">
            <button class="btn btn-primary" onclick="sendSpeakingMessage()">Send</button>
        </div>`;
    addSpeakingMessage('Hello! I am your English tutor. What would you like to talk about today?', 'bot');
}

// ============ DAILY PRACTICE ============
async function loadDaily() {
    const content = document.getElementById('daily-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading your daily practice...</p>
        </div>`;
    try {
        const res = await fetch(`/api/daily-practice?user_id=${userId}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        const practice = data.practice || data;
        const exercises = practice.practice || practice.exercises || [];
        dailyState = practice;
        content.innerHTML = `
            <div class="card" style="background:linear-gradient(135deg,rgba(56,189,248,0.1),rgba(129,140,248,0.1));border-color:var(--accent)">
                <h3>⚡ Daily Practice</h3>
                <p>${practice.module_title || 'Quick exercises to keep your streak alive'}</p>
                <div class="tag grammar" style="margin-top:8px">${exercises.length} exercises</div>
            </div>
            ${exercises.map((ex, i) => `
                <div class="module-card" onclick="openDailyExercise(${i})">
                    <div class="module-title">${ex.icon || '📝'} ${ex.title || ex.type}</div>
                    <div class="module-desc">${ex.content && ex.content.exercise ? ex.content.exercise : (ex.description || ex.instruction || '')}</div>
                </div>
            `).join('')}`;
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load daily practice.</p></div>`;
    }
}

function openDailyExercise(index) {
    const content = document.getElementById('daily-content');
    const practice = dailyState || {};
    const exercises = practice.practice || practice.exercises || [];
    const ex = exercises[index];
    if (!ex) { showToast('Exercise not found'); return; }
    const exContent = ex.content || {};
    content.innerHTML = `
        <button class="btn btn-secondary" onclick="loadDaily()">← Back</button>
        <div class="card">
            <h3>${ex.icon || '📝'} ${ex.title || ex.type}</h3>
            <p>${exContent.introduction || ex.instruction || ex.description || ''}</p>
            <div class="result-box" style="margin-top:12px">${exContent.exercise || exContent.explanation || ''}</div>
            ${exContent.examples ? `<div style="margin-top:8px">${exContent.examples.map(e => `<div class="tag vocab">${e}</div>`).join('')}</div>` : ''}
        </div>
        <button class="btn btn-success" onclick="completeDailyExercise()">✅ Complete</button>`;
}

async function completeDailyExercise() {
    const content = document.getElementById('daily-content');
    showConfetti();
    showXpPopup(10);
    content.innerHTML = `
        <div class="card" style="text-align:center;animation:scaleIn 0.4s ease">
            <h3 style="font-size:24px;margin-bottom:8px">🎉 Great job!</h3>
            <p style="font-size:18px;font-weight:700;color:var(--accent)">+10 XP</p>
            <p style="margin-top:8px">Keep your streak alive!</p>
        </div>
        <button class="btn btn-primary" onclick="loadDaily()">⚡ More Exercises</button>
        <button class="btn btn-secondary" onclick="showView('home')">🏠 Home</button>`;
    loadStats();
}

// ============ ДОСТИЖЕНИЯ ============
async function loadAchievements() {
    const content = document.getElementById('achievements-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading your achievements...</p>
        </div>`;
    try {
        const res = await fetch(`/api/achievements?user_id=${userId}`);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = `<div class="card"><p class="error-text">${data.error}</p></div>`;
            return;
        }
        const achievements = data.achievements || [];
        content.innerHTML = `
            <div class="card">
                <h3>🏆 Your Achievements</h3>
                <p>${achievements.length} unlocked</p>
            </div>
            <div class="achievement-grid">
                ${achievements.map(a => `
                    <div class="achievement-item">
                        <span class="icon">${a.icon || '🏅'}</span>
                        <div class="name">${a.title}</div>
                    </div>
                `).join('')}
            </div>`;
    } catch (e) {
        content.innerHTML = `<div class="card"><p class="error-text">Failed to load achievements.</p></div>`;
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', initTelegram);
