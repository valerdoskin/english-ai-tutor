"""
curriculum_service.py — управление программой обучения (curriculum).

Отвечает за:
- Структуру программы: уровни → модули → уроки
- Генерацию модулей и уроков через LLM
- Принцип i+1 (подбор контента чуть сложнее текущего уровня)
- Task-Based Learning (реальные задачи)
"""
import asyncio
import json
import logging

from services.llm_service import call_llm
from utils.json_parser import extract_json
from database import (
    get_modules, get_module, create_module,
    get_lessons, get_lesson, create_lesson, complete_lesson,
)

logger = logging.getLogger(__name__)

# Порядок уровней CEFR
CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Стандартные модули для каждого уровня (fallback, если LLM недоступен)
DEFAULT_MODULES = {
    "A1": [
        {"title": "Greetings & Introductions", "description": "Learn to introduce yourself and greet others."},
        {"title": "Everyday Objects", "description": "Vocabulary for common objects and daily life."},
        {"title": "Numbers & Time", "description": "Numbers, dates, and telling time."},
        {"title": "Simple Present", "description": "Talk about habits and routines."},
    ],
    "A2": [
        {"title": "Daily Routines", "description": "Describe your daily activities."},
        {"title": "Food & Restaurants", "description": "Order food and talk about meals."},
        {"title": "Past Simple", "description": "Talk about past events."},
        {"title": "Travel & Directions", "description": "Ask for and give directions."},
    ],
    "B1": [
        {"title": "Present Perfect", "description": "Talk about experiences and recent events."},
        {"title": "Work & Career", "description": "Discuss jobs, interviews, and workplace."},
        {"title": "Health & Body", "description": "Talk about health, symptoms, and doctors."},
        {"title": "Future Forms", "description": "Express plans, predictions, and intentions."},
    ],
    "B2": [
        {"title": "Conditionals", "description": "Express hypothetical situations."},
        {"title": "Business English", "description": "Meetings, negotiations, and presentations."},
        {"title": "Passive Voice", "description": "Use passive constructions in writing and speech."},
        {"title": "Debates & Opinions", "description": "Express and defend opinions."},
    ],
    "C1": [
        {"title": "Advanced Grammar", "description": "Complex structures: inversion, cleft sentences."},
        {"title": "Academic Writing", "description": "Essays, reports, and formal writing."},
        {"title": "Idioms & Phrasal Verbs", "description": "Natural, idiomatic English."},
        {"title": "Persuasion & Rhetoric", "description": "Persuasive speaking and writing."},
    ],
    "C2": [
        {"title": "Nuance & Register", "description": "Fine distinctions in meaning and style."},
        {"title": "Professional Fluency", "description": "Near-native professional communication."},
        {"title": "Literary English", "description": "Understanding and using literary devices."},
        {"title": "Mastery Projects", "description": "Complex, real-world language projects."},
    ],
}


def get_next_level(current_level):
    """Возвращает следующий уровень CEFR."""
    idx = CEFR_ORDER.index(current_level) if current_level in CEFR_ORDER else 0
    if idx < len(CEFR_ORDER) - 1:
        return CEFR_ORDER[idx + 1]
    return None


def get_previous_level(current_level):
    """Возвращает предыдущий уровень CEFR."""
    idx = CEFR_ORDER.index(current_level) if current_level in CEFR_ORDER else 0
    if idx > 0:
        return CEFR_ORDER[idx - 1]
    return None


def ensure_modules_for_level(level):
    """Создаёт стандартные модули для уровня, если их ещё нет."""
    existing = get_modules(level)
    if existing:
        return existing
    defaults = DEFAULT_MODULES.get(level, [])
    created = []
    for i, mod in enumerate(defaults):
        module_id = create_module(level, mod["title"], mod["description"], i)
        created.append({"id": module_id, "level": level, **mod, "order_index": i})
    logger.info(f"Created {len(created)} modules for level {level}")
    return created


def get_curriculum(user_id, level):
    """Возвращает программу обучения для уровня с прогрессом пользователя."""
    modules = ensure_modules_for_level(level)
    lessons = get_lessons(user_id)
    lessons_by_module = {}
    for lesson in lessons:
        lessons_by_module.setdefault(lesson["module_id"], []).append(lesson)

    result = []
    for mod in modules:
        mod_lessons = lessons_by_module.get(mod["id"], [])
        completed = sum(1 for l in mod_lessons if l["completed"])
        result.append({
            "id": mod["id"],
            "level": mod["level"],
            "title": mod["title"],
            "description": mod["description"],
            "order_index": mod["order_index"],
            "lessons_count": len(mod_lessons),
            "completed_count": completed,
            "progress": round((completed / len(mod_lessons)) * 100) if mod_lessons else 0,
        })
    return result


def generate_module_lessons(user_id, module_id, level, topic):
    """Генерирует уроки для модуля через LLM."""
    prompt = f"""Create a set of English lessons for a {level} level student.
Module topic: "{topic}"

Create 5 lessons that progressively build skills. Each lesson should be slightly more
challenging than the previous (principle of i+1).

Return ONLY valid JSON in this exact format:
{{
  "lessons": [
    {{
      "title": "Lesson title",
      "type": "grammar|vocabulary|listening|speaking|reading|writing",
      "content": {{
        "introduction": "Short engaging intro",
        "explanation": "Clear explanation appropriate for {level}",
        "examples": ["example1", "example2"],
        "exercise": "Practice exercise instructions",
        "task": "Real-world task (TBLT) the student should complete"
      }}
    }}
  ]
}}
The content should be appropriate for a {level} CEFR level student.
Return ONLY the JSON, no other text."""

    result = asyncio.run(call_llm([{"role": "user", "content": prompt}]))
    if result and not result.startswith("❌"):
        data = extract_json(result)
        if data and "lessons" in data:
            created = []
            for lesson in data["lessons"]:
                lesson_id = create_lesson(
                    user_id, module_id,
                    lesson.get("type", "grammar"),
                    lesson.get("title", "Lesson"),
                    lesson.get("content"),
                )
                created.append({"id": lesson_id, **lesson})
            return created
    # Fallback
    return _fallback_lessons(user_id, module_id, level, topic)


def _fallback_lessons(user_id, module_id, level, topic):
    """Создаёт базовые уроки, если LLM недоступен."""
    types = ["grammar", "vocabulary", "listening", "speaking", "reading"]
    created = []
    for i, lesson_type in enumerate(types):
        content = {
            "introduction": f"Welcome to lesson {i+1} about {topic}!",
            "explanation": f"This lesson focuses on {lesson_type} skills for {level} level.",
            "examples": [f"Example sentence about {topic}."],
            "exercise": f"Practice {lesson_type} with the topic {topic}.",
            "task": f"Complete a real-world task related to {topic}.",
        }
        lesson_id = create_lesson(user_id, module_id, lesson_type, f"{topic} — {lesson_type.capitalize()}", content)
        created.append({"id": lesson_id, "title": f"{topic} — {lesson_type.capitalize()}", "type": lesson_type, "content": content})
    return created


def get_lesson_content(user_id, lesson_id):
    """Возвращает содержимое урока."""
    lesson = get_lesson(user_id, lesson_id)
    if not lesson:
        return None
    content = lesson["content"]
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            content = {"explanation": content}
    return {
        "id": lesson["id"],
        "title": lesson["title"],
        "type": lesson["lesson_type"],
        "completed": lesson["completed"],
        "score": lesson["score"],
        "content": content,
    }


def submit_lesson(user_id, lesson_id, score):
    """Отмечает урок завершённым и возвращает результат."""
    complete_lesson(user_id, lesson_id, score)
    lesson = get_lesson(user_id, lesson_id)
    return {
        "ok": True,
        "lesson_id": lesson_id,
        "score": score,
        "completed": True,
        "module_id": lesson["module_id"] if lesson else None,
    }
