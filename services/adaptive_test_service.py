"""
adaptive_test_service.py — адаптивный тест определения уровня CEFR.

Реализует адаптивный алгоритм: сложность вопросов подстраивается
под ответы пользователя (как в Duolingo English Test).
Поддерживает сохранение состояния теста между запросами.
"""
import asyncio
import json
import logging

from services.llm_service import call_llm
from services.question_bank import get_questions_for_level, get_all_questions
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)

CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Описания уровней для отчёта
CEFR_DESCRIPTIONS = {
    "A1": {
        "name": "Beginner (Начальный)",
        "description": "Понимаете и используете базовые фразы и выражения. Можете представиться и задать простые вопросы.",
    },
    "A2": {
        "name": "Elementary (Элементарный)",
        "description": "Понимаете простые предложения и часто используемые выражения. Можете общаться в простых ситуациях.",
    },
    "B1": {
        "name": "Intermediate (Средний)",
        "description": "Понимаете основные идеи на знакомые темы. Можете справиться с большинством ситуаций в путешествиях.",
    },
    "B2": {
        "name": "Upper-Intermediate (Выше среднего)",
        "description": "Понимаете сложные тексты и можете общаться с носителями без напряжения. Можете аргументировать свою точку зрения.",
    },
    "C1": {
        "name": "Advanced (Продвинутый)",
        "description": "Понимаете сложные тексты и можете выражать мысли бегло и спонтанно. Используете язык гибко и эффективно.",
    },
    "C2": {
        "name": "Proficient (Свободное владение)",
        "description": "Понимаете практически всё услышанное и прочитанное. Выражаетесь спонтанно, точно и бегло.",
    },
}


class AdaptiveTest:
    """Адаптивный тест уровня CEFR с сохранением состояния."""

    def __init__(self, max_questions=15, state=None):
        self.max_questions = max_questions
        if state:
            self._load_state(state)
        else:
            self.current_level_idx = 2  # Начинаем с B1
            self.questions = []
            self.answers = []
            self.level_scores = {lvl: {"correct": 0, "total": 0} for lvl in CEFR_ORDER}
            self.skill_scores = {"grammar": {"correct": 0, "total": 0},
                                 "vocabulary": {"correct": 0, "total": 0}}

    def _load_state(self, state):
        """Загружает состояние теста из словаря."""
        self.current_level_idx = state.get("current_level_idx", 2)
        self.questions = state.get("questions", [])
        self.answers = state.get("answers", [])
        self.level_scores = state.get("level_scores", {lvl: {"correct": 0, "total": 0} for lvl in CEFR_ORDER})
        self.skill_scores = state.get("skill_scores", {"grammar": {"correct": 0, "total": 0},
                                                       "vocabulary": {"correct": 0, "total": 0}})

    def to_state(self):
        """Возвращает состояние теста для сохранения."""
        return {
            "current_level_idx": self.current_level_idx,
            "questions": self.questions,
            "answers": self.answers,
            "level_scores": self.level_scores,
            "skill_scores": self.skill_scores,
        }

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
        skill = question.get("skill", "grammar")

        self.level_scores[level]["total"] += 1
        self.skill_scores[skill]["total"] += 1
        if correct:
            self.level_scores[level]["correct"] += 1
            self.skill_scores[skill]["correct"] += 1

        self.answers.append({"question": question["question"], "selected": selected,
                             "correct": correct, "level": level, "skill": skill})

        # Адаптация сложности
        if correct:
            self.current_level_idx = min(self.current_level_idx + 1, len(CEFR_ORDER) - 1)
        else:
            self.current_level_idx = max(self.current_level_idx - 1, 0)

        return {"correct": correct, "level": level, "skill": skill}

    def get_result(self):
        """Возвращает детальный результат теста."""
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

        # Детальный отчёт по навыкам
        skill_report = {}
        for skill, s in self.skill_scores.items():
            if s["total"] > 0:
                skill_report[skill] = {
                    "correct": s["correct"],
                    "total": s["total"],
                    "percent": round((s["correct"] / s["total"]) * 100),
                }
            else:
                skill_report[skill] = {"correct": 0, "total": 0, "percent": 0}

        # Рекомендации на основе слабых мест
        recommendations = []
        if skill_report.get("grammar", {}).get("percent", 100) < 60:
            recommendations.append("Уделите больше внимания грамматике: повторите времена и конструкции.")
        if skill_report.get("vocabulary", {}).get("percent", 100) < 60:
            recommendations.append("Расширяйте словарный запас: учите по 5-10 новых слов в день.")
        if not recommendations:
            recommendations.append("Отличный результат! Продолжайте в том же темпе.")

        return {
            "level": result_level,
            "level_name": CEFR_DESCRIPTIONS[result_level]["name"],
            "description": CEFR_DESCRIPTIONS[result_level]["description"],
            "score": score_pct,
            "correct": total_correct,
            "total": total,
            "level_scores": level_scores,
            "skill_report": skill_report,
            "recommendations": recommendations,
        }

    def _get_question_for_level(self, level):
        """Возвращает вопрос для уровня из банка вопросов."""
        questions = get_questions_for_level(level, exclude=self.questions)
        if questions:
            return dict(questions[0])
        return None


def generate_adaptive_test_questions(user_id, num_questions=15):
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
      "level": "A1",
      "skill": "grammar"
    }}
  ]
}}
The "answer" field is the index (0-3) of the correct option.
The "skill" field is either "grammar" or "vocabulary".
Make sure exactly one option is correct for each question.
Return ONLY the JSON, no other text."""

    result = asyncio.run(call_llm([{"role": "user", "content": prompt}]))
    if result and not result.startswith("❌"):
        data = extract_json(result)
        if data and "questions" in data and len(data["questions"]) >= 6:
            return data["questions"]
    # Fallback на статические вопросы
    logger.warning("LLM недоступен, используем статические вопросы")
    return get_all_questions()[:num_questions]


def evaluate_test(questions):
    """Оценивает тест и определяет уровень CEFR (для неадаптивного режима)."""
    total = len(questions)
    correct = 0
    level_scores = {}
    skill_scores = {"grammar": {"correct": 0, "total": 0}, "vocabulary": {"correct": 0, "total": 0}}

    for q in questions:
        if q.get("selected") == q.get("answer"):
            correct += 1
            lvl = q.get("level", "A1")
            level_scores[lvl] = level_scores.get(lvl, 0) + 1
        skill = q.get("skill", "grammar")
        skill_scores[skill]["total"] += 1
        if q.get("selected") == q.get("answer"):
            skill_scores[skill]["correct"] += 1

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

    skill_report = {}
    for skill, s in skill_scores.items():
        if s["total"] > 0:
            skill_report[skill] = {
                "correct": s["correct"],
                "total": s["total"],
                "percent": round((s["correct"] / s["total"]) * 100),
            }
        else:
            skill_report[skill] = {"correct": 0, "total": 0, "percent": 0}

    return {
        "level": level,
        "level_name": CEFR_DESCRIPTIONS[level]["name"],
        "description": CEFR_DESCRIPTIONS[level]["description"],
        "score": score_pct,
        "correct": correct,
        "total": total,
        "level_scores": level_scores,
        "skill_report": skill_report,
    }
