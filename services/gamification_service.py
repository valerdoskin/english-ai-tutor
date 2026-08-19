"""
gamification_service.py — геймификация: бейджи, ранги, лидерборд.

Отвечает за:
- Проверку и разблокировку достижений (бейджей)
- Лидерборд
- Мотивационные сообщения
"""
import logging

from database import (
    get_connection, get_achievements, unlock_achievement,
    get_user_data,
)

logger = logging.getLogger(__name__)

# Определения всех достижений
ACHIEVEMENTS = {
    "first_lesson": {"title": "First Steps", "description": "Complete your first lesson", "icon": "🎯"},
    "first_word": {"title": "Word Explorer", "description": "Learn your first word", "icon": "📖"},
    "first_voice": {"title": "Speaker", "description": "Send your first voice message", "icon": "🎤"},
    "streak_3": {"title": "On Fire", "description": "3-day learning streak", "icon": "🔥"},
    "streak_7": {"title": "Week Warrior", "description": "7-day learning streak", "icon": "⚡"},
    "streak_30": {"title": "Unstoppable", "description": "30-day learning streak", "icon": "🏆"},
    "words_10": {"title": "Vocabulary Builder", "description": "Learn 10 words", "icon": "📚"},
    "words_50": {"title": "Word Master", "description": "Learn 50 words", "icon": "💪"},
    "words_100": {"title": "Lexicon Legend", "description": "Learn 100 words", "icon": "👑"},
    "lessons_5": {"title": "Dedicated", "description": "Complete 5 lessons", "icon": "📝"},
    "lessons_20": {"title": "Scholar", "description": "Complete 20 lessons", "icon": "🎓"},
    "lessons_50": {"title": "Academic", "description": "Complete 50 lessons", "icon": "🏅"},
    "daily_goal": {"title": "Goal Getter", "description": "Complete your daily goal", "icon": "✅"},
    "level_up": {"title": "Level Up", "description": "Advance to a new CEFR level", "icon": "🚀"},
    "perfect_lesson": {"title": "Perfect Score", "description": "Get 100% on a lesson", "icon": "💯"},
    "task_completed": {"title": "Task Master", "description": "Complete a real-world task", "icon": "🎯"},
}


def check_achievements(user_id):
    """Проверяет и разблокирует достижения. Возвращает список новых."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        return []

    c.execute("SELECT COUNT(*) FROM words WHERE user_id = ?", (user_id,))
    word_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM lessons WHERE user_id = ? AND completed = 1", (user_id,))
    lesson_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM errors WHERE user_id = ?", (user_id,))
    error_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM activity_log WHERE user_id = ? AND action = 'voice_message'", (user_id,))
    voice_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM activity_log WHERE user_id = ? AND action = 'task_completed'", (user_id,))
    task_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM lessons WHERE user_id = ? AND completed = 1 AND score = 100", (user_id,))
    perfect_count = c.fetchone()[0]
    conn.close()

    streak = user["streak"] or 0

    # Определяем, какие достижения должны быть разблокированы
    conditions = {
        "first_lesson": lesson_count >= 1,
        "first_word": word_count >= 1,
        "first_voice": voice_count >= 1,
        "streak_3": streak >= 3,
        "streak_7": streak >= 7,
        "streak_30": streak >= 30,
        "words_10": word_count >= 10,
        "words_50": word_count >= 50,
        "words_100": word_count >= 100,
        "lessons_5": lesson_count >= 5,
        "lessons_20": lesson_count >= 20,
        "lessons_50": lesson_count >= 50,
        "daily_goal": False,  # Проверяется отдельно
        "level_up": False,  # Проверяется отдельно
        "perfect_lesson": perfect_count >= 1,
        "task_completed": task_count >= 1,
    }

    new_achievements = []
    for key, met in conditions.items():
        if met and key in ACHIEVEMENTS:
            a = ACHIEVEMENTS[key]
            if unlock_achievement(user_id, key, a["title"], a["description"]):
                new_achievements.append({"key": key, **a})

    return new_achievements


def get_user_achievements(user_id):
    """Возвращает достижения пользователя с иконками."""
    achievements = get_achievements(user_id)
    result = []
    for a in achievements:
        meta = ACHIEVEMENTS.get(a["achievement_key"], {})
        result.append({
            "key": a["achievement_key"],
            "title": a["title"],
            "description": a["description"],
            "icon": meta.get("icon", "🏅"),
            "unlocked_at": a["unlocked_at"],
        })
    return result


def get_leaderboard(limit=10):
    """Возвращает топ пользователей по XP."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, xp, level, streak, rank FROM users ORDER BY xp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    leaders = []
    for i, r in enumerate(rows):
        leaders.append({
            "position": i + 1,
            "user_id": r["user_id"],
            "xp": r["xp"] or 0,
            "level": r["level"],
            "streak": r["streak"] or 0,
            "rank": r["rank"],
        })
    return leaders


def get_motivational_message(streak):
    """Возвращает мотивационное сообщение в зависимости от streak."""
    if streak == 0:
        return "Start your learning journey today! Every word counts. 💪"
    elif streak == 1:
        return "Great start! Come back tomorrow to keep your streak alive! 🔥"
    elif streak < 7:
        return f"You're on a {streak}-day streak! Keep it going! 🔥"
    elif streak < 30:
        return f"Amazing! {streak} days in a row! You're building a powerful habit! ⚡"
    else:
        return f"Incredible! {streak}-day streak! You're unstoppable! 🏆"
