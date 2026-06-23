"""
utils/translator.py
-------------------
Translation pipeline with provider priority:
  1. Google Gemini API (via GOOGLE_API_KEY — AI Studio key, works!)
  2. googletrans (free, no key needed)
  3. OpenAI GPT-3.5 (via OPENAI_API_KEY)
  4. MyMemory (free REST fallback)
"""

import asyncio
import logging
import json
import base64
import ssl
import urllib.request
import urllib.parse
from typing import Optional

logger = logging.getLogger(__name__)

# ── Language map ──────────────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "ur": "Urdu",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ar": "Arabic",
    "hi": "Hindi",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "ru": "Russian",
    "tr": "Turkish",
    "fa": "Persian",
    "pt": "Portuguese",
    "it": "Italian",
}

LANGUAGE_NAMES = {v.lower(): k for k, v in SUPPORTED_LANGUAGES.items()}

# ── Config ────────────────────────────────────────────────────────────────────
try:
    from utils.config import Config
    GOOGLE_API_KEY = Config.GOOGLE_API_KEY
    OPENAI_API_KEY = Config.OPENAI_API_KEY
except Exception:
    import os
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

_ssl_ctx = ssl.create_default_context()

# ── Provider detection ────────────────────────────────────────────────────────
def get_active_provider() -> str:
    if GOOGLE_API_KEY:
        return "Google Gemini (AI Studio) ✅"
    try:
        import googletrans  # noqa
        return "googletrans (free)"
    except ImportError:
        pass
    if OPENAI_API_KEY:
        return "OpenAI GPT-3.5"
    return "MyMemory (free REST)"


# ── Provider 1: Gemini translation ───────────────────────────────────────────
async def _translate_gemini(text: str, target_lang: str) -> Optional[str]:
    """Use Gemini 2.5 Flash to translate text."""
    if not GOOGLE_API_KEY:
        return None
    lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
    prompt = (
        f"Translate the following text to {lang_name}. "
        f"Return ONLY the translated text, no explanations, no quotes.\n\n"
        f"Text to translate:\n{text}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-2.5-flash:generateContent?key={GOOGLE_API_KEY}"
    )
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        loop = asyncio.get_event_loop()
        def _call():
            with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx) as r:
                return json.loads(r.read())
        data = await loop.run_in_executor(None, _call)
        result = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        logger.info("Gemini translation succeeded")
        return result
    except Exception as e:
        logger.warning(f"Gemini translation failed: {e}")
        return None


# ── Provider 2: googletrans ───────────────────────────────────────────────────
async def _translate_googletrans(text: str, target_lang: str) -> Optional[str]:
    try:
        from googletrans import Translator
        translator = Translator()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: translator.translate(text, dest=target_lang)
        )
        logger.info("googletrans translation succeeded")
        return result.text
    except Exception as e:
        logger.warning(f"googletrans failed: {e}")
        return None


# ── Provider 3: OpenAI ────────────────────────────────────────────────────────
async def _translate_openai(text: str, target_lang: str) -> Optional[str]:
    if not OPENAI_API_KEY:
        return None
    lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": f"Translate to {lang_name}. Return only the translation."},
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": 1024,
                },
            )
            data = resp.json()
            result = data["choices"][0]["message"]["content"].strip()
            logger.info("OpenAI translation succeeded")
            return result
    except Exception as e:
        logger.warning(f"OpenAI translation failed: {e}")
        return None


# ── Provider 4: MyMemory ──────────────────────────────────────────────────────
async def _translate_mymemory(text: str, target_lang: str) -> Optional[str]:
    try:
        encoded = urllib.parse.quote(text[:500])
        url = f"https://api.mymemory.translated.net/get?q={encoded}&langpair=auto|{target_lang}"
        loop = asyncio.get_event_loop()
        def _call():
            req = urllib.request.Request(url, headers={"User-Agent": "MangaBot/2.0"})
            with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx) as r:
                return json.loads(r.read())
        data = await loop.run_in_executor(None, _call)
        result = data.get("responseData", {}).get("translatedText", "")
        if result and result.upper() != text.upper():
            logger.info("MyMemory translation succeeded")
            return result
        return None
    except Exception as e:
        logger.warning(f"MyMemory failed: {e}")
        return None


# ── Public API ────────────────────────────────────────────────────────────────
async def translate_text(text: str, target_lang: str = "ur") -> str:
    """
    Translate text using the best available provider.
    Priority: Gemini → googletrans → OpenAI → MyMemory
    """
    if not text or not text.strip():
        return ""

    # Normalise lang code
    target_lang = target_lang.lower().strip()
    if target_lang not in SUPPORTED_LANGUAGES:
        # Try name lookup
        target_lang = LANGUAGE_NAMES.get(target_lang, "ur")

    for provider in [
        _translate_gemini,
        _translate_googletrans,
        _translate_openai,
        _translate_mymemory,
    ]:
        result = await provider(text, target_lang)
        if result:
            return result

    return f"[Translation unavailable] {text}"


async def translate_lines(lines: list[str], target_lang: str = "ur") -> list[str]:
    """Translate a list of lines, preserving empty lines."""
    results = []
    for line in lines:
        if line.strip():
            translated = await translate_text(line, target_lang)
            results.append(translated)
        else:
            results.append("")
    return results


def get_language_name(code: str) -> str:
    return SUPPORTED_LANGUAGES.get(code.lower(), code)
