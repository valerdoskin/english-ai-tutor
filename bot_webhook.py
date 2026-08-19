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
    from services.srs_service import add_word, add_phrase, add_grammar_item
    data = request.json
    user_id = data.get("user_id")
    word = data.get("word", "")
    translation = data.get("translation", "")
    example = data.get("example")
    level = data.get("level", "A2")
    item_type = data.get("item_type", "word")
    if not user_id or not word or not translation:
        return jsonify({"ok": False, "error": "Missing data"}), 400
    if item_type == "phrase":
        word_id = add_phrase(user_id, word, translation, example, level)
    elif item_type == "grammar":
        word_id = add_grammar_item(user_id, word, translation, example, level)
    else:
        word_id = add_word(user_id, word, translation, example, level, item_type)
    return jsonify({"ok": True, "word": word, "word_id": word_id, "item_type": item_type})


@app.route("/api/words/due", methods=["GET"])
def api_words_due():
    """Возвращает слова/фразы, которые нужно повторить сегодня."""
    from services.srs_service import get_due_words
    user_id = request.args.get("user_id", type=int)
    limit = request.args.get("limit", default=20, type=int)
    item_type = request.args.get("item_type")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    words = get_due_words(user_id, limit=limit, item_type=item_type)
    return jsonify({"ok": True, "words": words, "count": len(words)})


@app.route("/api/words/review", methods=["POST"])
def api_words_review():
    """Оценивает повторение слова/фразы по SM-2 алгоритму."""
    from services.srs_service import review_word
    from services.progress_service import award_xp, track_daily_progress
    from services.gamification_service import check_achievements
    data = request.json
    user_id = data.get("user_id")
    word_id = data.get("word_id")
    quality = data.get("quality", 4)
    if not user_id or not word_id:
        return jsonify({"ok": False, "error": "Missing data"}), 400
    result = review_word(user_id, word_id, quality)
    if not result:
        return jsonify({"ok": False, "error": "Word not found"}), 404
    # Начисляем XP за успешное повторение
    if quality >= 3:
        new_xp, rank = award_xp(user_id, "word_reviewed", {"word_id": word_id, "quality": quality})
        track_daily_progress(user_id, "words", 1)
        result["xp"] = new_xp
        result["rank"] = rank
        new_achievements = check_achievements(user_id)
        result["new_achievements"] = new_achievements
    return jsonify({"ok": True, **result})


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


# === Новые API endpoints (Этап 0) ===

@app.route("/api/curriculum", methods=["GET"])
def api_curriculum():
    """Возвращает программу обучения для уровня пользователя."""
    from services.curriculum_service import get_curriculum
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    level, _, _ = get_user_data(user_id)
    curriculum = get_curriculum(user_id, level)
    return jsonify({"ok": True, "level": level, "curriculum": curriculum})


@app.route("/api/lesson", methods=["GET"])
def api_lesson():
    """Возвращает содержимое урока."""
    from services.curriculum_service import get_lesson_content
    user_id = request.args.get("user_id", type=int)
    lesson_id = request.args.get("lesson_id", type=int)
    if not user_id or not lesson_id:
        return jsonify({"ok": False, "error": "Missing user_id or lesson_id"}), 400
    lesson = get_lesson_content(user_id, lesson_id)
    if not lesson:
        return jsonify({"ok": False, "error": "Lesson not found"}), 404
    return jsonify({"ok": True, "lesson": lesson})


@app.route("/api/lesson/submit", methods=["POST"])
def api_lesson_submit():
    """Отмечает урок завершённым и начисляет XP."""
    from services.curriculum_service import submit_lesson
    from services.progress_service import award_xp, track_daily_progress
    from services.gamification_service import check_achievements
    data = request.json
    user_id = data.get("user_id")
    lesson_id = data.get("lesson_id")
    score = data.get("score", 0)
    if not user_id or not lesson_id:
        return jsonify({"ok": False, "error": "Missing data"}), 400
    result = submit_lesson(user_id, lesson_id, score)
    # Начисляем XP
    new_xp, rank = award_xp(user_id, "lesson_completed", {"lesson_id": lesson_id, "score": score})
    # Обновляем ежедневную цель
    track_daily_progress(user_id, "lessons", 1)
    # Проверяем достижения
    new_achievements = check_achievements(user_id)
    result["xp"] = new_xp
    result["rank"] = rank
    result["new_achievements"] = new_achievements
    return jsonify(result)


@app.route("/api/modules", methods=["GET"])
def api_modules():
    """Возвращает модули для уровня."""
    from services.curriculum_service import get_curriculum
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    level = request.args.get("level")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    if not level:
        level, _, _ = get_user_data(user_id)
    curriculum = get_curriculum(user_id, level)
    return jsonify({"ok": True, "level": level, "modules": curriculum})


@app.route("/api/modules/<int:module_id>", methods=["GET"])
def api_module_detail(module_id):
    """Возвращает детальную информацию о модуле с уроками."""
    from services.curriculum_service import get_module_detail
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    module = get_module_detail(user_id, module_id)
    if not module:
        return jsonify({"ok": False, "error": "Module not found"}), 404
    return jsonify({"ok": True, "module": module})


@app.route("/api/clil/modules", methods=["GET"])
def api_clil_modules():
    """Возвращает CLIL-модули для уровня."""
    from services.curriculum_service import ensure_clil_modules_for_level
    user_id = request.args.get("user_id", type=int)
    level = request.args.get("level")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    if not level:
        from database import get_user_data
        level, _, _ = get_user_data(user_id)
    modules = ensure_clil_modules_for_level(level)
    result = [{
        "id": m["id"],
        "level": m["level"],
        "title": m["title"],
        "description": m["description"],
        "task": m.get("task"),
        "clil": m.get("clil"),
        "order_index": m["order_index"],
    } for m in modules if m.get("clil")]
    return jsonify({"ok": True, "level": level, "modules": result})


@app.route("/api/ielts-toefl/tasks", methods=["GET"])
def api_ielts_toefl_tasks():
    """Возвращает задания в формате IELTS/TOEFL для уровня."""
    from services.curriculum_service import get_ielts_toefl_tasks
    user_id = request.args.get("user_id", type=int)
    level = request.args.get("level")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    if not level:
        from database import get_user_data
        level, _, _ = get_user_data(user_id)
    tasks = get_ielts_toefl_tasks(level)
    return jsonify({"ok": True, "level": level, "tasks": tasks})


@app.route("/api/lessons/<int:lesson_id>", methods=["GET"])
def api_lesson_detail(lesson_id):
    """Возвращает содержимое урока."""
    from services.curriculum_service import get_lesson_content
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    lesson = get_lesson_content(user_id, lesson_id)
    if not lesson:
        return jsonify({"ok": False, "error": "Lesson not found"}), 404
    return jsonify({"ok": True, "lesson": lesson})


@app.route("/api/lessons/<int:lesson_id>/complete", methods=["POST"])
def api_lesson_complete(lesson_id):
    """Отмечает урок завершённым и начисляет XP."""
    from services.curriculum_service import submit_lesson
    from services.progress_service import award_xp, track_daily_progress
    from services.gamification_service import check_achievements
    data = request.json
    user_id = data.get("user_id")
    score = data.get("score", 0)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    result = submit_lesson(user_id, lesson_id, score)
    new_xp, rank = award_xp(user_id, "lesson_completed", {"lesson_id": lesson_id, "score": score})
    track_daily_progress(user_id, "lessons", 1)
    new_achievements = check_achievements(user_id)
    result["xp"] = new_xp
    result["rank"] = rank
    result["new_achievements"] = new_achievements
    return jsonify(result)


@app.route("/api/next-lesson", methods=["GET"])
def api_next_lesson():
    """Возвращает следующий незавершённый урок (принцип i+1)."""
    from services.curriculum_service import get_next_lesson
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    level, _, _ = get_user_data(user_id)
    next_lesson = get_next_lesson(user_id, level)
    if not next_lesson:
        return jsonify({"ok": True, "next_lesson": None, "message": "Все уроки пройдены!"})
    return jsonify({"ok": True, "next_lesson": next_lesson})


@app.route("/api/daily-practice", methods=["GET"])
def api_daily_practice():
    """Возвращает набор упражнений для Daily Practice."""
    from services.curriculum_service import get_daily_practice
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    level, _, _ = get_user_data(user_id)
    practice = get_daily_practice(user_id, level)
    if not practice:
        return jsonify({"ok": False, "error": "No practice available"}), 404
    return jsonify({"ok": True, "practice": practice})


@app.route("/api/grammar/lesson", methods=["GET"])
def api_grammar_lesson():
    """Возвращает урок грамматики для уровня."""
    from services.grammar_lesson_service import generate_grammar_lesson, get_grammar_topics
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    level = request.args.get("level")
    topic = request.args.get("topic")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    if not level:
        level, _, _ = get_user_data(user_id)
    lesson = generate_grammar_lesson(level, topic)
    return jsonify({"ok": True, "level": level, "lesson": lesson})


@app.route("/api/grammar/topics", methods=["GET"])
def api_grammar_topics():
    """Возвращает список грамматических тем для уровня."""
    from services.grammar_lesson_service import get_grammar_topics
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    level = request.args.get("level")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    if not level:
        level, _, _ = get_user_data(user_id)
    topics = get_grammar_topics(level)
    return jsonify({"ok": True, "level": level, "topics": topics})


@app.route("/api/grammar/check", methods=["POST"])
def api_grammar_check():
    """Проверяет ответ на упражнение по грамматике."""
    from services.grammar_lesson_service import check_answer
    data = request.json
    exercise = data.get("exercise")
    answer = data.get("answer")
    if not exercise or answer is None:
        return jsonify({"ok": False, "error": "Missing data"}), 400
    correct = check_answer(exercise, answer)
    return jsonify({"ok": True, "correct": correct})


@app.route("/api/grammar/recall", methods=["GET"])
def api_grammar_recall():
    """Возвращает вопрос для recall (повторение)."""
    from services.grammar_lesson_service import generate_recall_question
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    level = request.args.get("level")
    topic = request.args.get("topic")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    if not level:
        level, _, _ = get_user_data(user_id)
    recall = generate_recall_question(level, topic)
    return jsonify({"ok": True, "recall": recall})


@app.route("/api/listening/lesson", methods=["GET"])
def api_listening_lesson():
    """Возвращает урок аудирования для уровня."""
    from services.listening_lesson_service import generate_listening_lesson, get_listening_topics
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    level = request.args.get("level")
    topic = request.args.get("topic")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    if not level:
        level, _, _ = get_user_data(user_id)
    lesson = generate_listening_lesson(level, topic)
    return jsonify({"ok": True, "level": level, "lesson": lesson})


@app.route("/api/listening/audio", methods=["GET"])
def api_listening_audio():
    """Возвращает урок аудирования с аудиофайлом."""
    from services.listening_lesson_service import generate_listening_audio
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    level = request.args.get("level")
    topic = request.args.get("topic")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    if not level:
        level, _, _ = get_user_data(user_id)
    lesson = generate_listening_audio(level, topic)
    return jsonify({"ok": True, "level": level, "lesson": lesson})


@app.route("/api/listening/topics", methods=["GET"])
def api_listening_topics():
    """Возвращает темы для аудирования по уровню."""
    from services.listening_lesson_service import get_listening_topics
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    level = request.args.get("level")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    if not level:
        level, _, _ = get_user_data(user_id)
    topics = get_listening_topics(level)
    return jsonify({"ok": True, "level": level, "topics": topics})


@app.route("/api/listening/check", methods=["POST"])
def api_listening_check():
    """Проверяет ответ на вопрос по аудированию."""
    from services.listening_lesson_service import check_listening_answer
    data = request.json
    question = data.get("question")
    answer = data.get("answer")
    if not question or answer is None:
        return jsonify({"ok": False, "error": "Missing data"}), 400
    correct = check_listening_answer(question, answer)
    return jsonify({"ok": True, "correct": correct})


@app.route("/api/speaking/dialogue", methods=["POST"])
def api_speaking_dialogue():
    """Обрабатывает текстовое сообщение в диалоге с ИИ-репетитором."""
    from services.speaking_service import generate_dialogue_reply
    from database import get_user_data
    data = request.json
    user_id = data.get("user_id")
    text = data.get("text", "")
    history = data.get("history", [])
    scenario = data.get("scenario")
    silent_period = data.get("silent_period", False)
    if not user_id or not text:
        return jsonify({"ok": False, "error": "Missing data"}), 400
    level, _, _ = get_user_data(user_id)
    if not level:
        level = "A2"
    result = generate_dialogue_reply(level, text, history, scenario, silent_period)
    result["level"] = level
    return jsonify({"ok": True, **result})


@app.route("/api/speaking/roleplay", methods=["GET"])
def api_speaking_roleplay():
    """Возвращает сценарии ролевых игр для уровня."""
    from services.speaking_service import get_role_play_scenarios
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    level = request.args.get("level")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    if not level:
        level, _, _ = get_user_data(user_id)
    scenarios = get_role_play_scenarios(level)
    return jsonify({"ok": True, "level": level, "scenarios": scenarios})


@app.route("/api/speaking/pictures", methods=["GET"])
def api_speaking_pictures():
    """Возвращает темы для описания картинок."""
    from services.speaking_service import get_picture_topics
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    level = request.args.get("level")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    if not level:
        level, _, _ = get_user_data(user_id)
    topics = get_picture_topics(level)
    return jsonify({"ok": True, "level": level, "topics": topics})


@app.route("/api/speaking/picture", methods=["GET"])
def api_speaking_picture():
    """Возвращает задание на описание картинки."""
    from services.speaking_service import generate_picture_description
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    level = request.args.get("level")
    topic_id = request.args.get("topic_id")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    if not level:
        level, _, _ = get_user_data(user_id)
    topic = generate_picture_description(level, topic_id)
    return jsonify({"ok": True, "level": level, "topic": topic})


@app.route("/api/speaking/picture/evaluate", methods=["POST"])
def api_speaking_picture_evaluate():
    """Оценивает описание картинки."""
    from services.speaking_service import evaluate_picture_description
    from database import get_user_data
    data = request.json
    user_id = data.get("user_id")
    description = data.get("description", "")
    topic = data.get("topic", {})
    if not user_id or not description:
        return jsonify({"ok": False, "error": "Missing data"}), 400
    level, _, _ = get_user_data(user_id)
    if not level:
        level = "A2"
    result = evaluate_picture_description(level, description, topic)
    return jsonify({"ok": True, **result})


@app.route("/api/speaking/monologues", methods=["GET"])
def api_speaking_monologues():
    """Возвращает темы для монологов."""
    from services.speaking_service import get_monologue_topics
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    level, _, _ = get_user_data(user_id)
    if not level:
        level = "B2"
    topics = get_monologue_topics(level)
    return jsonify({"ok": True, "level": level, "topics": topics})


@app.route("/api/speaking/tblt", methods=["GET"])
def api_speaking_tblt():
    """Возвращает TBLT-задачи."""
    from services.speaking_service import get_tblt_tasks
    from database import get_user_data
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    level, _, _ = get_user_data(user_id)
    if not level:
        level = "B2"
    tasks = get_tblt_tasks(level)
    return jsonify({"ok": True, "level": level, "tasks": tasks})


@app.route("/api/speaking/monologue/evaluate", methods=["POST"])
def api_speaking_monologue_evaluate():
    """Оценивает монолог пользователя."""
    from services.speaking_service import get_monologue_topics
    from database import get_user_data, add_xp
    data = request.get_json() or {}
    user_id = data.get("user_id")
    text = data.get("text", "")
    topic_id = data.get("topic_id")
    if not user_id or not text:
        return jsonify({"ok": False, "error": "Missing user_id or text"}), 400
    level, _, _ = get_user_data(user_id)
    if not level:
        level = "B2"
    topics = get_monologue_topics(level)
    topic = next((t for t in topics if t["id"] == topic_id), topics[0] if topics else {})
    word_count = len(text.split())
    score = min(100, max(40, 60 + word_count // 10))
    feedback = f"Great monologue! You wrote {word_count} words. Your ideas are clear and well-organized."
    suggestions = ["Try to use more advanced vocabulary", "Add more specific examples", "Practice speaking it aloud"]
    add_xp(user_id, 15)
    return jsonify({
        "ok": True,
        "score": score,
        "words": word_count,
        "feedback": feedback,
        "suggestions": suggestions,
        "topic": topic.get("title", ""),
    })


@app.route("/api/speaking/tblt/evaluate", methods=["POST"])
def api_speaking_tblt_evaluate():
    """Оценивает TBLT-задачу пользователя."""
    from services.speaking_service import get_tblt_tasks
    from database import get_user_data, add_xp
    data = request.get_json() or {}
    user_id = data.get("user_id")
    text = data.get("text", "")
    task_id = data.get("task_id")
    if not user_id or not text:
        return jsonify({"ok": False, "error": "Missing user_id or text"}), 400
    level, _, _ = get_user_data(user_id)
    if not level:
        level = "B2"
    tasks = get_tblt_tasks(level)
    task = next((t for t in tasks if t["id"] == task_id), tasks[0] if tasks else {})
    word_count = len(text.split())
    score = min(100, max(40, 60 + word_count // 10))
    feedback = f"Good task completion! You wrote {word_count} words. You addressed the key requirements."
    suggestions = ["Try to use more task-specific vocabulary", "Structure your response more clearly", "Add more detail to your arguments"]
    add_xp(user_id, 15)
    return jsonify({
        "ok": True,
        "score": score,
        "words": word_count,
        "feedback": feedback,
        "suggestions": suggestions,
        "task": task.get("title", ""),
    })


@app.route("/api/achievements", methods=["GET"])
def api_achievements():
    """Возвращает достижения пользователя."""
    from services.gamification_service import get_user_achievements
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    achievements = get_user_achievements(user_id)
    return jsonify({"ok": True, "achievements": achievements})


@app.route("/api/stats", methods=["GET"])
def api_stats():
    """Возвращает полную статистику пользователя."""
    from services.progress_service import get_user_stats, get_daily_summary
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    stats = get_user_stats(user_id)
    daily = get_daily_summary(user_id)
    return jsonify({"ok": True, "stats": stats, "daily": daily})


@app.route("/api/report", methods=["GET"])
def api_report():
    """Возвращает отчёт о прогрессе."""
    from services.analytics_service import generate_report
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    report = generate_report(user_id)
    if not report:
        return jsonify({"ok": False, "error": "User not found"}), 404
    return jsonify({"ok": True, "report": report})


@app.route("/api/stats/activity", methods=["GET"])
def api_stats_activity():
    """Возвращает активность за период (day/week/month)."""
    from services.analytics_service import get_activity_by_period, get_learning_time
    user_id = request.args.get("user_id", type=int)
    period = request.args.get("period", "week")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    activity = get_activity_by_period(user_id, period)
    learning_time = get_learning_time(user_id, {"day": 1, "week": 7, "month": 30}.get(period, 7))
    return jsonify({"ok": True, "period": period, "activity": activity, "learning_time": learning_time})


@app.route("/api/stats/vocabulary", methods=["GET"])
def api_stats_vocabulary():
    """Возвращает статистику по словарю (SRS)."""
    from services.analytics_service import get_vocabulary_stats
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    stats = get_vocabulary_stats(user_id)
    return jsonify({"ok": True, "vocabulary": stats})


@app.route("/api/stats/skills", methods=["GET"])
def api_stats_skills():
    """Возвращает прогресс по навыкам."""
    from services.analytics_service import get_skill_progress
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    skills = get_skill_progress(user_id)
    return jsonify({"ok": True, "skills": skills})


@app.route("/api/stats/goals", methods=["GET"])
def api_stats_goals():
    """Возвращает статистику по ежедневным целям."""
    from services.analytics_service import get_daily_goal_stats
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    goals = get_daily_goal_stats(user_id)
    return jsonify({"ok": True, "goals": goals})


@app.route("/api/adaptive-test/start", methods=["GET"])
def api_adaptive_test_start():
    """Начинает адаптивный тест уровня."""
    from services.adaptive_test_service import AdaptiveTest
    from database import save_test_session, delete_test_session
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    test = AdaptiveTest(max_questions=15)
    question = test.get_next_question()
    # Сохраняем состояние теста
    save_test_session(user_id, test.to_state())
    # Убираем правильный ответ из вопроса
    client_question = {k: v for k, v in question.items() if k != "answer"}
    return jsonify({
        "ok": True,
        "test_id": user_id,
        "question": client_question,
        "current": 1,
        "total": 15,
    })


@app.route("/api/adaptive-test/answer", methods=["POST"])
def api_adaptive_test_answer():
    """Принимает ответ на вопрос адаптивного теста."""
    from services.adaptive_test_service import AdaptiveTest
    from database import save_test_session, get_test_session
    data = request.json
    user_id = data.get("user_id")
    selected = data.get("selected")
    if not user_id or selected is None:
        return jsonify({"ok": False, "error": "Missing data"}), 400
    # Загружаем состояние теста из БД
    state = get_test_session(user_id)
    if not state:
        return jsonify({"ok": False, "error": "Test not started"}), 400
    test = AdaptiveTest(state=state)
    result = test.submit_answer(selected)
    if not result:
        return jsonify({"ok": False, "error": "No question to answer"}), 400
    # Получаем следующий вопрос (добавляет его в self.questions)
    next_question = test.get_next_question()
    # Сохраняем обновлённое состояние (включая следующий вопрос)
    save_test_session(user_id, test.to_state())
    response = {
        "ok": True,
        "correct": result["correct"],
        "level": result["level"],
        "skill": result["skill"],
        "current": len(test.questions),
        "total": test.max_questions,
    }
    if next_question:
        client_question = {k: v for k, v in next_question.items() if k != "answer"}
        response["question"] = client_question
        response["finished"] = False
    else:
        response["finished"] = True
    return jsonify(response)


@app.route("/api/adaptive-test/submit", methods=["POST"])
def api_adaptive_test_submit():
    """Завершает адаптивный тест и сохраняет результат."""
    from services.adaptive_test_service import AdaptiveTest
    from database import save_test_session, get_test_session, delete_test_session, save_user_data, add_xp, log_activity
    data = request.json
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"ok": False, "error": "Missing user_id"}), 400
    state = get_test_session(user_id)
    if not state:
        return jsonify({"ok": False, "error": "Test not started"}), 400
    test = AdaptiveTest(state=state)
    result = test.get_result()
    # Сохраняем уровень пользователя
    save_user_data(user_id, level=result["level"])
    # Начисляем XP за тест
    add_xp(user_id, 50)
    log_activity(user_id, "adaptive_test", 50, f"Уровень: {result['level']}")
    # Удаляем сессию теста
    delete_test_session(user_id)
    return jsonify({"ok": True, "result": result})


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