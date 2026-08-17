import sqlite3
import json
import logging
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
            streak INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            original TEXT,
            corrected TEXT,
            context TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            word TEXT,
            translation TEXT,
            level TEXT DEFAULT 'A2',
            next_review TEXT,
            interval INTEGER DEFAULT 0,
            ease_factor REAL DEFAULT 2.5,
            repetitions INTEGER DEFAULT 0
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

    # Миграция: добавляем колонки ease_factor и repetitions, если их ещё нет
    # (для уже существующих БД без этих колонок)
    _migrations = [
        ("ease_factor", "REAL DEFAULT 2.5"),
        ("repetitions", "INTEGER DEFAULT 0"),
    ]
    for col, col_def in _migrations:
        try:
            c.execute(f"ALTER TABLE words ADD COLUMN {col} {col_def}")
            logger.info(f"Added column {col} to words table")
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

def save_user_data(user_id, level=None, history=None, current_practice=None):
    conn = get_connection()
    c = conn.cursor()
    if level is not None:
        c.execute("UPDATE users SET level = ? WHERE user_id = ?", (level, user_id))
    if history is not None:
        c.execute("UPDATE users SET history = ? WHERE user_id = ?", (json.dumps(history), user_id))
    if current_practice is not None:
        c.execute("UPDATE users SET current_practice = ? WHERE user_id = ?", (current_practice, user_id))
    conn.commit()
    conn.close()

def append_message(user_id, role, text):
    level, history, current_practice = get_user_data(user_id)
    history.append({"role": role, "content": text})
    if len(history) > 20:
        history = history[-20:]
    save_user_data(user_id, history=history)

def save_error(user_id, original, corrected, context=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO errors (user_id, original, corrected, context) VALUES (?, ?, ?, ?)",
              (user_id, original, corrected, context))
    conn.commit()
    conn.close()