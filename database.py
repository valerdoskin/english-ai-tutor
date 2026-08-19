import sqlite3
import json
import logging
from datetime import datetime, date
from config import DB_PATH

logger = logging.getLogger(__name__)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            level TEXT DEFAULT 'A2',
            history TEXT DEFAULT '[]',
            current_practice TEXT,
            xp INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_active DATE,
            rank TEXT DEFAULT 'Bronze'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            original TEXT,
            corrected TEXT,
            context TEXT,
            error_type TEXT DEFAULT 'grammar',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            word TEXT,
            translation TEXT,
            example TEXT,
            level TEXT DEFAULT 'A2',
            next_review TEXT,
            interval INTEGER DEFAULT 0,
            ease_factor REAL DEFAULT 2.5,
            repetitions INTEGER DEFAULT 0,
            item_type TEXT DEFAULT 'word'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            xp INTEGER DEFAULT 0,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT,
            title TEXT,
            description TEXT,
            task TEXT,
            order_index INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            module_id INTEGER,
            lesson_type TEXT,
            title TEXT,
            content TEXT,
            completed BOOLEAN DEFAULT 0,
            score INTEGER,
            completed_at DATETIME
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            achievement_key TEXT,
            title TEXT,
            description TEXT,
            unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            goal_date DATE,
            goal_type TEXT,
            target INTEGER DEFAULT 1,
            progress INTEGER DEFAULT 0,
            completed BOOLEAN DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS test_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            state TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Миграции для существующих БД
    _migrations = [
        ("users", "last_active", "DATE"),
        ("users", "rank", "TEXT DEFAULT 'Bronze'"),
        ("words", "example", "TEXT"),
        ("words", "ease_factor", "REAL DEFAULT 2.5"),
        ("words", "repetitions", "INTEGER DEFAULT 0"),
        ("words", "item_type", "TEXT DEFAULT 'word'"),
        ("errors", "error_type", "TEXT DEFAULT 'grammar'"),
        ("modules", "task", "TEXT"),
    ]
    for table, col, col_def in _migrations:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
            logger.info(f"Added column {col} to {table} table")
        except Exception:
            # Колонка уже существует — пропускаем
            pass

    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, level, history) VALUES (?, 'A2', '[]')", (user_id,))
        conn.commit()
        conn.close()
        return "A2", [], None
    conn.close()
    level = row["level"]
    history = json.loads(row["history"] or "[]")
    current_practice = row["current_practice"]
    return level, history, current_practice

def save_user_data(user_id, level=None, history=None, current_practice=None, xp=None, streak=None, last_active=None, rank=None):
    conn = get_connection()
    c = conn.cursor()
    if level is not None:
        c.execute("UPDATE users SET level = ? WHERE user_id = ?", (level, user_id))
    if history is not None:
        c.execute("UPDATE users SET history = ? WHERE user_id = ?", (json.dumps(history), user_id))
    if current_practice is not None:
        c.execute("UPDATE users SET current_practice = ? WHERE user_id = ?", (current_practice, user_id))
    if xp is not None:
        c.execute("UPDATE users SET xp = ? WHERE user_id = ?", (xp, user_id))
    if streak is not None:
        c.execute("UPDATE users SET streak = ? WHERE user_id = ?", (streak, user_id))
    if last_active is not None:
        c.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (last_active, user_id))
    if rank is not None:
        c.execute("UPDATE users SET rank = ? WHERE user_id = ?", (rank, user_id))
    conn.commit()
    conn.close()

def append_message(user_id, role, text):
    level, history, current_practice = get_user_data(user_id)
    history.append({"role": role, "content": text})
    if len(history) > 20:
        history = history[-20:]
    save_user_data(user_id, history=history)

def save_error(user_id, original, corrected, context="", error_type="grammar"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO errors (user_id, original, corrected, context, error_type) VALUES (?, ?, ?, ?, ?)",
              (user_id, original, corrected, context, error_type))
    conn.commit()
    conn.close()

def add_xp(user_id, amount):
    """Начисляет XP пользователю и обновляет ранг."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT xp FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    current_xp = row["xp"] if row else 0
    new_xp = current_xp + amount
    rank = _rank_for_xp(new_xp)
    c.execute("UPDATE users SET xp = ?, rank = ? WHERE user_id = ?", (new_xp, rank, user_id))
    conn.commit()
    conn.close()
    return new_xp, rank

def _rank_for_xp(xp):
    """Определяет ранг по количеству XP."""
    if xp >= 5000:
        return "Diamond"
    elif xp >= 2000:
        return "Platinum"
    elif xp >= 1000:
        return "Gold"
    elif xp >= 400:
        return "Silver"
    return "Bronze"

def update_streak(user_id):
    """Обновляет ежедневную серию (streak). Возвращает текущий streak."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT streak, last_active FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return 0
    today = date.today().isoformat()
    streak = row["streak"] or 0
    last_active = row["last_active"]
    if last_active == today:
        # Уже занимался сегодня — streak не меняется
        pass
    elif last_active:
        from datetime import timedelta
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if last_active == yesterday:
            streak += 1
        else:
            streak = 1
    else:
        streak = 1
    c.execute("UPDATE users SET streak = ?, last_active = ? WHERE user_id = ?", (streak, today, user_id))
    conn.commit()
    conn.close()
    return streak

def log_activity(user_id, action, xp=0, details=None):
    """Записывает действие в activity_log."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO activity_log (user_id, action, xp, details) VALUES (?, ?, ?, ?)",
              (user_id, action, xp, json.dumps(details) if details else None))
    conn.commit()
    conn.close()

# === Модули и уроки ===

def get_modules(level=None):
    """Возвращает список модулей (опционально по уровню)."""
    conn = get_connection()
    c = conn.cursor()
    if level:
        c.execute("SELECT * FROM modules WHERE level = ? ORDER BY order_index", (level,))
    else:
        c.execute("SELECT * FROM modules ORDER BY level, order_index")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_module(module_id):
    """Возвращает модуль по id."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM modules WHERE id = ?", (module_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def create_module(level, title, description, order_index, task=None):
    """Создаёт модуль."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO modules (level, title, description, task, order_index) VALUES (?, ?, ?, ?, ?)",
              (level, title, description, task, order_index))
    conn.commit()
    module_id = c.lastrowid
    conn.close()
    return module_id

def get_lessons(user_id, module_id=None):
    """Возвращает уроки пользователя (опционально по модулю)."""
    conn = get_connection()
    c = conn.cursor()
    if module_id:
        c.execute("SELECT * FROM lessons WHERE user_id = ? AND module_id = ? ORDER BY id", (user_id, module_id))
    else:
        c.execute("SELECT * FROM lessons WHERE user_id = ? ORDER BY id", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_lesson(user_id, lesson_id):
    """Возвращает урок по id."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM lessons WHERE id = ? AND user_id = ?", (lesson_id, user_id))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def create_lesson(user_id, module_id, lesson_type, title, content=None):
    """Создаёт урок."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO lessons (user_id, module_id, lesson_type, title, content) VALUES (?, ?, ?, ?, ?)",
              (user_id, module_id, lesson_type, title, json.dumps(content) if content else None))
    conn.commit()
    lesson_id = c.lastrowid
    conn.close()
    return lesson_id

def complete_lesson(user_id, lesson_id, score=None):
    """Отмечает урок завершённым."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE lessons SET completed = 1, score = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
              (score, lesson_id, user_id))
    conn.commit()
    conn.close()

# === Достижения ===

def unlock_achievement(user_id, achievement_key, title, description):
    """Разблокирует достижение, если его ещё нет."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM achievements WHERE user_id = ? AND achievement_key = ?", (user_id, achievement_key))
    if c.fetchone():
        conn.close()
        return False
    c.execute("INSERT INTO achievements (user_id, achievement_key, title, description) VALUES (?, ?, ?, ?)",
              (user_id, achievement_key, title, description))
    conn.commit()
    conn.close()
    return True

def get_achievements(user_id):
    """Возвращает достижения пользователя."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM achievements WHERE user_id = ? ORDER BY unlocked_at", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# === Ежедневные цели ===

def get_daily_goal(user_id, goal_date=None):
    """Возвращает ежедневную цель пользователя."""
    if not goal_date:
        goal_date = date.today().isoformat()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM daily_goals WHERE user_id = ? AND goal_date = ?", (user_id, goal_date))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def set_daily_goal(user_id, goal_type, target=1, goal_date=None):
    """Устанавливает ежедневную цель."""
    if not goal_date:
        goal_date = date.today().isoformat()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM daily_goals WHERE user_id = ? AND goal_date = ?", (user_id, goal_date))
    existing = c.fetchone()
    if existing:
        c.execute("UPDATE daily_goals SET goal_type = ?, target = ? WHERE id = ?", (goal_type, target, existing["id"]))
    else:
        c.execute("INSERT INTO daily_goals (user_id, goal_date, goal_type, target) VALUES (?, ?, ?, ?)",
                  (user_id, goal_date, goal_type, target))
    conn.commit()
    conn.close()

def update_daily_goal_progress(user_id, goal_type, amount=1, goal_date=None):
    """Увеличивает прогресс ежедневной цели."""
    if not goal_date:
        goal_date = date.today().isoformat()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM daily_goals WHERE user_id = ? AND goal_date = ? AND goal_type = ?", (user_id, goal_date, goal_type))
    row = c.fetchone()
    if row:
        progress = row["progress"] + amount
        completed = 1 if progress >= row["target"] else 0
        c.execute("UPDATE daily_goals SET progress = ?, completed = ? WHERE id = ?", (progress, completed, row["id"]))
    else:
        c.execute("INSERT INTO daily_goals (user_id, goal_date, goal_type, target, progress, completed) VALUES (?, ?, ?, 1, ?, ?)",
                  (user_id, goal_date, goal_type, amount, 1 if amount >= 1 else 0))
    conn.commit()
    conn.close()

# === Test sessions (адаптивный тест) ===

def save_test_session(user_id, state):
    """Сохраняет состояние адаптивного теста."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM test_sessions WHERE user_id = ?", (user_id,))
    existing = c.fetchone()
    if existing:
        c.execute("UPDATE test_sessions SET state = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                  (json.dumps(state), existing["id"]))
    else:
        c.execute("INSERT INTO test_sessions (user_id, state) VALUES (?, ?)",
                  (user_id, json.dumps(state)))
    conn.commit()
    conn.close()


def get_test_session(user_id):
    """Возвращает состояние адаптивного теста или None."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT state FROM test_sessions WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row and row["state"]:
        return json.loads(row["state"])
    return None


def delete_test_session(user_id):
    """Удаляет состояние адаптивного теста."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM test_sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
