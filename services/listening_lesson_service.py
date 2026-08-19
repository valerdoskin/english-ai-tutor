"""
listening_lesson_service.py — сервис уроков аудирования.

Отвечает за:
- Шаблон урока аудирования (текст → аудио → вопросы на понимание)
- Генерацию аудио через LLM + TTS
- Упражнения на понимание (multiple choice, true/false, fill_blank)
- Регулировку скорости воспроизведения
"""
import asyncio
import json
import logging

from services.llm_service import call_llm
from services.tts_service import text_to_speech
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)

# Темы для аудирования по уровням (fallback)
LISTENING_TOPICS = {
    "A1": [
        {"topic": "My Morning Routine", "transcript": "I wake up at seven o'clock every morning. First, I brush my teeth. Then I take a shower. I eat breakfast at seven thirty. I drink coffee and eat toast. I go to work at eight o'clock. I take the bus to work. I arrive at work at eight thirty."},
        {"topic": "At the Restaurant", "transcript": "I go to a restaurant with my friend. The waiter comes to our table. He asks, 'What would you like to order?' I say, 'I would like a pizza, please.' My friend orders a salad. We drink water. The food is delicious. We pay the bill and leave."},
        {"topic": "My Family", "transcript": "I have a small family. There are four people in my family. My father is a doctor. My mother is a teacher. I have one sister. Her name is Anna. She is twelve years old. I am fifteen. We live in a small house. We are happy."},
    ],
    "A2": [
        {"topic": "A Day at the Beach", "transcript": "Last Saturday, I went to the beach with my friends. The weather was beautiful and sunny. We swam in the sea and played volleyball on the sand. At noon, we had a picnic. We ate sandwiches and drank lemonade. In the afternoon, we walked along the shore and collected seashells. We stayed until sunset. It was a wonderful day."},
        {"topic": "My Favorite Hobby", "transcript": "My favorite hobby is photography. I started taking photos two years ago. I have a small camera that I take everywhere. I like to photograph nature and animals. Last month, I took a photo of a beautiful sunset. My friends said it was amazing. I want to become a professional photographer one day."},
        {"topic": "A Trip to the City", "transcript": "Last weekend, I visited the city with my family. We took the train in the morning. First, we went to the museum. It was very interesting. Then, we had lunch at a nice restaurant. After that, we walked around the old town. We bought some souvenirs. We returned home in the evening. We were tired but happy."},
    ],
    "B1": [
        {"topic": "The Importance of Learning Languages", "transcript": "Learning a foreign language is very important in today's world. It helps you communicate with people from different countries. It also improves your memory and thinking skills. Many companies look for employees who speak more than one language. If you learn English, you can travel to many countries and make new friends. You can also watch movies and read books in their original language. In my opinion, everyone should learn at least one foreign language."},
        {"topic": "A Job Interview", "transcript": "Yesterday, I had a job interview at a technology company. I was very nervous before the interview. The interviewer asked me about my experience and skills. I told her about my previous job and my education. She also asked me why I wanted to work at their company. I explained that I was interested in their projects and wanted to grow professionally. At the end, she said they would contact me next week. I hope I get the job."},
        {"topic": "Environmental Problems", "transcript": "Environmental problems are becoming more serious every year. Climate change is affecting weather patterns around the world. Pollution is damaging our air and water. Many species of animals are in danger of extinction. However, there are things we can do to help. We can reduce, reuse, and recycle. We can use public transport instead of cars. We can save energy at home. If everyone does their part, we can make a difference."},
    ],
    "B2": [
        {"topic": "The Future of Technology", "transcript": "Technology is developing at an incredible speed. Artificial intelligence is changing the way we work and live. Self-driving cars will soon be on our roads. Virtual reality will transform education and entertainment. However, these changes also bring challenges. We need to think about privacy and security. We need to prepare people for new types of jobs. We need to make sure that technology benefits everyone, not just a few. The future is exciting, but we must be careful."},
        {"topic": "Cultural Differences", "transcript": "When you travel to a different country, you notice many cultural differences. In some cultures, people greet each other with a handshake. In others, they bow or kiss on the cheek. Food habits also vary greatly. In some countries, people eat with chopsticks, while in others they use forks and knives. Understanding these differences is important for effective communication. It helps us avoid misunderstandings and build better relationships with people from different backgrounds."},
        {"topic": "The Benefits of Exercise", "transcript": "Regular exercise has many benefits for both physical and mental health. It strengthens your heart and muscles. It helps you maintain a healthy weight. It also reduces stress and improves your mood. Studies have shown that people who exercise regularly sleep better and have more energy. However, many people find it difficult to start exercising. The key is to start slowly and choose activities you enjoy. Even thirty minutes of walking every day can make a big difference."},
    ],
    "C1": [
        {"topic": "The Impact of Social Media", "transcript": "Social media has transformed the way we communicate and consume information. While it connects people across the globe, it also raises concerns about privacy and mental health. Research suggests that excessive use of social media can lead to anxiety and depression, particularly among young people. Moreover, the spread of misinformation on these platforms poses a significant challenge to democratic societies. Nevertheless, social media also provides a platform for social movements and gives voice to marginalized communities. The key is to use it mindfully and critically."},
        {"topic": "The Economics of Globalization", "transcript": "Globalization has had a profound impact on the world economy. It has facilitated the free movement of goods, services, and capital across borders. Multinational corporations have expanded their operations globally, creating jobs in developing countries. However, critics argue that globalization has also led to income inequality and the exploitation of workers in developing nations. Furthermore, it has contributed to the homogenization of cultures. The debate over the benefits and drawbacks of globalization continues to shape economic policy worldwide."},
    ],
    "C2": [
        {"topic": "The Philosophy of Artificial Intelligence", "transcript": "The rapid advancement of artificial intelligence raises profound philosophical questions about consciousness, agency, and the nature of intelligence itself. If machines can perform tasks that require human-like reasoning, what does this mean for our understanding of the human mind? Some philosophers argue that consciousness is not reducible to computational processes, while others contend that it is merely a complex information-processing phenomenon. These debates have practical implications for how we design AI systems and integrate them into society."},
        {"topic": "The Ethics of Genetic Engineering", "transcript": "Genetic engineering presents humanity with unprecedented ethical dilemmas. The ability to modify the human genome offers the potential to eliminate hereditary diseases and enhance human capabilities. However, it also raises concerns about eugenics, inequality, and the commodification of human life. Should parents be allowed to select the genetic traits of their children? Who should have access to these technologies? These questions require careful consideration of both scientific possibilities and moral principles."},
    ],
}


def get_listening_topics(level):
    """Возвращает темы для аудирования по уровню."""
    return LISTENING_TOPICS.get(level, LISTENING_TOPICS.get("A1", []))


def generate_listening_lesson(level, topic=None):
    """Генерирует урок аудирования через LLM (или fallback)."""
    if not topic:
        topics = get_listening_topics(level)
        topic = topics[0]["topic"] if topics else "A Short Story"

    prompt = f"""Create a listening lesson for a {level} level English student on the topic: "{topic}".

Return ONLY valid JSON in this exact format:
{{
  "topic": "{topic}",
  "transcript": "A short listening text (100-200 words) appropriate for {level} level",
  "questions": [
    {{
      "type": "multiple_choice",
      "question": "What is the main topic of the text?",
      "options": ["option1", "option2", "option3", "option4"],
      "answer": 0
    }},
    {{
      "type": "true_false",
      "question": "The speaker lives in a big city.",
      "answer": true
    }},
    {{
      "type": "fill_blank",
      "question": "Complete: The speaker ___ to work every day.",
      "answer": "goes"
    }}
  ]
}}
Create 3-4 questions of different types (multiple_choice, true_false, fill_blank).
The transcript should be appropriate for a {level} CEFR level student.
Return ONLY the JSON, no other text."""

    result = asyncio.run(call_llm([{"role": "user", "content": prompt}]))
    if result and not result.startswith("❌"):
        data = extract_json(result)
        if data and "transcript" in data:
            return data
    # Fallback
    return _fallback_listening_lesson(level, topic)


def _fallback_listening_lesson(level, topic):
    """Создаёт урок аудирования без LLM."""
    topics = get_listening_topics(level)
    topic_data = None
    for t in topics:
        if t["topic"].lower() == topic.lower():
            topic_data = t
            break
    if not topic_data:
        topic_data = topics[0] if topics else {"topic": topic, "transcript": f"This is a short listening text about {topic}."}

    transcript = topic_data["transcript"]
    # Создаём вопросы на основе текста
    sentences = [s.strip() for s in transcript.split(".") if s.strip()]
    questions = [
        {
            "type": "multiple_choice",
            "question": f"What is the main topic of the text?",
            "options": [topic_data["topic"], "A different topic", "A story about animals", "A news report"],
            "answer": 0,
        },
        {
            "type": "true_false",
            "question": f"The text is about {topic_data['topic']}.",
            "answer": True,
        },
        {
            "type": "fill_blank",
            "question": f"Complete the sentence: '{sentences[0][:50]}...'",
            "answer": sentences[0].split()[-1] if sentences else "word",
        },
    ]
    return {
        "topic": topic_data["topic"],
        "transcript": transcript,
        "questions": questions,
    }


def generate_listening_audio(level, topic=None):
    """Генерирует урок аудирования с аудиофайлом."""
    lesson = generate_listening_lesson(level, topic)
    # Генерируем аудио из транскрипта
    audio_url = text_to_speech(lesson.get("transcript", ""))
    lesson["audio_url"] = audio_url
    return lesson


def check_listening_answer(question, user_answer):
    """Проверяет ответ на вопрос по аудированию."""
    q_type = question.get("type")
    correct = question.get("answer")

    if q_type == "multiple_choice":
        try:
            return int(user_answer) == correct
        except (ValueError, TypeError):
            options = question.get("options", [])
            if isinstance(correct, int) and 0 <= correct < len(options):
                return str(user_answer).strip().lower() == str(options[correct]).strip().lower()
            return False

    elif q_type == "true_false":
        if isinstance(correct, bool):
            if isinstance(user_answer, bool):
                return user_answer == correct
            return str(user_answer).strip().lower() in ("true", "yes", "да", "верно") == correct
        return False

    elif q_type == "fill_blank":
        if isinstance(correct, str):
            return str(user_answer).strip().lower() == correct.strip().lower()
        return False

    return False
