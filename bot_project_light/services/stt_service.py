import aiohttp
import base64
import logging
from config import HF_TOKEN, HF_WHISPER_MODEL, REPLICATE_API_KEY

logger = logging.getLogger(__name__)

HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_WHISPER_MODEL}"
REPLICATE_URL = "https://api.replicate.com/v1/predictions"

async def transcribe_audio(audio_bytes: bytes) -> str:
    """Распознавание речи: пробует HuggingFace, затем Replicate"""
    
    # Попытка 1: HuggingFace
    if HF_TOKEN:
        result = await _transcribe_hf(audio_bytes)
        if result and not result.startswith("❌") and not result.startswith("⏳"):
            return result

    # Попытка 2: Replicate (доступен из РФ)
    if REPLICATE_API_KEY:
        result = await _transcribe_replicate(audio_bytes)
        if result:
            return result

    return "❌ Speech-to-Text unavailable. Configure REPLICATE_API_KEY in config.py"

async def _transcribe_hf(audio_bytes: bytes) -> str:
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "audio/ogg"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(HF_API_URL, headers=headers, data=audio_bytes, timeout=30) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("text", "")
                elif resp.status == 503:
                    return "⏳ Model is loading. Please try again in a few seconds."
                else:
                    return None
    except aiohttp.ClientError as e:
        logger.error(f"HuggingFace STT error: {e}")
        return None
    except Exception as e:
        logger.error(f"HuggingFace STT unexpected error: {e}")
        return None

async def _transcribe_replicate(audio_bytes: bytes) -> str:
    """Использует Replicate API с моделью openai/whisper"""
    # Кодируем аудио в base64
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    data_url = f"data:audio/ogg;base64,{audio_b64}"

    headers = {
        "Authorization": f"Bearer {REPLICATE_API_KEY}",
        "Content-Type": "application/json",
        "Prefer": "wait"
    }
    payload = {
        "version": "4d501566e989e1e5e5d8f0d892adf06e2a9b3b22",
        "input": {
            "audio": data_url,
            "model": "large-v3",
            "language": "en"
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Запускаем предсказание
            async with session.post(REPLICATE_URL, headers=headers, json=payload, timeout=60) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    # Ждём результат
                    if data.get("output"):
                        return " ".join(data["output"]) if isinstance(data["output"], list) else data["output"]
                    elif data.get("status") == "processing":
                        # Пробуем получить результат по URL
                        get_url = data.get("urls", {}).get("get")
                        if get_url:
                            import asyncio
                            for _ in range(10):
                                await asyncio.sleep(2)
                                async with session.get(get_url, headers=headers) as get_resp:
                                    if get_resp.status == 200:
                                        result = await get_resp.json()
                                        if result.get("output"):
                                            return " ".join(result["output"]) if isinstance(result["output"], list) else result["output"]
                                        if result.get("status") == "failed":
                                            break
                    return None
                else:
                    return None
    except aiohttp.ClientError as e:
        logger.error(f"Replicate STT error: {e}")
        return None
    except Exception as e:
        logger.error(f"Replicate STT unexpected error: {e}")
        return None


