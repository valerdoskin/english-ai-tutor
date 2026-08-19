"""
adaptive_test_service.py — адаптивный тест определения уровня CEFR.

Реализует адаптивный алгоритм: сложность вопросов подстраивается
под ответы пользователя (как в Duolingo English Test).
"""
import asyncio
import json
import logging

from services.llm_service import call_llm
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)

CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Статические вопросы для каждого уровня (fallback)
STATIC_QUESTIONS = {
    "A1": [
        {"question": "Choose the correct sentence:", "options": ["She go to school.", "She goes to school.", "She going to school.", "She gone to school."], "answer": 1},
        {"question": "Complete: 'I ___ a book right now.'", "options": ["read", "am reading", "reads", "reading"], "answer": 1},
        {"question": "What is the plural of 'child'?", "options": ["childs", "children", "childes", "childrens"], "answer": 1},
    ],
    "A2": [
        {"question": "Choose the correct form: 'If it rains, we ___ at home.'", "options": ["stay", "will stay", "stayed", "would stay"], "answer": 1},
        {"question": "Complete: 'She has lived here ___ 2010.'", "options": ["for", "since", "from", "during"], "answer": 1},
        {"question": "Choose the correct sentence:", "options": ["I am agree with you.", "I agree with you.", "I agreeing with you.", "I agreed with you."], "answer": 1},
    ],
    "B1": [
        {"question": "Choose the correct sentence:", "options": ["He suggested me to go.", "He suggested that I go.", "He suggested me going.", "He suggested to go."], "answer": 1},
        {"question": "Complete: 'By the time we arrived, the movie ___ .'", "options": ["started", "had started", "has started", "was starting"], "answer": 1},
        {"question": "Choose the correct form: 'I'm looking forward ___ you.'", "options": ["to see", "to seeing", "seeing", "see"], "answer": 1},
    ],
    "B2": [
        {"question": "Choose the correct form: 'I wish I ___ more time.'", "options": ["have", "had", "would have", "will have"], "answer": 1},
        {"question": "Complete: 'The report ___ by the end of the week.'", "options": ["will be completed", "will complete", "will have completed", "completes"], "answer": 0},
        {"question": "Choose the correct sentence:", "options": ["She is used to work late.", "She is used to working late.", "She used to working late.", "She uses to work late."], "answer": 1},
    ],
    "C1": [
        {"question": "Choose the correct sentence:", "options": ["Despite of the rain, we went out.", "Despite the rain, we went out.", "Despite the rain, we went out.", "Despite the rain, we went out."], "answer": 1},
        {"question": "Complete: 'Had I known about the meeting, I ___ attended.'", "options": ["would have", "will have", "would", "have"], "answer": 0},
        {"question": "Choose the correct form: 'The manager insisted that the report ___ immediately.'", "options": ["is submitted", "be submitted", "was submitted", "submitted"], "answer": 1},
    ],
    "C2": [
        {"question": "Choose the correct sentence:", "options": ["The data suggests a clear trend.", "The data suggest a clear trend.", "The data suggesting a clear trend.", "The data are suggesting a clear trend."], "answer": 0},
        {"question": "Complete: 'Not only ___ the exam, but she also got the highest score.'", "options": ["she passed", "did she pass", "she did pass", "passed she"], "answer": 1},
        {"question": "Choose the correct form: 'Were it not for your help, we ___ the project.'", "options": ["wouldn't finish", "wouldn't have finished", "didn't finish", "haven't finished"], "answer": 1},
    ],
}


class AdaptiveTest:
    """Адаптивный тест уровня CEFR."""

    def __init__(self, max_questions=12):
        self.max_questions = max_questions
        self.current_level_idx = 2  # Начинаем с B1
        self.questions = []
        self.answers = []
        self.level_scores = {lvl: {"correct": 0, "total": 0} for lvl in CEFR_ORDER}

    def get_next_question(self):
        """Возвращает следующий вопрос, подстраивая сложность."""
        if len(self.questions) >= self.max_questions:
            return None

        level = CEFR_ORDER[self.current_level_idx]
        question = self._get_question_for_level(level)
        if not question:
            # Если вопросы для уровня закончились, двигаемся
            self.current_level_idx = min(self.current_level_idx + 1, len(CEFR_ORDER) - 1)
            return self.get_next_question()

        question["level"] = level
        self.questions.append(question)
        return question

    def submit_answer(self, selected):
        """Принимает ответ и корректирует сложность."""
        if not self.questions:
            return None
        question = self.questions[-1]
        correct = (selected == question["answer"])
        level = question["level"]

        self.level_scores[level]["total"] += 1
        if correct:
            self.level_scores[level]["correct"] += 1

        # Адаптация сложности
        if correct:
            self.current_level_idx = min(self.current_level_idx + 1, len(CEFR_ORDER) - 1)
        else:
            self.current_level_idx = max(self.current_level_idx - 1, 0)

        return {"correct": correct, "level": level}

    def get_result(self):
        """Возвращает результат теста."""
        # Определяем уровень по последним ответам (взвешенно)
        # Считаем процент правильных по каждому уровню
        level_scores = {}
        for lvl in CEFR_ORDER:
            s = self.level_scores[lvl]
            if s["total"] > 0:
                level_scores[lvl] = round((s["correct"] / s["total"]) * 100)
            else:
                level_scores[lvl] = 0

        # Определяем уровень: самый высокий, где >= 60% правильных
        result_level = "A1"
        for lvl in CEFR_ORDER:
            if level_scores.get(lvl, 0) >= 60:
                result_level = lvl

        total_correct = sum(s["correct"] for s in self.level_scores.values())
        total = sum(s["total"] for s in self.level_scores.values())
        score_pct = round((total_correct / total) * 100) if total else 0

        return {
            "level": result_level,
            "score": score_pct,
            "correct": total_correct,
            "total": total,
            "level_scores": level_scores,
        }

    def _get_question_for_level(self, level):
        """Возвращает вопрос для уровня (из статических или LLM)."""
        questions = STATIC_QUESTIONS.get(level, [])
        # Убираем уже использованные вопросы
        used = {q["question"] for q in self.questions}
        available = [q for q in questions if q["question"] not in used]
        if available:
            return dict(available[0])
        return None


def generate_adaptive_test_questions(user_id, num_questions=12):
    """Генерирует вопросы для адаптивного теста через LLM."""
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
        data = extract_json(result)
        if data and "questions" in data and len(data["questions"]) >= 6:
            return data["questions"]
    # Fallback на статические вопросы
    logger.warning("LLM недоступен, используем статические вопросы")
    questions = []
    for lvl in CEFR_ORDER:
        questions.extend(STATIC_QUESTIONS.get(lvl, []))
    return questions[:num_questions]


def evaluate_test(questions):
    """Оценивает тест и определяет уровень CEFR (для неадаптивного режима)."""
    total = len(questions)
    correct = 0
    level_scores = {}

    for q in questions:
        if q.get("selected") == q.get("answer"):
            correct += 1
            lvl = q.get("level", "A1")
            level_scores[lvl] = level_scores.get(lvl, 0) + 1

    score_pct = round((correct / total) * 100) if total else 0

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
        "level_scores": level_scores,
    }
