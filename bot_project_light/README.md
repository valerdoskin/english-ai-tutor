# English AI Tutor Bot

Telegram бот-репетитор английского языка на Flask + python-telegram-bot.
Оптимизирован для бесплатного тарифа PythonAnywhere (webhook-режим, без Telethon и тяжёлых зависимостей).

## 📁 Структура проекта
```
├── bot_webhook.py        # ОСНОВНОЙ файл: Flask + python-telegram-bot (webhook)
├── config.py             # конфигурация (загрузка .env)
├── database.py           # SQLite БД
├── index.py              # WSGI entry point для PythonAnywhere
├── webapp_proxy.py       # прокси (переиспользует app из bot_webhook)
├── services/
│   ├── llm_service.py    # LLM: Groq → DeepSeek → HuggingFace
│   └── stt_service.py    # STT: HuggingFace → Replicate
├── utils/
│   └── json_parser.py    # парсинг JSON-ответов LLM
├── requirements.txt      # минимальные зависимости
├── .env.example          # шаблон конфигурации
└── .env                  # реальные ключи (НЕ коммитить!)
```

## 🚀 Деплой на PythonAnywhere (бесплатный тариф)

### 1. Загрузить файлы
Через **Web → Files** загрузите все файлы проекта в `/home/valerdos/bot_project_light/`.

### 2. Создать `.env`
Скопируйте `.env.example` → `.env` и заполните реальные ключи:
```bash
cp .env.example .env
```
> ⚠️ **Безопасность:** ключи в `.env` уже засветились в открытом виде — **перевыпустите их** (BOT_TOKEN, GROQ_API_KEY, DEEPSEEK_API_KEY, HF_TOKEN, REPLICATE_API_KEY) перед деплоем. `.env` не должен попадать в git (добавлен в `.gitignore`).

### 3. Настроить Web → WSGI
В PythonAnywhere: **Web → WSGI configuration file** → замените содержимое на:
```python
import sys
import os
sys.path.insert(0, '/home/valerdos/bot_project_light')
from index import application
```
(`index.py` автоматически вызывает `set_webhook()` при старте.)

### 4. Установить зависимости
В Bash консоли PythonAnywhere:
```bash
cd ~/bot_project_light
pip install --user -r requirements.txt
```

### 5. Перезагрузить Web App
Нажмите **Reload** в Web → ваше приложение.

### 6. Проверить
- Webhook: `https://valerdos.pythonanywhere.com/health`
- API: `https://valerdos.pythonanywhere.com/api/profile?user_id=123`
- Отправьте боту сообщение в Telegram.

## 🔧 Локальный запуск
```bash
pip install -r requirements.txt
python bot_webhook.py
```

## 🤖 Команды бота
- `/start` — приветствие
- `/help` — помощь
- `/level` — текущий уровень
- `/setlevel B1` — установить уровень (A1-C2)
- `/stats` — статистика

## 🔑 API ключи (в `.env`)
- **Groq** (LLM, основной) — `GROQ_API_KEY`
- **DeepSeek** (LLM fallback) — `DEEPSEEK_API_KEY`
- **HuggingFace** (STT) — `HF_TOKEN`
- **Replicate** (STT fallback) — `REPLICATE_API_KEY`

## ⚙️ Оптимизация под бесплатный тариф
- Убраны тяжёлые зависимости: `telethon`, `faster-whisper`, `gtts`, `gunicorn`, `requests`, `flask-cors`.
- STT идёт через внешние API (HuggingFace/Replicate), а не локально — экономит память и диск.
- Ленивая инициализация Telegram Application при первом запросе.
- Обработка ошибок в webhook endpoint (возвращает 200, чтобы Telegram не ретраил).
