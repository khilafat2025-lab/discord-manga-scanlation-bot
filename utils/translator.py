"""
Async translation utility.
Primary:  googletrans (free, no key needed)
Fallback: OpenAI GPT (if OPENAI_API_KEY is set)
"""

import asyncio
import logging
import os
from typing import Optional

log = logging.getLogger("MangaBot.Translator")


async def translate_text(
    text: str,
    target_lang: str = "ur",
    source_lang: str = "auto",
) -> str:
    """
    Translate `text` to `target_lang`.
    Returns translated string or raises RuntimeError on failure.
    """
    if not text or not text.strip():
        return ""

    # ── Attempt 1: googletrans ────────────────────────────────────────────────
    try:
        result = await _googletrans_translate(text, target_lang, source_lang)
        if result:
            return result
    except Exception as exc:
        log.warning(f"googletrans failed: {exc}")

    # ── Attempt 2: OpenAI GPT ─────────────────────────────────────────────────
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        try:
            result = await _openai_translate(text, target_lang, openai_key)
            if result:
                return result
        except Exception as exc:
            log.warning(f"OpenAI translation failed: {exc}")

    # ── Attempt 3: MyMemory free API ──────────────────────────────────────────
    try:
        result = await _mymemory_translate(text, target_lang, source_lang)
        if result:
            return result
    except Exception as exc:
        log.warning(f"MyMemory failed: {exc}")

    raise RuntimeError("All translation backends failed. Please try again later.")


async def translate_lines(
    lines: list[str],
    target_lang: str = "ur",
    source_lang: str = "auto",
    batch_size: int = 20,
) -> list[str]:
    """Translate a list of lines, batching to avoid rate limits."""
    translated = []
    for i in range(0, len(lines), batch_size):
        batch = lines[i : i + batch_size]
        joined = "\n".join(batch)
        try:
            result = await translate_text(joined, target_lang, source_lang)
            translated.extend(result.split("\n"))
        except Exception as exc:
            log.error(f"Batch translation error: {exc}")
            translated.extend(batch)  # fallback: keep original
        await asyncio.sleep(0.3)  # be polite to free APIs
    return translated


# ── Backend implementations ───────────────────────────────────────────────────

async def _googletrans_translate(text: str, target: str, source: str) -> Optional[str]:
    from googletrans import Translator
    loop = asyncio.get_event_loop()

    def _sync():
        t = Translator()
        result = t.translate(text, dest=target, src=source if source != "auto" else "auto")
        return result.text

    return await loop.run_in_executor(None, _sync)


async def _openai_translate(text: str, target: str, api_key: str) -> Optional[str]:
    import httpx

    lang_names = {
        "ur": "Urdu", "en": "English", "zh-cn": "Chinese (Simplified)",
        "ru": "Russian", "ar": "Arabic", "fr": "French", "es": "Spanish",
        "de": "German", "ja": "Japanese", "ko": "Korean", "hi": "Hindi",
        "tr": "Turkish",
    }
    lang_name = lang_names.get(target, target)

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": f"You are a professional translator. Translate the following text to {lang_name}. Return ONLY the translated text, nothing else."},
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


async def _mymemory_translate(text: str, target: str, source: str) -> Optional[str]:
    import httpx

    # MyMemory has a 500-char limit per request
    if len(text) > 500:
        text = text[:500]

    src = source if source != "auto" else "en"
    params = {"q": text, "langpair": f"{src}|{target}"}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get("https://api.mymemory.translated.net/get", params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("responseStatus") == 200:
            return data["responseData"]["translatedText"]
    return None
