import os
from dotenv import load_dotenv

# Загружаем .env из директории config.py (не зависит от рабочей директории)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Домен PythonAnywhere для webhook (без https:// и без слэша в конце)
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN", "valerdos.pythonanywhere.com")

# DeepSeek (LLM) fallback
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Hugging Face (Speech-to-Text fallback)
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_WHISPER_MODEL = os.getenv("HF_WHISPER_MODEL", "openai/whisper-large-v3")

# Replicate (Speech-to-Text)
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY", "")

# Groq (основной LLM) — бесплатный, быстрый
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

MAX_HISTORY = int(os.getenv("MAX_HISTORY", "10"))
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tutor_bot.db")

# === Настройки приложения ===
TEST_QUESTIONS_COUNT = int(os.getenv("TEST_QUESTIONS_COUNT", "12"))
DAILY_WORDS_LIMIT = int(os.getenv("DAILY_WORDS_LIMIT", "20"))
LESSONS_PER_MODULE = int(os.getenv("LESSONS_PER_MODULE", "5"))

# === Настройки геймификации (XP) ===
XP_LESSON = int(os.getenv("XP_LESSON", "20"))
XP_TEST_QUESTION = int(os.getenv("XP_TEST_QUESTION", "5"))
XP_WORD = int(os.getenv("XP_WORD", "5"))
XP_VOICE = int(os.getenv("XP_VOICE", "10"))
XP_DAILY = int(os.getenv("XP_DAILY", "15"))
XP_TASK = int(os.getenv("XP_TASK", "30"))
