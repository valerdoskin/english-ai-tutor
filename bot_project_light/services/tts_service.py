"""
tts_service.py — генерация аудио (Text-to-Speech) через edge-tts.
Бесплатно, без ключей, использует Microsoft Edge TTS.
"""
import asyncio
import logging
import os
import uuid

import edge_tts

logger = logging.getLogger(__name__)

# Папка для аудиофайлов
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Голоса для разных уровней (можно настроить)
VOICE = "en-US-JennyNeural"  # женский голос, чёткая речь


def text_to_speech(text, voice=VOICE):
    """Генерирует аудиофайл из текста. Возвращает URL или None."""
    try:
        filename = f"tts_{uuid.uuid4().hex[:12]}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        async def _generate():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(filepath)

        asyncio.run(_generate())

        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return f"/static/audio/{filename}"
        return None
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return None
