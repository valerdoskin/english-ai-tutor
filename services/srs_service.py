"""
srs_service.py — интервальное повторение (Spaced Repetition System).

Реализует алгоритм SM-2 (аналог Anki) для слов, фраз и грамматических конструкций.
"""
import logging
from datetime import datetime, timedelta

from database import get_connection

logger = logging.getLogger(__name__)


def add_word(user_id, word, translation, example=None, level="A2", item_type="word"):
    """Добавляет слово/фразу/грамматическую конструкцию в систему SRS."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO words (user_id, word, translation, example, level, item_type) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, word, translation, example, level, item_type),
    )
    conn.commit()
    word_id = c.lastrowid
    conn.close()
    return word_id


def add_phrase(user_id, phrase, translation, example=None, level="B1"):
    """Добавляет фразу в систему SRS."""
    return add_word(user_id, phrase, translation, example, level, item_type="phrase")


def add_grammar_item(user_id, pattern, explanation, example=None, level="B1"):
    """Добавляет грамматическую конструкцию в систему SRS."""
    return add_word(user_id, pattern, explanation, example, level, item_type="grammar")


def get_due_words(user_id, limit=20, item_type=None):
    """Возвращает слова/фразы, которые нужно повторить сегодня."""
    today = datetime.now().isoformat()
    conn = get_connection()
    c = conn.cursor()
    if item_type:
        c.execute("""
            SELECT * FROM words
            WHERE user_id = ? AND item_type = ? AND (next_review IS NULL OR next_review <= ?)
            ORDER BY next_review IS NULL DESC, next_review ASC
            LIMIT ?
        """, (user_id, item_type, today, limit))
    else:
        c.execute("""
            SELECT * FROM words
            WHERE user_id = ? AND (next_review IS NULL OR next_review <= ?)
            ORDER BY next_review IS NULL DESC, next_review ASC
            LIMIT ?
        """, (user_id, today, limit))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_words(user_id):
    """Возвращает все слова пользователя."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM words WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def review_word(user_id, word_id, quality):
    """
    Обновляет интервал повторения по алгоритму SM-2.
    quality: 0-5 (0 = полное забывание, 5 = идеальное припоминание)
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM words WHERE id = ? AND user_id = ?", (word_id, user_id))
    row = c.fetchone()
    if not row:
        conn.close()
        return None

    interval = row["interval"] or 0
    ease = row["ease_factor"] or 2.5
    reps = row["repetitions"] or 0

    # SM-2 алгоритм
    ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if ease < 1.3:
        ease = 1.3

    if quality < 3:
        interval = 1
        reps = 0
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = int(interval * ease)
        reps += 1

    next_review = (datetime.now() + timedelta(days=interval)).isoformat()
    c.execute("""
        UPDATE words SET interval = ?, ease_factor = ?, repetitions = ?, next_review = ?
        WHERE id = ? AND user_id = ?
    """, (interval, ease, reps, next_review, word_id, user_id))
    conn.commit()
    conn.close()

    return {
        "word_id": word_id,
        "interval": interval,
        "ease_factor": round(ease, 2),
        "repetitions": reps,
        "next_review": next_review,
    }


def get_word_stats(user_id):
    """Возвращает статистику по словам."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM words WHERE user_id = ?", (user_id,))
    total = c.fetchone()[0]
    today = datetime.now().isoformat()
    c.execute("SELECT COUNT(*) FROM words WHERE user_id = ? AND next_review <= ?", (user_id, today))
    due = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM words WHERE user_id = ? AND repetitions >= 3", (user_id,))
    mastered = c.fetchone()[0]
    conn.close()
    return {
        "total": total,
        "due": due,
        "mastered": mastered,
    }
