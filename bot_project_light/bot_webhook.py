import sys
import os
import logging
import asyncio

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from flask import Flask, request, jsonify, render_template
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import BOT_TOKEN, WEBHOOK_DOMAIN
from database import init_db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Инициализируем Flask
app = Flask(__name__)

# Инициализируем БД
init_db()
logger.info("Database initialized")

# === Хэндлеры команд ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    webapp_url = f"https://{WEBHOOK_DOMAIN}/webapp"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Open Learning App", web_app=WebAppInfo(url=webapp_url))],
    ])
    await update.message.reply_text(
        "🎯 *English AI Tutor*\n\n"
        "I'm your personal English teacher! Here's what I can do:\n\n"
        "📝 *Level Test* — Determine your CEFR level (A1-C2)\n"
        "📚 *AI Lessons* — Personalized lessons for your level\n"
        "🎧 *Podcasts* — Audio podcasts on topics you love\n"
        "🎤 *Voice Dialogue* — Speak and get corrections\n\n"
        "Tap the button below to open the full learning app 👇",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤔 *Need help?*\n\n"
        "Just send me a message in English and I'll:\n"
        "• Correct your grammar mistakes\n"
        "• Improve your vocabulary\n"
        "• Reply naturally to continue the conversation\n\n"
        "Send a voice message for speech practice!\n"
        "Use /start to see all features.",
        parse_mode="Markdown",
    )


async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_user_data
    user_id = update.effective_user.id
    level, _, _ = get_user_data(user_id)
    await update.message.reply_text(
        f"📊 Your current level: *{level}*\n\n"
        f"Available: A1, A2, B1, B2, C1, C2\n"
        f"Use /setlevel B1 to change.",
        parse_mode="Markdown",
    )


async def setlevel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import save_user_data
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /setlevel <level> (A1, A2, B1, B2, C1, C2)")
        return
    level = context.args[0].upper()
    if level not in ("A1", "A2", "B1", "B2", "C1", "C2"):
        await update.message.reply_text(f"❌ Invalid level: {level}. Available: A1, A2, B1, B2, C1, C2")
        return
    save_user_data(user_id, level=level)
    await update.message.reply_text(f"✅ Level updated to *{level}*!", parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_connection, get_user_data
    user_id = update.effective_user.id
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM errors WHERE user_id = ?", (user_id,))
    errors = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM words WHERE user_id = ?", (user_id,))
    words = c.fetchone()[0]
    conn.close()
    level, history, _ = get_user_data(user_id)
    msg_count = len([m for m in history if m["role"] == "user"])
    await update.message.reply_text(
        f"📊 *Your Statistics*\n\n"
        f"Level: *{level}*\n"
        f"Messages sent: *{msg_count}*\n"
        f"Errors corrected: *{errors}*\n"
        f"Words learned: *{words}*",
        parse_mode="Markdown",
    )


# === Хэндлеры сообщений ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from utils.json_parser import extract_corrections_and_response
    from database import get_user_data, save_user_data, append_message, save_error
    from services.llm_service import call_llm

    user_id = update.effective_user.id
    text = update.message.text.strip()
    logger.info(f"📨 Text from {user_id}: {text[:50]}...")

    level, history, current_practice = get_user_data(user_id)

    await update.message.reply_text("🤔 ...")
    append_message(user_id, "user", text)

    # Формируем историю и вызываем LLM
    system_prompt = f"""You are an English tutor. The student's level is {level}.

Analyze the student's message and:
1. Find any English grammar/spelling errors
2. Provide corrections
3. Reply naturally to continue the conversation

Return JSON:
{{"corrections": [{{"original": "...", "corrected": "..."}}], "reply": "your reply"}}

If no errors, return empty corrections.
Speak at {level} level. Be encouraging."""

    full_messages = [
        {"role": "system", "content": system_prompt},
        *history[-10:],
        {"role": "user", "content": text},
    ]

    result = await call_llm(full_messages)

    corrections, reply = extract_corrections_and_response(result)
    if not reply:
        reply = result

    if corrections:
        corr_msg = "📝 *Corrections:*\n"
        for c in corrections:
            if c.get("original") and c.get("corrected"):
                corr_msg += f"~{c['original']}~ → *{c['corrected']}*\n"
                save_error(user_id, c["original"], c["corrected"], text)
        await update.message.reply_text(corr_msg, parse_mode="Markdown")

    # Разбиваем длинные ответы
    max_len = 4096
    if len(reply) <= max_len:
        await update.message.reply_text(reply, parse_mode="Markdown")
    else:
        for i in range(0, len(reply), max_len):
            await update.message.reply_text(reply[i:i + max_len], parse_mode="Markdown")

    append_message(user_id, "assistant", reply)
    logger.info(f"✅ Reply sent to {user_id}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from utils.json_parser import extract_corrections_and_response
    from database import get_user_data, append_message, save_error
    from services.stt_service import transcribe_audio
    from services.llm_service import call_llm

    user_id = update.effective_user.id
    logger.info(f"🎤 Voice from {user_id}")

    # Скачиваем файл
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    audio_bytes = await file.download_as_bytearray()

    await update.message.reply_text("⏳ Transcribing...")

    # Распознаём речь
    text = await transcribe_audio(bytes(audio_bytes))

    if text.startswith("❌") or text.startswith("⏳"):
        await update.message.reply_text(text)
        return

    await update.message.reply_text(f"📝 *Transcribed:* {text}", parse_mode="Markdown")

    level, history, current_practice = get_user_data(user_id)
    append_message(user_id, "user", text)

    system_prompt = f"""You are an English tutor. The student's level is {level}.

Analyze the student's message and:
1. Find any English grammar/spelling errors
2. Provide corrections
3. Reply naturally to continue the conversation

Return JSON:
{{"corrections": [{{"original": "...", "corrected": "..."}}], "reply": "your reply"}}

If no errors, return empty corrections.
Speak at {level} level. Be encouraging."""

    full_messages = [
        {"role": "system", "content": system_prompt},
        *history[-10:],
        {"role": "user", "content": text},
    ]

    result = await call_llm(full_messages)

    corrections, reply = extract_corrections_and_response(result)
    if not reply:
        reply = result

    if corrections:
        corr_msg = "📝 *Corrections:*\n"
        for c in corrections:
            if c.get("original") and c.get("corrected"):
                corr_msg += f"~{c['original']}~ → *{c['corrected']}*\n"
                save_error(user_id, c["original"], c["corrected"], text)
        await update.message.reply_text(corr_msg, parse_mode="Markdown")

    max_len = 4096
    if len(reply) <= max_len:
        await update.message.reply_text(reply, parse_mode="Markdown")
    else:
        for i in range(0, len(reply), max_len):
            await update.message.reply_text(reply[i:i + max_len], parse_mode="Markdown")

    append_message(user_id, "assistant", reply)
    logger.info(f"✅ Reply sent to {user_id}")


# === Регистрация хэндлеров ===
def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("level", level_command))
    app.add_handler(CommandHandler("setlevel", setlevel_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    logger.info("✅ Handlers registered")


# === Flask webhook endpoint ===
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    """Обрабатывает входящие webhook-запросы от Telegram."""
    try:
        data = request.get_json(force=True)

        async def _process():
            # Создаём Application заново в этом event loop, чтобы httpx-клиент
            # был привязан к текущему loop (asyncio.run создаёт новый loop).
            app = Application.builder().token(BOT_TOKEN).build()
            register_handlers(app)
            await app.initialize()
            try:
                update = Update.de_json(data, app.bot)
                await app.process_update(update)
            finally:
                await app.shutdown()

        asyncio.run(_process())
        return "OK", 200
    except Exception as e:
        logger.exception("Webhook processing error")
        # Возвращаем 200, чтобы Telegram не ретраил бесконечно
        return "OK", 200


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "bot": "English AI Tutor",
        "status": "running",
        "endpoints": ["/health", "/api/profile", "/api/progress", "/api/words", "/api/leaderboard"]
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "English AI Tutor"})


@app.route("/webapp", methods=["GET"])
def webapp():
    """Telegram Web App интерфейс."""
    return render_template("webapp.html")


@app.route("/api/profile", methods=["GET"])
def api_profile():
    """Webapp API endpoint."""
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    level, history, current_practice = get_user_data(user_id)
    return jsonify({
        "user_id": user_id,
        "level": level,
        "history_length": len(history),
        "current_practice": current_practice,
    })


@app.route("/api/progress", methods=["GET"])
def api_progress():
    from database import get_connection
    from datetime import datetime
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM errors WHERE user_id = ?", (user_id,))
    total_errors = c.fetchone()[0]
    today = datetime.now().date().isoformat()
    c.execute("SELECT COUNT(*) FROM errors WHERE user_id = ? AND date(timestamp) = ?", (user_id, today))
    today_errors = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM words WHERE user_id = ?", (user_id,))
    total_words = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM words WHERE user_id = ? AND date(next_review) <= ?", (user_id, today))
    today_words = c.fetchone()[0]
    conn.close()
    xp = total_errors + total_words * 5
    level_num = min(5, max(1, xp // 100 + 1))
    levels = ["A1", "A2", "B1", "B2", "C1"]
    level = levels[min(level_num - 1, 4)]
    return jsonify({
        "ok": True,
        "level": level,
        "xp": xp,
        "total_errors": total_errors,
        "total_words": total_words,
        "today_words": today_words,
        "today_errors": today_errors,
        "xp_to_next": (level_num) * 100,
        "level_num": level_num,
    })


@app.route("/api/words", methods=["GET"])
def api_words():
    from database import get_connection
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, word, translation, level, next_review FROM words WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    words = [{"id": r["id"], "word": r["word"], "translation": r["translation"], "level": r["level"], "next_review": r["next_review"]} for r in rows]
    return jsonify({"ok": True, "words": words})


@app.route("/api/words/add", methods=["POST"])
def api_words_add():
    from database import get_connection
    data = request.json
    user_id = data.get("user_id")
    word = data.get("word", "")
    translation = data.get("translation", "")
    if not user_id or not word or not translation:
        return jsonify({"ok": False, "error": "Missing data"}), 400
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO words (user_id, word, translation) VALUES (?, ?, ?)", (user_id, word, translation))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "word": word})


@app.route("/api/words/done", methods=["POST"])
def api_words_done():
    from database import get_connection
    from datetime import datetime, timedelta
    data = request.json
    user_id = data.get("user_id")
    word_id = data.get("word_id")
    quality = data.get("quality", 4)
    if not user_id or not word_id:
        return jsonify({"ok": False, "error": "Missing data"}), 400
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT interval, ease_factor, repetitions FROM words WHERE id = ? AND user_id = ?", (word_id, user_id))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Word not found"}), 404
    interval, ease, reps = row["interval"], row["ease_factor"], row["repetitions"]
    ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if ease < 1.3:
        ease = 1.3
    if quality < 3:
        interval = 1
        reps = 0
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = int(interval * ease)
        reps += 1
    next_review = (datetime.now() + timedelta(days=interval)).isoformat()
    c.execute("UPDATE words SET interval = ?, ease_factor = ?, repetitions = ?, next_review = ? WHERE id = ? AND user_id = ?", (interval, ease, reps, next_review, word_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "next_review": next_review, "interval": interval})


@app.route("/api/leaderboard", methods=["GET"])
def api_leaderboard():
    from database import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, xp FROM users ORDER BY xp DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    leaders = [{"name": f"User {r['user_id']}", "level": "A2", "score": r["xp"] or 0} for r in rows]
    return jsonify({"ok": True, "leaders": leaders})


# === Web App API endpoints ===
@app.route("/api/test/start", methods=["GET"])
def api_test_start():
    """Начинает тест уровня."""
    from services.tutor_service import generate_test_questions
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    questions = generate_test_questions(user_id)
    # Убираем правильные ответы из вопросов, отправляемых клиенту
    client_questions = []
    for q in questions:
        client_questions.append({
            "question": q["question"],
            "options": q["options"],
            "level": q.get("level", "A1"),
        })
    return jsonify({
        "questions": client_questions,
        "current": 0,
        "total": len(client_questions),
    })


@app.route("/api/test/submit", methods=["POST"])
def api_test_submit():
    """Оценивает тест и определяет уровень."""
    from services.tutor_service import evaluate_test
    from database import save_user_data
    data = request.json
    user_id = data.get("user_id")
    questions = data.get("answers", [])
    if not user_id or not questions:
        return jsonify({"error": "Missing data"}), 400
    result = evaluate_test(questions)
    # Сохраняем уровень пользователя
    save_user_data(user_id, level=result["level"])
    return jsonify(result)


@app.route("/api/lesson/generate", methods=["POST"])
def api_lesson_generate():
    """Генерирует урок по теме и уровню."""
    from services.tutor_service import generate_lesson
    from database import get_user_data
    data = request.json
    user_id = data.get("user_id")
    topic = data.get("topic", "")
    if not user_id or not topic:
        return jsonify({"error": "Missing data"}), 400
    level, _, _ = get_user_data(user_id)
    if not level:
        level = "A2"
    lesson = generate_lesson(user_id, level, topic)
    return jsonify(lesson)


@app.route("/api/podcast/generate", methods=["POST"])
def api_podcast_generate():
    """Генерирует подкаст."""
    from services.tutor_service import generate_podcast_script
    from services.tts_service import text_to_speech
    from database import get_user_data
    data = request.json
    user_id = data.get("user_id")
    topic = data.get("topic", "")
    if not user_id or not topic:
        return jsonify({"error": "Missing data"}), 400
    level, _, _ = get_user_data(user_id)
    if not level:
        level = "A2"
    script = generate_podcast_script(user_id, level, topic)
    # Генерируем аудио
    audio_url = text_to_speech(script.get("transcript", ""))
    script["audio_url"] = audio_url
    return jsonify(script)


@app.route("/api/dialogue/voice", methods=["POST"])
def api_dialogue_voice():
    """Обрабатывает голосовое сообщение в диалоге."""
    from services.stt_service import transcribe_audio
    from services.tutor_service import generate_dialogue_reply
    from services.tts_service import text_to_speech
    from database import get_user_data
    user_id = request.form.get("user_id", type=int)
    audio_file = request.files.get("audio")
    if not user_id or not audio_file:
        return jsonify({"error": "Missing data"}), 400
    # Читаем аудио как байты
    audio_bytes = audio_file.read()
    # Распознаём речь (асинхронная функция)
    transcript = asyncio.run(transcribe_audio(audio_bytes))
    if not transcript or transcript.startswith("❌"):
        return jsonify({"error": "Speech recognition failed. Please try again."}), 500
    level, _, _ = get_user_data(user_id)
    if not level:
        level = "A2"
    # Генерируем ответ
    result = generate_dialogue_reply(user_id, level, transcript)
    result["transcript"] = transcript
    # Генерируем аудио ответ
    audio_url = text_to_speech(result.get("reply", ""))
    result["audio_url"] = audio_url
    return jsonify(result)


def set_webhook():
    """Устанавливает webhook на Telegram."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is empty — cannot set webhook")
        return
    webhook_url = f"https://{WEBHOOK_DOMAIN}/{BOT_TOKEN}"
    try:
        async def _set():
            app = Application.builder().token(BOT_TOKEN).build()
            await app.initialize()
            try:
                await app.bot.set_webhook(webhook_url)
            finally:
                await app.shutdown()
        asyncio.run(_set())
        logger.info(f"✅ Webhook set to {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")


if __name__ == "__main__":
    set_webhook()
    # Запускаем Flask на порту 8000 (для локальной разработки)
    app.run(host="0.0.0.0", port=8000)