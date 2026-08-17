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

MAX_HISTORY = 10
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tutor_bot.db")
