"""
analytics_service.py — аналитика и отчёты по прогрессу.

Отвечает за:
- Статистику ошибок (по типам)
- Активность по дням
- Прогресс по навыкам
- Отчёты для пользователя
"""
import logging
from datetime import date, datetime, timedelta

from database import get_connection

logger = logging.getLogger(__name__)

# Навыки, которые отслеживаются
SKILLS = ["grammar", "vocabulary", "listening", "speaking", "reading", "writing"]


def get_error_stats(user_id):
    """Возвращает статистику ошибок по типам."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT error_type, COUNT(*) as count
        FROM errors
        WHERE user_id = ?
        GROUP BY error_type
        ORDER BY count DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_errors(user_id, limit=20):
    """Возвращает последние ошибки пользователя."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM errors
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_activity_by_day(user_id, days=30):
    """Возвращает активность по дням за последние N дней."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT date(timestamp) as day, COUNT(*) as actions, COALESCE(SUM(xp), 0) as xp
        FROM activity_log
        WHERE user_id = ? AND timestamp >= datetime('now', ?)
        GROUP BY date(timestamp)
        ORDER BY day
    """, (user_id, f"-{days} days"))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_skill_progress(user_id):
    """Возвращает прогресс по навыкам на основе завершённых уроков."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT lesson_type, COUNT(*) as total, SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
        FROM lessons
        WHERE user_id = ?
        GROUP BY lesson_type
    """, (user_id,))
    rows = c.fetchall()
    conn.close()

    progress = {}
    for skill in SKILLS:
        progress[skill] = {"total": 0, "completed": 0, "percent": 0}

    for r in rows:
        skill = r["lesson_type"]
        if skill in progress:
            progress[skill]["total"] = r["total"]
            progress[skill]["completed"] = r["completed"]
            if r["total"] > 0:
                progress[skill]["percent"] = round((r["completed"] / r["total"]) * 100)

    return progress


def get_weak_areas(user_id):
    """Определяет слабые места на основе ошибок."""
    error_stats = get_error_stats(user_id)
    if not error_stats:
        return []
    # Сортируем по количеству ошибок
    error_stats.sort(key=lambda x: x["count"], reverse=True)
    return error_stats[:3]


def generate_report(user_id):
    """Генерирует полный отчёт о прогрессе."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        return None

    c.execute("SELECT COUNT(*) FROM errors WHERE user_id = ?", (user_id,))
    total_errors = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM words WHERE user_id = ?", (user_id,))
    total_words = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM lessons WHERE user_id = ? AND completed = 1", (user_id,))
    completed_lessons = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM achievements WHERE user_id = ?", (user_id,))
    achievements = c.fetchone()[0]
    conn.close()

    return {
        "user_id": user_id,
        "level": user["level"],
        "xp": user["xp"] or 0,
        "streak": user["streak"] or 0,
        "rank": user["rank"],
        "total_errors": total_errors,
        "total_words": total_words,
        "completed_lessons": completed_lessons,
        "achievements": achievements,
        "skill_progress": get_skill_progress(user_id),
        "weak_areas": get_weak_areas(user_id),
        "recent_errors": get_recent_errors(user_id, 5),
        "activity": get_activity_by_day(user_id, 14),
    }
