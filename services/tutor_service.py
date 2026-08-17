"""
tutor_service.py — сервисы для продвинутых функций репетитора:
- Тест уровня (CEFR)
- Генерация уроков
- Генерация подкастов
- Аудио диалог
"""
import asyncio
import json
import logging
import re

from services.llm_service import call_llm

logger = logging.getLogger(__name__)

# Описание уровней CEFR
CEFR_LEVELS = {
    "A1": {
        "name": "Beginner",
        "description": "You can understand and use familiar everyday expressions and very basic phrases. You can introduce yourself and ask simple questions.",
    },
    "A2": {
        "name": "Elementary",
        "description": "You can understand sentences and frequently used expressions related to areas of most immediate relevance. You can describe in simple terms aspects of your background.",
    },
    "B1": {
        "name": "Intermediate",
        "description": "You can understand the main points of clear standard input on familiar matters. You can deal with most situations likely to arise while travelling.",
    },
    "B2": {
        "name": "Upper-Intermediate",
        "description": "You can understand the main ideas of complex text on both concrete and abstract topics. You can interact with a degree of fluency and spontaneity.",
    },
    "C1": {
        "name": "Advanced",
        "description": "You can understand a wide range of demanding, longer texts and recognise implicit meaning. You can express ideas fluently and spontaneously.",
    },
    "C2": {
        "name": "Proficiency",
        "description": "You can understand with ease virtually everything heard or read. You can summarise information from different spoken and written sources.",
    },
}

# Статические вопросы для теста (fallback, если LLM недоступен)
STATIC_TEST_QUESTIONS = [
    {
        "question": "Choose the correct sentence:",
        "options": ["She go to school every day.", "She goes to school every day.", "She going to school every day.", "She gone to school every day."],
        "answer": 1,
        "level": "A1",
    },
    {
        "question": "Complete: 'I ___ a book right now.'",
        "options": ["read", "am reading", "reads", "reading"],
        "answer": 1,
        "level": "A1",
    },
    {
        "question": "Choose the correct form: 'If it rains, we ___ at home.'",
        "options": ["stay", "will stay", "stayed", "would stay"],
        "answer": 1,
        "level": "A2",
    },
    {
        "question": "Complete: 'She has lived here ___ 2010.'",
        "options": ["for", "since", "from", "during"],
        "answer": 1,
        "level": "A2",
    },
    {
        "question": "Choose the correct sentence:",
        "options": ["He suggested me to go.", "He suggested that I go.", "He suggested me going.", "He suggested to go."],
        "answer": 1,
        "level": "B1",
    },
    {
        "question": "Complete: 'By the time we arrived, the movie ___ .'",
        "options": ["started", "had started", "has started", "was starting"],
        "answer": 1,
        "level": "B1",
    },
    {
        "question": "Choose the correct form: 'I wish I ___ more time.'",
        "options": ["have", "had", "would have", "will have"],
        "answer": 1,
        "level": "B2",
    },
    {
        "question": "Complete: 'The report ___ by the end of the week.'",
        "options": ["will be completed", "will complete", "will have completed", "completes"],
        "answer": 0,
        "level": "B2",
    },
    {
        "question": "Choose the correct sentence:",
        "options": ["Despite of the rain, we went out.", "Despite the rain, we went out.", "Despite the rain, we went out.", "Despite the rain, we went out."],
        "answer": 1,
        "level": "C1",
    },
    {
        "question": "Complete: 'Had I known about the meeting, I ___ attended.'",
        "options": ["would have", "will have", "would", "have"],
        "answer": 0,
        "level": "C1",
    },
    {
        "question": "Choose the correct sentence:",
        "options": ["The data suggests a clear trend.", "The data suggest a clear trend.", "The data suggesting a clear trend.", "The data are suggesting a clear trend."],
        "answer": 0,
        "level": "C2",
    },
    {
        "question": "Complete: 'Not only ___ the exam, but she also got the highest score.'",
        "options": ["she passed", "did she pass", "she did pass", "passed she"],
        "answer": 1,
        "level": "C2",
    },
]


def _extract_json(text):
    """Извлекает JSON из ответа LLM."""
    if not text:
        return None
    text = text.strip()
    # Убираем markdown-обёртки
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Пробуем найти JSON в тексте
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def generate_test_questions(user_id, num_questions=12):
    """Генерирует вопросы для теста уровня."""
    prompt = f"""Generate {num_questions} English level test questions for a CEFR placement test.
The questions should range from A1 (easy) to C2 (hard), covering grammar and vocabulary.
Return ONLY valid JSON in this exact format:
{{
  "questions": [
    {{
      "question": "question text",
      "options": ["option1", "option2", "option3", "option4"],
      "answer": 0,
      "level": "A1"
    }}
  ]
}}
The "answer" field is the index (0-3) of the correct option.
Make sure exactly one option is correct for each question.
Return ONLY the JSON, no other text."""

    result = asyncio.run(call_llm([{"role": "user", "content": prompt}]))
    if result and not result.startswith("❌"):
        data = _extract_json(result)
        if data and "questions" in data and len(data["questions"]) >= 6:
            return data["questions"]
    # Fallback на статические вопросы
    logger.warning("LLM недоступен, используем статические вопросы")
    return STATIC_TEST_QUESTIONS


def evaluate_test(questions):
    """Оценивает тест и определяет уровень CEFR."""
    total = len(questions)
    correct = 0
    level_scores = {}

    for q in questions:
        if q.get("selected") == q.get("answer"):
            correct += 1
            lvl = q.get("level", "A1")
            level_scores[lvl] = level_scores.get(lvl, 0) + 1

    score_pct = round((correct / total) * 100) if total else 0

    # Определяем уровень по проценту правильных ответов
    if score_pct >= 90:
        level = "C2"
    elif score_pct >= 80:
        level = "C1"
    elif score_pct >= 65:
        level = "B2"
    elif score_pct >= 50:
        level = "B1"
    elif score_pct >= 35:
        level = "A2"
    else:
        level = "A1"

    return {
        "level": level,
        "score": score_pct,
        "correct": correct,
        "total": total,
        "description": CEFR_LEVELS[level]["description"],
        "level_name": CEFR_LEVELS[level]["name"],
    }


def generate_lesson(user_id, level, topic):
    """Генерирует урок по теме и уровню."""
    prompt = f"""Create an English lesson for a {level} level student on the topic: "{topic}".

Return ONLY valid JSON in this exact format:
{{
  "title": "Lesson title",
  "introduction": "A short engaging introduction (2-3 sentences)",
  "vocabulary": ["word1", "word2", "word3", "word4", "word5"],
  "explanation": "A clear grammar/vocabulary explanation appropriate for {level} level",
  "exercise": "A practice exercise with instructions"
}}
The content should be appropriate for a {level} CEFR level student.
Return ONLY the JSON, no other text."""

    result = asyncio.run(call_llm([{"role": "user", "content": prompt}]))
    if result and not result.startswith("❌"):
        data = _extract_json(result)
        if data and "title" in data:
            return data
    # Fallback
    return {
        "title": f"Lesson: {topic}",
        "introduction": f"Welcome to your lesson about {topic}! Let's explore this interesting topic together.",
        "vocabulary": ["topic", "learn", "practice", "improve", "speak"],
        "explanation": f"This lesson is designed for {level} level students. We'll focus on vocabulary and grammar related to {topic}.",
        "exercise": f"Write 3 sentences about {topic} using the new vocabulary words.",
    }


def generate_podcast_script(user_id, level, topic):
    """Генерирует сценарий подкаста."""
    prompt = f"""Create a short English podcast script (about 150-200 words) for a {level} level student on the topic: "{topic}".

The podcast should be engaging and educational, with natural spoken English appropriate for {level} level.

Return ONLY valid JSON in this exact format:
{{
  "title": "Podcast title",
  "summary": "One sentence summary",
  "transcript": "The full podcast transcript text"
}}
Return ONLY the JSON, no other text."""

    result = asyncio.run(call_llm([{"role": "user", "content": prompt}]))
    if result and not result.startswith("❌"):
        data = _extract_json(result)
        if data and "transcript" in data:
            return data
    # Fallback
    return {
        "title": f"Podcast: {topic}",
        "summary": f"An interesting podcast about {topic}.",
        "transcript": f"Welcome to our podcast about {topic}. Today we'll explore this fascinating topic. {topic} is important because it affects our daily lives. Let's learn more about it together. Thank you for listening!",
    }


def generate_dialogue_reply(user_id, level, user_text):
    """Генерирует ответ на реплику пользователя в диалоге."""
    prompt = f"""You are an English tutor for a {level} level student.
The student said: "{user_text}"

Correct any errors in their English and reply naturally to continue the conversation.

Return ONLY valid JSON in this exact format:
{{
  "corrections": ["correction1", "correction2"],
  "reply": "Your natural reply to continue the conversation"
}}
If there are no errors, corrections should be an empty array.
Keep the reply appropriate for {level} level and engaging.
Return ONLY the JSON, no other text."""

    result = asyncio.run(call_llm([{"role": "user", "content": prompt}]))
    if result and not result.startswith("❌"):
        data = _extract_json(result)
        if data and "reply" in data:
            return data
    # Fallback
    return {
        "corrections": [],
        "reply": f"That's interesting! Tell me more about {user_text}.",
    }
