"""Unit-тесты для MVP English AI Tutor.

Покрывает:
- Адаптивный тест уровня (банк вопросов, оценка)
- Генерацию уроков грамматики (fallback без LLM)
- Генерацию уроков аудирования (fallback без LLM)
- Разговорную практику (fallback диалог)
- Программу обучения (модули, уроки)
- Геймификацию (достижения, мотивационные сообщения)
- API endpoints (stats, modules, grammar, listening, speaking)
"""
import os
import sys
import unittest
import tempfile

# Настраиваем тестовую БД до импорта модулей
TEST_DB = tempfile.mktemp(suffix=".db")
os.environ["DB_PATH"] = TEST_DB

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Переопределяем DB_PATH в config до импорта database
import config
config.DB_PATH = TEST_DB

import database
database.init_db()

from services import adaptive_test_service
from services import grammar_lesson_service
from services import listening_lesson_service
from services import speaking_service
from services import curriculum_service
from services import gamification_service
from services.question_bank import QUESTION_BANK


class TestQuestionBank(unittest.TestCase):
    """Тесты банка вопросов для адаптивного теста."""

    def test_question_bank_has_all_levels(self):
        """Банк вопросов содержит все уровни A1-C2."""
        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        for level in levels:
            self.assertIn(level, QUESTION_BANK, f"Уровень {level} отсутствует в банке")
            self.assertGreaterEqual(len(QUESTION_BANK[level]), 10,
                                    f"Уровень {level} имеет меньше 10 вопросов")

    def test_question_structure(self):
        """Каждый вопрос имеет корректную структуру."""
        for level, questions in QUESTION_BANK.items():
            for q in questions:
                self.assertIn("question", q, f"Вопрос без поля question: {q}")
                self.assertIn("options", q, f"Вопрос без поля options: {q}")
                self.assertIn("answer", q, f"Вопрос без поля answer: {q}")
                self.assertIn("skill", q, f"Вопрос без поля skill: {q}")
                self.assertEqual(len(q["options"]), 4, f"Вопрос должен иметь 4 варианта: {q}")
                # answer — индекс правильного варианта
                self.assertIsInstance(q["answer"], int, f"answer должен быть индексом: {q}")
                self.assertGreaterEqual(q["answer"], 0, f"answer должен быть >= 0: {q}")
                self.assertLess(q["answer"], len(q["options"]),
                                f"answer должен быть < len(options): {q}")


class TestAdaptiveTest(unittest.TestCase):
    """Тесты адаптивного теста уровня."""

    def test_generate_questions(self):
        """Генерация вопросов для теста."""
        questions = adaptive_test_service.generate_adaptive_test_questions(9999, num_questions=12)
        self.assertEqual(len(questions), 12)
        for q in questions:
            self.assertIn("question", q)
            self.assertIn("options", q)
            self.assertIn("answer", q)

    def test_evaluate_test(self):
        """Оценка теста."""
        questions = adaptive_test_service.generate_adaptive_test_questions(9999, num_questions=5)
        # Все ответы правильные
        for q in questions:
            q["selected"] = q["answer"]
        result = adaptive_test_service.evaluate_test(questions)
        self.assertIn("score", result)
        self.assertIn("level", result)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)


class TestGrammarLesson(unittest.TestCase):
    """Тесты генерации уроков грамматики."""

    def test_fallback_lesson(self):
        """Fallback-урок грамматики работает без LLM."""
        lesson = grammar_lesson_service.generate_grammar_lesson("A1", "Present Simple")
        self.assertIn("topic", lesson)
        self.assertIn("explanation", lesson)
        self.assertIn("exercises", lesson)
        self.assertGreaterEqual(len(lesson["exercises"]), 3)

    def test_exercise_structure(self):
        """Упражнения имеют корректную структуру."""
        lesson = grammar_lesson_service.generate_grammar_lesson("A1", "Present Simple")
        for ex in lesson["exercises"]:
            self.assertIn("type", ex)
            self.assertIn("instruction", ex)
            self.assertIn("answer", ex)
            self.assertIn("hint", ex)

    def test_check_answer(self):
        """Проверка ответов работает."""
        # fill_blank
        ex = {"type": "fill_blank", "answer": "goes", "sentence": "She ___ to school"}
        self.assertTrue(grammar_lesson_service.check_answer(ex, "goes"))
        self.assertTrue(grammar_lesson_service.check_answer(ex, " GOES "))
        self.assertFalse(grammar_lesson_service.check_answer(ex, "go"))

        # multiple_choice — answer это индекс
        ex = {"type": "multiple_choice", "answer": 1, "options": ["go", "goes", "going", "gone"]}
        self.assertTrue(grammar_lesson_service.check_answer(ex, "1"))
        self.assertTrue(grammar_lesson_service.check_answer(ex, "goes"))
        self.assertFalse(grammar_lesson_service.check_answer(ex, "0"))

    def test_topics(self):
        """Список тем грамматики."""
        topics = grammar_lesson_service.get_grammar_topics("A1")
        self.assertGreaterEqual(len(topics), 5)


class TestListeningLesson(unittest.TestCase):
    """Тесты генерации уроков аудирования."""

    def test_fallback_lesson(self):
        """Fallback-урок аудирования работает без LLM."""
        lesson = listening_lesson_service.generate_listening_lesson("A1", "My Morning Routine")
        self.assertIn("topic", lesson)
        self.assertIn("transcript", lesson)
        self.assertIn("questions", lesson)
        self.assertGreaterEqual(len(lesson["questions"]), 3)

    def test_question_structure(self):
        """Вопросы аудирования имеют корректную структуру."""
        lesson = listening_lesson_service.generate_listening_lesson("A1", "My Morning Routine")
        for q in lesson["questions"]:
            self.assertIn("type", q)
            self.assertIn("question", q)
            self.assertIn("answer", q)

    def test_check_answer(self):
        """Проверка ответов на вопросы аудирования."""
        # multiple_choice — answer это индекс
        q = {"type": "multiple_choice", "answer": 0, "options": ["A", "B", "C", "D"]}
        self.assertTrue(listening_lesson_service.check_listening_answer(q, "0"))
        self.assertTrue(listening_lesson_service.check_listening_answer(q, "A"))
        self.assertFalse(listening_lesson_service.check_listening_answer(q, "1"))

    def test_topics(self):
        """Список тем аудирования."""
        topics = listening_lesson_service.get_listening_topics("A1")
        self.assertGreaterEqual(len(topics), 3)


class TestSpeaking(unittest.TestCase):
    """Тесты разговорной практики."""

    def test_roleplay_scenarios(self):
        """Сценарии ролевых игр."""
        scenarios = speaking_service.get_role_play_scenarios("A1")
        self.assertGreaterEqual(len(scenarios), 3)

    def test_picture_topics(self):
        """Темы описания картинок."""
        topics = speaking_service.get_picture_topics("A1")
        self.assertGreaterEqual(len(topics), 3)

    def test_fallback_dialogue(self):
        """Fallback-диалог работает без LLM."""
        reply = speaking_service._fallback_dialogue_reply("A1", "Hello, how are you?")
        self.assertIsInstance(reply, dict)
        self.assertIn("reply", reply)
        self.assertIn("feedback", reply)
        self.assertIn("corrections", reply)
        self.assertGreater(len(reply["reply"]), 0)

    def test_picture_description(self):
        """Описание картинки."""
        desc = speaking_service.generate_picture_description("A1", topic_id=0)
        self.assertIn("id", desc)
        self.assertIn("title", desc)
        self.assertIn("description", desc)


class TestCurriculum(unittest.TestCase):
    """Тесты программы обучения."""

    def test_modules_for_level(self):
        """Модули для уровня."""
        modules = curriculum_service.ensure_modules_for_level("A1")
        self.assertGreaterEqual(len(modules), 3)

    def test_next_level(self):
        """Следующий уровень."""
        self.assertEqual(curriculum_service.get_next_level("A1"), "A2")
        self.assertEqual(curriculum_service.get_next_level("B1"), "B2")
        # C2 — последний уровень, следующего нет
        self.assertIsNone(curriculum_service.get_next_level("C2"))

    def test_previous_level(self):
        """Предыдущий уровень."""
        self.assertEqual(curriculum_service.get_previous_level("A2"), "A1")
        self.assertEqual(curriculum_service.get_previous_level("B2"), "B1")
        # A1 — первый уровень, предыдущего нет
        self.assertIsNone(curriculum_service.get_previous_level("A1"))


class TestGamification(unittest.TestCase):
    """Тесты геймификации."""

    def test_motivational_messages(self):
        """Мотивационные сообщения."""
        self.assertIn("Start", gamification_service.get_motivational_message(0))
        self.assertIn("streak", gamification_service.get_motivational_message(3).lower())
        self.assertIn("days in a row", gamification_service.get_motivational_message(10).lower())
        self.assertIn("streak", gamification_service.get_motivational_message(40).lower())

    def test_achievements_defined(self):
        """Достижения определены."""
        self.assertGreaterEqual(len(gamification_service.ACHIEVEMENTS), 10)
        for key, meta in gamification_service.ACHIEVEMENTS.items():
            self.assertIn("title", meta)
            self.assertIn("description", meta)
            self.assertIn("icon", meta)


class TestAPIEndpoints(unittest.TestCase):
    """Тесты API endpoints."""

    @classmethod
    def setUpClass(cls):
        import bot_webhook
        cls.client = bot_webhook.app.test_client()
        cls.user_id = 99999  # тестовый пользователь

    def test_stats(self):
        """GET /api/stats."""
        resp = self.client.get(f"/api/stats?user_id={self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("stats", data)

    def test_stats_missing_user(self):
        """GET /api/stats без user_id."""
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 400)

    def test_modules(self):
        """GET /api/modules."""
        resp = self.client.get(f"/api/modules?user_id={self.user_id}&level=A1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("modules", data)

    def test_grammar_topics(self):
        """GET /api/grammar/topics."""
        resp = self.client.get(f"/api/grammar/topics?user_id={self.user_id}&level=A1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])

    def test_grammar_lesson(self):
        """GET /api/grammar/lesson."""
        resp = self.client.get(f"/api/grammar/lesson?user_id={self.user_id}&level=A1&topic=Present%20Simple")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("lesson", data)

    def test_listening_topics(self):
        """GET /api/listening/topics."""
        resp = self.client.get(f"/api/listening/topics?user_id={self.user_id}&level=A1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])

    def test_listening_lesson(self):
        """GET /api/listening/lesson."""
        resp = self.client.get(f"/api/listening/lesson?user_id={self.user_id}&level=A1&topic=My%20Morning%20Routine")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("lesson", data)

    def test_speaking_roleplay(self):
        """GET /api/speaking/roleplay."""
        resp = self.client.get(f"/api/speaking/roleplay?user_id={self.user_id}&level=A1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])

    def test_speaking_pictures(self):
        """GET /api/speaking/pictures."""
        resp = self.client.get(f"/api/speaking/pictures?user_id={self.user_id}&level=A1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])

    def test_achievements(self):
        """GET /api/achievements."""
        resp = self.client.get(f"/api/achievements?user_id={self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("achievements", data)

    def test_adaptive_test_start(self):
        """GET /api/adaptive-test/start."""
        resp = self.client.get(f"/api/adaptive-test/start?user_id={self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("question", data)
        self.assertIn("total", data)
        self.assertIn("current", data)

    def test_daily_practice(self):
        """GET /api/daily-practice."""
        resp = self.client.get(f"/api/daily-practice?user_id={self.user_id}&level=A1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])


class TestPhase2Features(unittest.TestCase):
    """Тесты функций Этапа 2 (B2-C2, SRS, статистика, монологи, TBLT)."""

    @classmethod
    def setUpClass(cls):
        import bot_webhook
        cls.client = bot_webhook.app.test_client()
        cls.user_id = 99999  # тестовый пользователь

    def test_clil_modules(self):
        """CLIL-модули доступны для B2, C1, C2."""
        from services.curriculum_service import ensure_clil_modules_for_level, CLIL_MODULES
        for level in ["B2", "C1", "C2"]:
            self.assertIn(level, CLIL_MODULES, f"CLIL-модули для {level} отсутствуют")
            self.assertGreaterEqual(len(CLIL_MODULES[level]), 3, f"CLIL-модули для {level} < 3")
            for m in CLIL_MODULES[level]:
                self.assertIn("title", m)
                self.assertIn("description", m)
                self.assertIn("clil", m, f"Модуль {m['title']} не помечен как CLIL")
            modules = ensure_clil_modules_for_level(level)
            self.assertGreaterEqual(len(modules), 3, f"CLIL-модули для {level} < 3")

    def test_ielts_toefl_tasks(self):
        """IELTS/TOEFL задания доступны для B2, C1, C2."""
        from services.curriculum_service import get_ielts_toefl_tasks
        for level in ["B2", "C1", "C2"]:
            tasks = get_ielts_toefl_tasks(level)
            self.assertGreaterEqual(len(tasks), 2, f"IELTS/TOEFL задания для {level} < 2")
            for t in tasks:
                self.assertIn("title", t)
                self.assertIn("type", t)
                self.assertIn("description", t)

    def test_srs_add_word(self):
        """SRS: добавление слова."""
        from services.srs_service import add_word
        result = add_word(self.user_id, "test_word", "тестовое слово")
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_srs_add_phrase(self):
        """SRS: добавление фразы."""
        from services.srs_service import add_phrase
        result = add_phrase(self.user_id, "take into account", "принимать во внимание")
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_srs_add_grammar(self):
        """SRS: добавление грамматической конструкции."""
        from services.srs_service import add_grammar_item
        result = add_grammar_item(self.user_id, "had + past participle", "Past Perfect")
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_srs_due_words(self):
        """SRS: получение слов для повторения."""
        from services.srs_service import get_due_words
        due = get_due_words(self.user_id)
        self.assertIsInstance(due, list)

    def test_srs_review(self):
        """SRS: повторение слова."""
        from services.srs_service import add_word, get_due_words, review_word
        add_word(self.user_id, "review_test", "тест")
        due = get_due_words(self.user_id)
        word = next((w for w in due if w.get("word") == "review_test"), None)
        if word:
            result = review_word(self.user_id, word["id"], 4)
            self.assertIsNotNone(result)

    def test_monologue_topics(self):
        """Монологи доступны для B2, C1, C2."""
        from services.speaking_service import get_monologue_topics
        for level in ["B2", "C1", "C2"]:
            topics = get_monologue_topics(level)
            self.assertGreaterEqual(len(topics), 2, f"Монологи для {level} < 2")
            for t in topics:
                self.assertIn("title", t)
                self.assertIn("description", t)
                self.assertIn("prompt", t)
                self.assertIn("tips", t)

    def test_tblt_tasks(self):
        """TBLT-задачи доступны для B2, C1, C2."""
        from services.speaking_service import get_tblt_tasks
        for level in ["B2", "C1", "C2"]:
            tasks = get_tblt_tasks(level)
            self.assertGreaterEqual(len(tasks), 2, f"TBLT-задачи для {level} < 2")
            for t in tasks:
                self.assertIn("title", t)
                self.assertIn("description", t)
                self.assertIn("steps", t)
                self.assertIn("language_focus", t)

    def test_analytics_activity(self):
        """Аналитика: активность за период."""
        from services.analytics_service import get_activity_by_period
        result = get_activity_by_period(self.user_id, period="week")
        self.assertIsInstance(result, list)

    def test_analytics_vocabulary(self):
        """Аналитика: статистика словаря."""
        from services.analytics_service import get_vocabulary_stats
        result = get_vocabulary_stats(self.user_id)
        self.assertIn("total", result)
        self.assertIn("words", result)
        self.assertIn("phrases", result)
        self.assertIn("grammar", result)

    def test_analytics_skills(self):
        """Аналитика: прогресс по навыкам."""
        from services.analytics_service import get_skill_progress
        result = get_skill_progress(self.user_id)
        self.assertIsInstance(result, dict)
        self.assertIn("grammar", result)
        self.assertIn("vocabulary", result)
        self.assertIn("listening", result)
        self.assertIn("speaking", result)

    def test_analytics_goals(self):
        """Аналитика: ежедневные цели."""
        from services.analytics_service import get_daily_goal_stats
        result = get_daily_goal_stats(self.user_id)
        self.assertIsInstance(result, list)

    def test_api_clil_modules(self):
        """GET /api/clil/modules."""
        resp = self.client.get(f"/api/clil/modules?user_id={self.user_id}&level=B2")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("modules", data)

    def test_api_ielts_toefl(self):
        """GET /api/ielts-toefl/tasks."""
        resp = self.client.get(f"/api/ielts-toefl/tasks?user_id={self.user_id}&level=B2")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("tasks", data)

    def test_api_words_due(self):
        """GET /api/words/due."""
        resp = self.client.get(f"/api/words/due?user_id={self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("words", data)

    def test_api_stats_activity(self):
        """GET /api/stats/activity."""
        resp = self.client.get(f"/api/stats/activity?user_id={self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])

    def test_api_stats_vocabulary(self):
        """GET /api/stats/vocabulary."""
        resp = self.client.get(f"/api/stats/vocabulary?user_id={self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])

    def test_api_stats_skills(self):
        """GET /api/stats/skills."""
        resp = self.client.get(f"/api/stats/skills?user_id={self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])

    def test_api_stats_goals(self):
        """GET /api/stats/goals."""
        resp = self.client.get(f"/api/stats/goals?user_id={self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])

    def test_api_speaking_monologues(self):
        """GET /api/speaking/monologues."""
        resp = self.client.get(f"/api/speaking/monologues?user_id={self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("topics", data)

    def test_api_speaking_tblt(self):
        """GET /api/speaking/tblt."""
        resp = self.client.get(f"/api/speaking/tblt?user_id={self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("tasks", data)

    def test_api_speaking_monologue_evaluate(self):
        """POST /api/speaking/monologue/evaluate."""
        resp = self.client.post("/api/speaking/monologue/evaluate",
                                json={"user_id": self.user_id, "text": "This is a test monologue about technology.",
                                      "topic_id": "technology_impact"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("score", data)
        self.assertIn("words", data)

    def test_api_speaking_tblt_evaluate(self):
        """POST /api/speaking/tblt/evaluate."""
        resp = self.client.post("/api/speaking/tblt/evaluate",
                                json={"user_id": self.user_id, "text": "I would plan a business trip carefully.",
                                      "task_id": "plan_trip"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("score", data)
        self.assertIn("words", data)


if __name__ == "__main__":
    unittest.main()
