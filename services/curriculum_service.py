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
# Каждый модуль содержит TBLT-задачу (реальный сценарий)
DEFAULT_MODULES = {
    "A1": [
        {"title": "Introductions", "description": "Introduce yourself, greet others, and ask basic questions.", "task": "Introduce yourself to a new classmate and ask them 3 questions."},
        {"title": "Daily Routine", "description": "Talk about your daily activities and habits.", "task": "Describe your typical day to a friend."},
        {"title": "Food & Drink", "description": "Order food, talk about meals, and express preferences.", "task": "Order a meal at a restaurant and ask about the menu."},
        {"title": "Family & Friends", "description": "Describe your family and friends.", "task": "Show a photo of your family and describe each person."},
        {"title": "Shopping", "description": "Ask about prices, sizes, and make purchases.", "task": "Buy a shirt at a clothing store, asking about size and price."},
        {"title": "Travel", "description": "Ask for directions and talk about travel.", "task": "Ask a stranger for directions to the train station."},
    ],
    "A2": [
        {"title": "Hobbies", "description": "Talk about your hobbies and free time.", "task": "Invite a friend to do a hobby together and make plans."},
        {"title": "Health", "description": "Describe symptoms and talk to a doctor.", "task": "Describe your symptoms to a doctor and get advice."},
        {"title": "Work & Jobs", "description": "Talk about jobs, responsibilities, and workplaces.", "task": "Describe your job to someone and answer questions about it."},
        {"title": "City Life", "description": "Describe your city and give directions.", "task": "Give a tourist directions to three places in your city."},
        {"title": "Weather & Seasons", "description": "Talk about weather and seasons.", "task": "Describe the weather forecast for the week to a friend."},
        {"title": "Past Experiences", "description": "Talk about past events and experiences.", "task": "Tell a friend about your last vacation."},
    ],
    "B1": [
        {"title": "Education", "description": "Discuss education, courses, and learning.", "task": "Recommend a course to a friend and explain why."},
        {"title": "Technology", "description": "Discuss technology and its impact.", "task": "Explain how to use a new app to someone."},
        {"title": "Environment", "description": "Discuss environmental issues and solutions.", "task": "Propose a plan to reduce waste in your community."},
        {"title": "Culture & Traditions", "description": "Discuss cultural differences and traditions.", "task": "Describe a traditional celebration from your country."},
        {"title": "Future Plans", "description": "Express plans, predictions, and intentions.", "task": "Describe your plans for the next 5 years."},
        {"title": "Opinions & Arguments", "description": "Express and defend opinions.", "task": "Argue for or against a topic in a debate."},
    ],
    "B2": [
        {"title": "Conditionals", "description": "Express hypothetical situations.", "task": "Discuss what you would do if you won the lottery."},
        {"title": "Business English", "description": "Meetings, negotiations, and presentations.", "task": "Present a product idea to a group of investors."},
        {"title": "Passive Voice", "description": "Use passive constructions in writing and speech.", "task": "Write a news report about a recent event."},
        {"title": "Debates & Opinions", "description": "Express and defend opinions.", "task": "Participate in a structured debate on a controversial topic."},
        {"title": "Society & Politics", "description": "Discuss social and political issues.", "task": "Explain a current social issue and propose solutions."},
        {"title": "Science & Innovation", "description": "Discuss scientific discoveries and innovations.", "task": "Explain a recent scientific breakthrough to a non-expert."},
    ],
    "C1": [
        {"title": "Advanced Grammar", "description": "Complex structures: inversion, cleft sentences.", "task": "Write a formal letter using advanced structures."},
        {"title": "Academic Writing", "description": "Essays, reports, and formal writing.", "task": "Write a 300-word academic essay on a given topic."},
        {"title": "Idioms & Phrasal Verbs", "description": "Natural, idiomatic English.", "task": "Tell a story using at least 5 idioms."},
        {"title": "Persuasion & Rhetoric", "description": "Persuasive speaking and writing.", "task": "Deliver a persuasive speech on a topic of your choice."},
        {"title": "Professional Communication", "description": "Effective communication in professional settings.", "task": "Conduct a job interview simulation."},
        {"title": "Critical Thinking", "description": "Analyze arguments and evaluate evidence.", "task": "Analyze a news article and identify bias."},
    ],
    "C2": [
        {"title": "Nuance & Register", "description": "Fine distinctions in meaning and style.", "task": "Rewrite a text in three different registers."},
        {"title": "Professional Fluency", "description": "Near-native professional communication.", "task": "Lead a complex business negotiation."},
        {"title": "Literary English", "description": "Understanding and using literary devices.", "task": "Write a short story using literary techniques."},
        {"title": "Mastery Projects", "description": "Complex, real-world language projects.", "task": "Produce a professional presentation on a complex topic."},
        {"title": "Stylistic Variation", "description": "Adapt language to different styles and contexts.", "task": "Write the same message in formal, informal, and academic styles."},
        {"title": "Expert Discourse", "description": "Engage in expert-level discussions.", "task": "Participate in a panel discussion on a specialized topic."},
    ],
}


# CLIL-модули (Content and Language Integrated Learning)
# Изучение предметов на английском языке
CLIL_MODULES = {
    "B2": [
        {"title": "Science & Innovation", "description": "Learn about scientific discoveries and innovations in English.", "task": "Explain a recent scientific breakthrough to a non-expert.", "clil": "science"},
        {"title": "Business & Finance", "description": "Study business concepts and financial literacy in English.", "task": "Analyze a company's annual report and present your findings.", "clil": "business"},
        {"title": "History & Culture", "description": "Explore historical events and cultural movements in English.", "task": "Give a presentation about a historical event that shaped your country.", "clil": "history"},
        {"title": "Technology & Society", "description": "Discuss how technology shapes modern society in English.", "task": "Debate the ethical implications of artificial intelligence.", "clil": "technology"},
    ],
    "C1": [
        {"title": "Academic Research", "description": "Read and analyze academic papers in English.", "task": "Summarize a research paper and present its key findings.", "clil": "academic"},
        {"title": "Global Economics", "description": "Study global economic systems and trade in English.", "task": "Analyze the impact of globalization on developing economies.", "clil": "economics"},
        {"title": "Environmental Science", "description": "Explore environmental challenges and solutions in English.", "task": "Propose a sustainable solution to a local environmental issue.", "clil": "environment"},
        {"title": "Media & Journalism", "description": "Analyze media content and journalism practices in English.", "task": "Write a balanced news article about a controversial topic.", "clil": "media"},
    ],
    "C2": [
        {"title": "Advanced Research Methods", "description": "Conduct and present advanced research in English.", "task": "Design a research study and present your methodology.", "clil": "research"},
        {"title": "International Relations", "description": "Discuss geopolitics and diplomacy in English.", "task": "Simulate a diplomatic negotiation between two countries.", "clil": "diplomacy"},
        {"title": "Philosophy & Ethics", "description": "Engage with philosophical concepts and ethical debates in English.", "task": "Lead a philosophical discussion on a complex ethical dilemma.", "clil": "philosophy"},
        {"title": "Advanced Technology", "description": "Explore cutting-edge technology topics in English.", "task": "Present a technical concept to a non-specialist audience.", "clil": "technology"},
    ],
}

# IELTS/TOEFL задания для уровней B2-C2
IELTS_TOEFL_TASKS = {
    "B2": [
        {"type": "essay", "title": "Opinion Essay", "description": "Write a 250-word essay expressing your opinion on a given topic.", "prompt": "Some people believe that technology makes us less social. Do you agree or disagree?"},
        {"type": "speaking", "title": "Part 2 Monologue", "description": "Speak for 1-2 minutes about a given topic.", "prompt": "Describe a place you would like to visit in the future. Explain why you want to go there."},
        {"type": "reading", "title": "Reading Comprehension", "description": "Read a passage and answer comprehension questions.", "prompt": "Read the passage about climate change and answer 5 questions."},
    ],
    "C1": [
        {"type": "essay", "title": "Argumentative Essay", "description": "Write a 300-word argumentative essay with a clear thesis.", "prompt": "To what extent should governments regulate the use of artificial intelligence?"},
        {"type": "speaking", "title": "Part 3 Discussion", "description": "Discuss abstract topics and express complex opinions.", "prompt": "Discuss the role of education in reducing social inequality."},
        {"type": "writing", "title": "Report Writing", "description": "Write a formal report based on given data.", "prompt": "Write a report analyzing the provided chart about internet usage trends."},
    ],
    "C2": [
        {"type": "essay", "title": "Academic Essay", "description": "Write a 400-word academic essay with citations.", "prompt": "Critically evaluate the statement: 'Globalization has done more harm than good.'"},
        {"type": "speaking", "title": "Part 4 Extended Discussion", "description": "Engage in an extended discussion on abstract topics.", "prompt": "Discuss the philosophical implications of consciousness in artificial intelligence."},
        {"type": "writing", "title": "Academic Report", "description": "Write a comprehensive academic report.", "prompt": "Write a research report on the effects of remote work on productivity."},
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
        module_id = create_module(level, mod["title"], mod["description"], i, mod.get("task"))
        created.append({"id": module_id, "level": level, **mod, "order_index": i})
    logger.info(f"Created {len(created)} modules for level {level}")
    return created


def ensure_clil_modules_for_level(level):
    """Создаёт CLIL-модули для уровня, если их ещё нет."""
    existing = get_modules(level)
    # Проверяем, есть ли уже CLIL-модули (по полю clil в описании)
    has_clil = any("clil" in m or "CLIL" in m.get("description", "") for m in existing)
    if has_clil:
        return existing
    clil_defaults = CLIL_MODULES.get(level, [])
    if not clil_defaults:
        return existing
    # Добавляем CLIL-модули после стандартных
    start_index = len(existing)
    created = []
    for i, mod in enumerate(clil_defaults):
        module_id = create_module(level, mod["title"], mod["description"], start_index + i, mod.get("task"))
        created.append({"id": module_id, "level": level, **mod, "order_index": start_index + i})
    logger.info(f"Created {len(created)} CLIL modules for level {level}")
    return existing + created


def get_ielts_toefl_tasks(level):
    """Возвращает задания в формате IELTS/TOEFL для уровня."""
    return IELTS_TOEFL_TASKS.get(level, [])


def get_curriculum(user_id, level):
    """Возвращает программу обучения для уровня с прогрессом пользователя."""
    modules = ensure_modules_for_level(level)
    # Добавляем CLIL-модули для уровней B2-C2
    if level in CLIL_MODULES:
        modules = ensure_clil_modules_for_level(level)
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
            "task": mod.get("task"),
            "order_index": mod["order_index"],
            "is_clil": bool(mod.get("clil")),
            "lessons_count": len(mod_lessons),
            "completed_count": completed,
            "progress": round((completed / len(mod_lessons)) * 100) if mod_lessons else 0,
        })
    return result


def get_module_detail(user_id, module_id):
    """Возвращает детальную информацию о модуле с уроками."""
    module = get_module(module_id)
    if not module:
        return None
    lessons = get_lessons(user_id, module_id)
    # Если уроков нет, генерируем базовые
    if not lessons:
        lessons = _fallback_lessons(user_id, module_id, module["level"], module["title"])
    lesson_list = []
    for lesson in lessons:
        lesson_list.append({
            "id": lesson["id"],
            "title": lesson["title"],
            "type": lesson["lesson_type"],
            "completed": lesson["completed"],
            "score": lesson["score"],
        })
    return {
        "id": module["id"],
        "level": module["level"],
        "title": module["title"],
        "description": module["description"],
        "task": module.get("task"),
        "order_index": module["order_index"],
        "lessons": lesson_list,
    }


def get_next_lesson(user_id, level):
    """Возвращает следующий незавершённый урок (принцип i+1)."""
    modules = ensure_modules_for_level(level)
    for mod in modules:
        lessons = get_lessons(user_id, mod["id"])
        if not lessons:
            lessons = _fallback_lessons(user_id, mod["id"], level, mod["title"])
        for lesson in lessons:
            if not lesson["completed"]:
                return {
                    "module_id": mod["id"],
                    "module_title": mod["title"],
                    "lesson_id": lesson["id"],
                    "title": lesson["title"],
                    "type": lesson["lesson_type"],
                }
    return None


def get_daily_practice(user_id, level):
    """Возвращает набор быстрых упражнений для Daily Practice (5-10 минут)."""
    modules = ensure_modules_for_level(level)
    if not modules:
        return None
    # Берём первый незавершённый модуль или первый модуль
    target_module = None
    for mod in modules:
        lessons = get_lessons(user_id, mod["id"])
        if not lessons:
            lessons = _fallback_lessons(user_id, mod["id"], level, mod["title"])
        if any(not l["completed"] for l in lessons):
            target_module = mod
            break
    if not target_module:
        target_module = modules[0]

    lessons = get_lessons(user_id, target_module["id"])
    if not lessons:
        lessons = _fallback_lessons(user_id, target_module["id"], level, target_module["title"])

    # Выбираем 3-4 упражнения из разных типов уроков
    practice = []
    seen_types = set()
    for lesson in lessons:
        if lesson["lesson_type"] not in seen_types and len(practice) < 4:
            seen_types.add(lesson["lesson_type"])
            practice.append({
                "lesson_id": lesson["id"],
                "title": lesson["title"],
                "type": lesson["lesson_type"],
                "content": _parse_content(lesson["content"]),
            })
    return {
        "module_id": target_module["id"],
        "module_title": target_module["title"],
        "level": level,
        "practice": practice,
    }


def _parse_content(content):
    """Парсит содержимое урока."""
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"explanation": content}
    return content or {}


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
        created.append({"id": lesson_id, "title": f"{topic} — {lesson_type.capitalize()}", "lesson_type": lesson_type, "content": content, "completed": False, "score": None})
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
