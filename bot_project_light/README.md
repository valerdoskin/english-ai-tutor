# English AI Tutor Bot

Telegram бот-репетитор английского языка на Flask + python-telegram-bot.
Включает **Telegram Web App** с продвинутыми функциями: тест уровня (CEFR), ИИ-уроки, аудио-подкасты и голосовой диалог.

## 📁 Структура проекта
```
├── bot_webhook.py        # ОСНОВНОЙ файл: Flask + python-telegram-bot (webhook + Web App API)
├── config.py             # конфигурация (загрузка .env)
├── database.py           # SQLite БД
├── index.py              # WSGI entry point для PythonAnywhere
├── webapp_proxy.py       # прокси (переиспользует app из bot_webhook)
├── templates/
│   └── webapp.html       # Telegram Web App интерфейс
├── static/
│   ├── webapp.js         # логика Web App
│   └── audio/            # сгенерированные аудиофайлы (TTS)
├── services/
│   ├── llm_service.py    # LLM: Groq → DeepSeek → HuggingFace → Replicate
│   ├── stt_service.py    # STT: HuggingFace → Replicate
│   ├── tts_service.py    # TTS: edge-tts (бесплатно, без ключей)
│   └── tutor_service.py  # тест CEFR, уроки, подкасты, диалог
├── utils/
│   └── json_parser.py    # парсинг JSON-ответов LLM
├── requirements.txt      # минимальные зависимости
├── .env.example          # шаблон конфигурации
└── .env                  # реальные ключи (НЕ коммитить!)
```

## 🎯 Функции Web App
- **📝 Тест уровня** — определяет CEFR уровень (A1-C2) через ИИ-вопросы
- **📚 ИИ-уроки** — персонализированные уроки по уровню и теме
- **🎧 Подкасты** — аудио-подкасты на любую тему (TTS через edge-tts)
- **🎤 Голосовой диалог** — распознавание речи, коррекция ошибок, ответы ИИ с озвучкой

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
- Web App: `https://valerdos.pythonanywhere.com/webapp`
- API: `https://valerdos.pythonanywhere.com/api/profile?user_id=123`
- Отправьте боту `/start` в Telegram → нажмите кнопку "🚀 Open Learning App".

## 🚀 Деплой на Render (бесплатный, поддерживает LLM API)

> ⚠️ **PythonAnywhere блокирует LLM API** (Groq, DeepSeek и др.), поэтому для полноценной работы ИИ-функций используйте Render.

### 1. Подготовить код
Загрузите проект на GitHub (см. ниже). В репозитории уже есть `Dockerfile` и `render.yaml`.

### 2. Создать аккаунт на Render
Зайдите на [render.com](https://render.com) → **Sign up** (можно через GitHub).

### 3. Создать Web Service
- **New** → **Web Service** → подключите ваш GitHub-репозиторий
- Render автоматически увидит `render.yaml` и предложит настройки
- Выберите план **Free**

### 4. Заполнить переменные окружения
В разделе **Environment** укажите:
- `BOT_TOKEN` — токен бота от @BotFather
- `WEBHOOK_DOMAIN` — адрес вашего сервиса на Render (например `english-ai-tutor.onrender.com`)
- `GROQ_API_KEY` — ключ от [console.groq.com](https://console.groq.com/keys) (бесплатно)
- Остальные ключи (DeepSeek, HF, Replicate) — по желанию

### 5. Deploy
Нажмите **Deploy**. Render соберёт Docker-образ и запустит приложение.

### 6. Проверить
- Health: `https://ВАШ-СЕРВИС.onrender.com/health`
- Web App: `https://ВАШ-СЕРВИС.onrender.com/webapp`
- Отправьте боту `/start` → нажмите кнопку "🚀 Open Learning App".

> 💡 **Важно:** на бесплатном плане Render сервис "засыпает" после 15 минут без запросов и просыпается при первом обращении (занимает ~30 сек). Для бота это нормально — Telegram будет ретраить.

## 📦 Размещение кода на GitHub

```bash
cd bot_project_light
git remote add origin https://github.com/ВАШ_ЛОГИН/НАЗВАНИЕ_РЕПО.git
git push -u origin master
```

> ⚠️ **Безопасность:** `.env` с ключами добавлен в `.gitignore` и **не** попадёт в git. На хостинге ключи задаются через переменные окружения (Environment), а не через `.env`.

## 🔧 Локальный запуск
```bash
pip install -r requirements.txt
python bot_webhook.py
```

## 🤖 Команды бота
- `/start` — приветствие + кнопка Web App
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
- Убраны тяжёлые зависимости: `telethon`, `faster-whisper`, `gunicorn`, `requests`, `flask-cors`.
- STT идёт через внешние API (HuggingFace/Replicate), а не локально — экономит память и диск.
- TTS через `edge-tts` (бесплатно, без ключей).
- Ленивая инициализация Telegram Application при первом запросе.
- Обработка ошибок в webhook endpoint (возвращает 200, чтобы Telegram не ретраил).


