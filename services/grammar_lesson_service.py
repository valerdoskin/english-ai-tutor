"""
grammar_lesson_service.py — сервис уроков грамматики.

Отвечает за:
- Шаблон урока грамматики (объяснение → примеры → упражнения → recall)
- Генерацию упражнений через LLM
- Проверку ответов
- Fallback-уроки (если LLM недоступен)
- Задания на recall (повторение через интервалы)
"""
import asyncio
import json
import logging
import re

from services.llm_service import call_llm
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)

# Грамматические темы по уровням (fallback)
GRAMMAR_TOPICS = {
    "A1": [
        {"topic": "Present Simple", "explanation": "We use Present Simple for habits and routines. Form: I/you/we/they + verb, he/she/it + verb+s.", "examples": ["I work every day.", "She works in a hospital.", "They live in London."]},
        {"topic": "Present Continuous", "explanation": "We use Present Continuous for actions happening now. Form: am/is/are + verb+ing.", "examples": ["I am reading now.", "She is cooking dinner.", "They are playing football."]},
        {"topic": "There is / There are", "explanation": "We use 'there is' for singular and 'there are' for plural.", "examples": ["There is a book on the table.", "There are three chairs in the room."]},
        {"topic": "Can / Can't", "explanation": "We use 'can' for ability and permission. Form: can + verb.", "examples": ["I can swim.", "She can't drive.", "Can you help me?"]},
        {"topic": "Possessive 's", "explanation": "We use 's to show possession.", "examples": ["John's car is red.", "My sister's name is Anna."]},
    ],
    "A2": [
        {"topic": "Past Simple", "explanation": "We use Past Simple for finished actions in the past. Regular verbs add -ed.", "examples": ["I visited my grandmother yesterday.", "She worked in a bank.", "They watched a movie."]},
        {"topic": "Past Continuous", "explanation": "We use Past Continuous for actions in progress in the past. Form: was/were + verb+ing.", "examples": ["I was reading when you called.", "They were playing at 5 PM."]},
        {"topic": "Present Perfect", "explanation": "We use Present Perfect for past actions with present relevance. Form: have/has + past participle.", "examples": ["I have visited Paris.", "She has finished her homework."]},
        {"topic": "Comparatives & Superlatives", "explanation": "We use comparatives to compare two things and superlatives for three or more.", "examples": ["This book is more interesting than that one.", "She is the tallest in the class."]},
        {"topic": "Going to (future)", "explanation": "We use 'going to' for plans and intentions.", "examples": ["I am going to travel next month.", "They are going to buy a house."]},
    ],
    "B1": [
        {"topic": "Present Perfect vs Past Simple", "explanation": "Present Perfect connects past to present; Past Simple is for finished time.", "examples": ["I have lived here for 5 years.", "I lived in Paris in 2019."]},
        {"topic": "First Conditional", "explanation": "We use First Conditional for real future possibilities. Form: if + present, will + verb.", "examples": ["If it rains, we will stay home.", "If you study, you will pass."]},
        {"topic": "Second Conditional", "explanation": "We use Second Conditional for unreal/hypothetical situations. Form: if + past, would + verb.", "examples": ["If I had more time, I would travel.", "If she won the lottery, she would buy a house."]},
        {"topic": "Passive Voice (present/past)", "explanation": "We use passive when the action is more important than the doer. Form: be + past participle.", "examples": ["The letter is written by John.", "The house was built in 1990."]},
        {"topic": "Reported Speech", "explanation": "We use reported speech to report what someone said.", "examples": ["She said that she was tired.", "He told me that he would come."]},
    ],
    "B2": [
        {"topic": "Third Conditional", "explanation": "We use Third Conditional for unreal past situations. Form: if + past perfect, would have + past participle.", "examples": ["If I had known, I would have come.", "If she had studied, she would have passed."]},
        {"topic": "Mixed Conditionals", "explanation": "Mixed conditionals combine different time references.", "examples": ["If I had studied harder, I would be a doctor now.", "If she were here, she would have helped."]},
        {"topic": "Modal Verbs of Deduction", "explanation": "We use must/might/can't for deduction.", "examples": ["He must be tired.", "She might be at home.", "They can't be serious."]},
        {"topic": "Causative Have", "explanation": "We use 'have something done' when someone does something for us.", "examples": ["I had my car repaired.", "She had her hair cut."]},
        {"topic": "Inversion", "explanation": "We use inversion for emphasis in formal English.", "examples": ["Never have I seen such a beautiful view.", "Not only did she pass, but she excelled."]},
    ],
    "C1": [
        {"topic": "Cleft Sentences", "explanation": "Cleft sentences emphasize a particular part of a sentence.", "examples": ["It was John who broke the window.", "What I need is a holiday."]},
        {"topic": "Advanced Conditionals", "explanation": "Advanced conditional structures with inversion.", "examples": ["Had I known, I would have acted differently.", "Were she to ask, I would say yes."]},
        {"topic": "Subjunctive Mood", "explanation": "We use subjunctive for formal suggestions and demands.", "examples": ["I suggest that he be present.", "It is essential that she arrive on time."]},
        {"topic": "Ellipsis & Substitution", "explanation": "We omit words to avoid repetition.", "examples": ["I like coffee, and she does too.", "He said he would help, and he did."]},
        {"topic": "Fronting", "explanation": "We move elements to the front for emphasis.", "examples": ["Rarely do we see such talent.", "Under no circumstances should you leave."]},
    ],
    "C2": [
        {"topic": "Advanced Inversion", "explanation": "Complex inversion structures in formal writing.", "examples": ["So compelling was the argument that everyone agreed.", "Little did she know what awaited her."]},
        {"topic": "Nominalization", "explanation": "We use nouns instead of verbs for formal style.", "examples": ["The implementation of the plan was successful.", "Her arrival was unexpected."]},
        {"topic": "Hedging Language", "explanation": "We use hedging to soften claims in academic writing.", "examples": ["It could be argued that...", "The evidence suggests that..."]},
        {"topic": "Complex Prepositions", "explanation": "Multi-word prepositions in formal English.", "examples": ["In light of recent events...", "With regard to your request..."]},
        {"topic": "Register Shifting", "explanation": "Adapting language to different registers.", "examples": ["Formal: I would appreciate your assistance.", "Informal: Can you help me out?"]},
    ],
}


def get_grammar_topics(level):
    """Возвращает грамматические темы для уровня."""
    return GRAMMAR_TOPICS.get(level, GRAMMAR_TOPICS.get("A1", []))


def generate_grammar_lesson(level, topic=None):
    """Генерирует урок грамматики через LLM (или fallback)."""
    if not topic:
        topics = get_grammar_topics(level)
        topic = topics[0]["topic"] if topics else "Present Simple"

    prompt = f"""Create a grammar lesson for a {level} level English student on the topic: "{topic}".

Return ONLY valid JSON in this exact format:
{{
  "topic": "{topic}",
  "explanation": "Clear, simple explanation of the grammar rule appropriate for {level} level",
  "examples": ["example1", "example2", "example3"],
  "exercises": [
    {{
      "type": "fill_blank",
      "instruction": "Complete the sentence with the correct form",
      "sentence": "She ___ (work) in a hospital.",
      "answer": "works",
      "hint": "Remember to add -s for he/she/it"
    }},
    {{
      "type": "multiple_choice",
      "instruction": "Choose the correct option",
      "sentence": "I ___ to school every day.",
      "options": ["go", "goes", "going", "gone"],
      "answer": 0,
      "hint": "I/you/we/they use the base form"
    }},
    {{
      "type": "reorder",
      "instruction": "Put the words in the correct order",
      "words": ["She", "works", "in", "a", "hospital"],
      "answer": "She works in a hospital.",
      "hint": "Subject + verb + place"
    }}
  ],
  "recall": {{
    "question": "A question to test recall of the rule",
    "answer": "The correct answer"
  }}
}}
Create 3-4 exercises of different types (fill_blank, multiple_choice, reorder, error_correction).
The content should be appropriate for a {level} CEFR level student.
Return ONLY the JSON, no other text."""

    result = asyncio.run(call_llm([{"role": "user", "content": prompt}]))
    if result and not result.startswith("❌"):
        data = extract_json(result)
        if data and "explanation" in data:
            return data
    # Fallback
    return _fallback_grammar_lesson(level, topic)


def _fallback_grammar_lesson(level, topic):
    """Создаёт урок грамматики без LLM."""
    topics = get_grammar_topics(level)
    topic_data = None
    for t in topics:
        if t["topic"].lower() == topic.lower():
            topic_data = t
            break
    if not topic_data:
        topic_data = topics[0] if topics else {"topic": topic, "explanation": f"Grammar topic: {topic}", "examples": ["Example sentence."]}

    return {
        "topic": topic_data["topic"],
        "explanation": topic_data["explanation"],
        "examples": topic_data["examples"],
        "exercises": [
            {
                "type": "fill_blank",
                "instruction": "Complete the sentence with the correct form",
                "sentence": f"___ (example) about {topic_data['topic']}.",
                "answer": "example",
                "hint": "Use the correct form of the verb.",
            },
            {
                "type": "multiple_choice",
                "instruction": "Choose the correct option",
                "sentence": f"This is a sentence about {topic_data['topic']}.",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer": 0,
                "hint": "Choose the best option.",
            },
            {
                "type": "reorder",
                "instruction": "Put the words in the correct order",
                "words": ["This", "is", "a", "sentence"],
                "answer": "This is a sentence.",
                "hint": "Subject + verb + object.",
            },
        ],
        "recall": {
            "question": f"What is the rule for {topic_data['topic']}?",
            "answer": topic_data["explanation"],
        },
    }


def check_answer(exercise, user_answer):
    """Проверяет ответ пользователя на упражнение."""
    ex_type = exercise.get("type")
    correct = exercise.get("answer")

    if ex_type == "multiple_choice":
        # answer — индекс правильного варианта
        try:
            user_idx = int(user_answer)
            return user_idx == correct
        except (ValueError, TypeError):
            # Пользователь мог ввести текст варианта
            options = exercise.get("options", [])
            if isinstance(correct, int) and 0 <= correct < len(options):
                return str(user_answer).strip().lower() == str(options[correct]).strip().lower()
            return False

    elif ex_type == "fill_blank":
        # answer — правильное слово/фраза
        if isinstance(correct, str):
            return _normalize(user_answer) == _normalize(correct)
        return False

    elif ex_type == "reorder":
        # answer — правильный порядок слов
        if isinstance(correct, str):
            return _normalize(user_answer) == _normalize(correct)
        return False

    elif ex_type == "error_correction":
        # answer — исправленное предложение
        if isinstance(correct, str):
            return _normalize(user_answer) == _normalize(correct)
        return False

    return False


def _normalize(text):
    """Нормализует текст для сравнения."""
    if not text:
        return ""
    text = str(text).strip().lower()
    text = re.sub(r"[.!?]+$", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def generate_recall_question(level, topic):
    """Генерирует вопрос для recall (повторение через интервалы)."""
    topics = get_grammar_topics(level)
    topic_data = None
    for t in topics:
        if t["topic"].lower() == topic.lower():
            topic_data = t
            break
    if not topic_data:
        topic_data = topics[0] if topics else {"topic": topic, "explanation": f"Grammar topic: {topic}"}
    return {
        "question": f"What is the rule for {topic_data['topic']}? Give an example.",
        "answer": topic_data["explanation"],
        "topic": topic_data["topic"],
    }
