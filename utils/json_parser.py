import json
import re
import logging

logger = logging.getLogger(__name__)


def extract_json(text):
    """Извлекает JSON из ответа LLM. Возвращает dict/list или None."""
    if not text:
        return None
    text = text.strip()
    # Убираем markdown-обёртки
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Пробуем найти JSON в тексте
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                # Очищаем trailing commas и пробуем снова
                cleaned = re.sub(r',\s*([}\]])', r'\1', match.group(0))
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    return None
    return None


def parse_groq_response(text):
    """Парсит ответ LLM: пытается извлечь JSON, если не выходит — возвращает текст."""
    if not text:
        return None, text

    # Сначала пробуем найти JSON в ответе
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return data, None
        except json.JSONDecodeError:
            logger.warning(f"JSON parse failed: {json_match.group()[:100]}...")
            pass

    return None, text


def extract_corrections_and_response(text):
    """
    Извлекает из текстового ответа LLM:
    - corrections: список dict {"original": ..., "corrected": ...}
    - reply: строка с ответом

    Устойчиво к markdown-обёрткам (```json ... ```), trailing commas и т.п.
    """
    corrections = []
    response = None

    if not text or not text.strip():
        return [], ""

    # --- 1. Пытаемся извлечь JSON-блок целиком ---
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        json_str = json_match.group()
        try:
            data = json.loads(json_str)
            corrections = data.get("corrections", [])
            if not isinstance(corrections, list):
                corrections = []
            response = data.get("reply", data.get("response", ""))
            if response:
                response = response.strip()
            return corrections, response
        except json.JSONDecodeError:
            # Очищаем trailing commas и пробуем снова
            cleaned = re.sub(r',\s*([}\]])', r'\1', json_str)
            try:
                data = json.loads(cleaned)
                corrections = data.get("corrections", [])
                if not isinstance(corrections, list):
                    corrections = []
                response = data.get("reply", data.get("response", ""))
                if response:
                    response = response.strip()
                return corrections, response
            except json.JSONDecodeError:
                logger.warning(f"JSON parse failed after cleaning: {cleaned[:100]}...")

    # --- 2. Fallback: извлекаем поля по regex по отдельности ---
    # corrections
    corr_match = re.search(r'"corrections"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    if corr_match:
        corr_text = corr_match.group(1)
        # пробуем извлечь original/corrected парами
        items = re.findall(
            r'\{\s*"original"\s*:\s*"(.*?)"\s*,\s*"corrected"\s*:\s*"(.*?)"\s*\}',
            corr_text,
            re.DOTALL,
        )
        if items:
            corrections = [{"original": orig, "corrected": corr} for orig, corr in items]
        else:
            # fallback: отдельные поля (менее точно)
            origs = re.findall(r'"original"\s*:\s*"([^"]*)"', corr_text, re.DOTALL)
            corrs = re.findall(r'"corrected"\s*:\s*"([^"]*)"', corr_text, re.DOTALL)
            if origs and corrs and len(origs) == len(corrs):
                corrections = [{"original": o, "corrected": c} for o, c in zip(origs, corrs)]

    # reply
    resp_match = re.search(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
    if resp_match:
        response = resp_match.group(1).strip()
    else:
        resp_match = re.search(r'"response"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
        if resp_match:
            response = resp_match.group(1).strip()
        else:
            response = text.strip()

    return corrections, response


def format_corrections_and_response(original_text, corrections, response_text):
    """
    Формирует HTML-сообщение с исправлениями и ответом.
    Возвращает (html_message, parse_mode).
    """
    if not corrections:
        return f"<b>💬 Ответ:</b> {response_text}", None

    corrected_text = original_text
    for corr in corrections:
        orig = corr.get("original", "").strip()
        corr_word = corr.get("corrected", "").strip()
        if orig and corr_word:
            pattern = re.compile(r'\b' + re.escape(orig) + r'\b', re.IGNORECASE)
            replacement = f"<s>{orig}</s> <b>{corr_word}</b>"
            corrected_text = pattern.sub(replacement, corrected_text)

    html_message = (
        f"<b>📝 Исправленный текст:</b>\n{corrected_text}\n\n"
        f"<b>💬 Ответ:</b> {response_text}"
    )
    return html_message, "HTML"
