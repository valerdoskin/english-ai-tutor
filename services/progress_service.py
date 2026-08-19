"""
progress_service.py — управление прогрессом пользователя.

Отвечает за:
- Начисление XP и определение ранга
- Ежедневную серию (streak)
- Ежедневные цели (daily goals)
- Общую статистику прогресса
"""
import logging
from datetime import date, datetime

from config import XP_LESSON, XP_TEST_QUESTION, XP_WORD, XP_VOICE, XP_DAILY, XP_TASK
from database import (
    get_connection, add_xp, update_streak, log_activity,
    get_daily_goal, set_daily_goal, update_daily_goal_progress,
    get_achievements, unlock_achievement,
)

logger = logging.getLogger(__name__)

# Награды за действия (XP) — из конфигурации
XP_REWARDS = {
    "lesson_completed": XP_LESSON,
    "test_question_correct": XP_TEST_QUESTION,
    "word_learned": XP_WORD,
    "word_reviewed": 2,
    "voice_message": XP_VOICE,
    "daily_practice": XP_DAILY,
    "task_completed": XP_TASK,
    "error_corrected": 3,
}

# Ранги и их пороги
RANKS = [
    {"name": "Bronze", "min_xp": 0, "icon": "🥉"},
    {"name": "Silver", "min_xp": 400, "icon": "🥈"},
    {"name": "Gold", "min_xp": 1000, "icon": "🥇"},
    {"name": "Platinum", "min_xp": 2000, "icon": "💎"},
    {"name": "Diamond", "min_xp": 5000, "icon": "👑"},
]


def get_rank_info(xp):
    """Возвращает информацию о ранге по XP."""
    current = RANKS[0]
    next_rank = None
    for rank in RANKS:
        if xp >= rank["min_xp"]:
            current = rank
        else:
            next_rank = rank
            break
    return {
        "current": current,
        "next": next_rank,
        "xp_to_next": (next_rank["min_xp"] - xp) if next_rank else 0,
    }


def award_xp(user_id, action, details=None):
    """Начисляет XP за действие и логирует его."""
    amount = XP_REWARDS.get(action, 0)
    if amount <= 0:
        return 0, None
    new_xp, rank = add_xp(user_id, amount)
    log_activity(user_id, action, amount, details)
    return new_xp, rank


def get_user_stats(user_id):
    """Возвращает полную статистику пользователя."""
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
    achievements_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM activity_log WHERE user_id = ?", (user_id,))
    total_actions = c.fetchone()[0]
    conn.close()

    xp = user["xp"] or 0
    rank_info = get_rank_info(xp)

    return {
        "user_id": user_id,
        "level": user["level"],
        "xp": xp,
        "streak": user["streak"] or 0,
        "rank": user["rank"],
        "rank_icon": rank_info["current"]["icon"],
        "xp_to_next_rank": rank_info["xp_to_next"],
        "total_errors": total_errors,
        "total_words": total_words,
        "completed_lessons": completed_lessons,
        "achievements_count": achievements_count,
        "total_actions": total_actions,
    }


def get_daily_summary(user_id):
    """Возвращает сводку за сегодня."""
    today = date.today().isoformat()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM activity_log WHERE user_id = ? AND date(timestamp) = ?", (user_id, today))
    today_actions = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(xp), 0) FROM activity_log WHERE user_id = ? AND date(timestamp) = ?", (user_id, today))
    today_xp = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM words WHERE user_id = ? AND date(next_review) <= ?", (user_id, today))
    due_words = c.fetchone()[0]
    conn.close()

    goal = get_daily_goal(user_id, today)

    return {
        "date": today,
        "today_actions": today_actions,
        "today_xp": today_xp,
        "due_words": due_words,
        "daily_goal": goal,
    }


def check_and_update_streak(user_id):
    """Обновляет streak и возвращает его."""
    return update_streak(user_id)


def ensure_daily_goal(user_id, goal_type="daily_practice", target=1):
    """Устанавливает ежедневную цель, если её ещё нет."""
    today = date.today().isoformat()
    goal = get_daily_goal(user_id, today)
    if not goal:
        set_daily_goal(user_id, goal_type, target, today)
        goal = get_daily_goal(user_id, today)
    return goal


def track_daily_progress(user_id, goal_type, amount=1):
    """Увеличивает прогресс ежедневной цели."""
    update_daily_goal_progress(user_id, goal_type, amount)
    goal = get_daily_goal(user_id)
    if goal and goal["completed"]:
        # Награда за выполнение ежедневной цели
        award_xp(user_id, "daily_practice")
        unlock_achievement(user_id, "daily_goal", "Daily Goal", "Complete your daily goal")
    return goal


def get_weekly_activity(user_id):
    """Возвращает активность за последние 7 дней."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT date(timestamp) as day, COUNT(*) as actions, COALESCE(SUM(xp), 0) as xp
        FROM activity_log
        WHERE user_id = ? AND timestamp >= datetime('now', '-7 days')
        GROUP BY date(timestamp)
        ORDER BY day
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
