import aiohttp
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, HF_TOKEN, GROQ_API_KEY, GROQ_MODEL

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
HF_LLM_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


async def call_llm(messages, system_prompt=None):
    """Вызов LLM: пробует Groq, затем DeepSeek, затем HuggingFace"""
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    # 1. Groq (бесплатный, быстрый)
    if GROQ_API_KEY:
        result = await _call_groq(full_messages)
        if result and not result.startswith("❌"):
            return result

    # 2. DeepSeek (fallback)
    if DEEPSEEK_API_KEY:
        result = await _call_deepseek(full_messages)
        if result and not result.startswith("❌"):
            return result

    # 3. HuggingFace (fallback)
    if HF_TOKEN:
        result = await _call_hf_llm(full_messages)
        if result:
            return result

    return "❌ All LLM services unavailable. Configure GROQ_API_KEY or DEEPSEEK_API_KEY."


async def _call_groq(messages):
    """Вызов Groq LLM"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(GROQ_URL, headers=headers, json=payload, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    text = await resp.text()
                    return f"❌ Groq API error ({resp.status}): {text[:200]}"
    except Exception as e:
        return f"❌ Groq error: {e}"

async def _call_deepseek(messages):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    text = await resp.text()
                    return f"❌ DeepSeek API error ({resp.status}): {text[:200]}"
    except Exception as e:
        return f"❌ DeepSeek error: {e}"

async def _call_hf_llm(messages):
    """
    HuggingFace Inference API (текст-в-текст) как fallback.
    Mistral-7B-Instruct через HF Inference API принимает только `inputs` (prompt),
    поэтому мы собираем историю в один prompt.
    """
    import logging
    logger = logging.getLogger(__name__)
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    # Собираем историю в prompt (Mistral-7B через HF Inference API не поддерживает чат-формат напрямую)
    prompt = _messages_to_prompt(messages)
    if not prompt.strip():
        return "❌ HF LLM: empty prompt"

    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 500, "temperature": 0.7, "return_full_text": False},
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(HF_LLM_URL, headers=headers, json=payload, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0].get("generated_text", str(data))
                    return str(data)
                elif resp.status == 503:
                    return "⏳ HF model is loading. Please try again in a few seconds."
                else:
                    text = await resp.text()
                    return f"❌ HF LLM error ({resp.status}): {text[:200]}"
    except aiohttp.ClientError as e:
        logger.error(f"HF LLM network error: {e}")
        return "❌ HF LLM: network error"
    except Exception as e:
        logger.error(f"HF LLM unexpected error: {e}")
        return f"❌ HF LLM error: {e}"


def _messages_to_prompt(messages):
    """Преобразует список сообщений в prompt для text-generation моделей."""
    parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"[SYSTEM] {content}")
        elif role == "user":
            parts.append(f"[USER] {content}")
        elif role == "assistant":
            parts.append(f"[ASSISTANT] {content}")
        else:
            parts.append(content)
    return "\n".join(parts)

async def analyze_and_correct(text, history, level):
    """Анализ текста с исправлением ошибок через LLM"""
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
        {"role": "user", "content": text}
    ]

    return await call_llm(full_messages)