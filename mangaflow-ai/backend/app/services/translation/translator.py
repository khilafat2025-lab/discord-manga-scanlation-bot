"""
MangaFlow AI - AI Translation Service
OpenAI GPT-4o + Gemini + LibreTranslate fallback
Context memory + Glossary enforcement
"""
import asyncio
import logging
from typing import List, Dict, Optional
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert manga/comic translator.
Rules:
1. Produce NATURAL translations, not literal word-for-word
2. Maintain character personalities and speech patterns
3. Preserve honorifics if requested (san, kun, chan, sama, sensei)
4. Keep sound effects (SFX) in style (BOOM, CRASH, etc.)
5. Maintain consistent character names from the glossary
6. Consider context from previous bubbles for continuity
7. Keep translations concise to fit speech bubbles
8. Return ONLY the translated text, no explanations
Output format: Return a JSON array of translated strings in the same order as input."""


class TranslationService:
    def __init__(self):
        self._context_window: List[Dict] = []
        self._max_context = 20

    async def translate_bubbles(self, bubbles, source_lang, target_lang, glossary=None, maintain_honorifics=True, page_number=0):
        texts = [b.get("original_text", "").strip() for b in bubbles]
        texts_to_translate = [t for t in texts if t]
        if not texts_to_translate:
            return bubbles
        context = self._build_context(glossary, maintain_honorifics, page_number)
        translations = await self._translate_batch(texts_to_translate, source_lang, target_lang, context)
        trans_idx = 0
        for bubble in bubbles:
            if bubble.get("original_text", "").strip():
                if trans_idx < len(translations):
                    bubble["translated_text"] = translations[trans_idx]
                    self._context_window.append({"original": bubble["original_text"], "translated": translations[trans_idx]})
                    if len(self._context_window) > self._max_context:
                        self._context_window.pop(0)
                trans_idx += 1
        return bubbles

    def _build_context(self, glossary, maintain_honorifics, page_number):
        parts = [f"Page: {page_number}"]
        if glossary:
            glossary_str = "\n".join(f"  {k} -> {v}" for k, v in list(glossary.items())[:20])
            parts.append(f"Glossary:\n{glossary_str}")
        if maintain_honorifics:
            parts.append("Preserve Japanese honorifics (san, kun, chan, sama, sensei, senpai)")
        if self._context_window:
            recent = self._context_window[-5:]
            ctx_str = "\n".join(f"  [{r['original']}] -> [{r['translated']}]" for r in recent)
            parts.append(f"Recent context:\n{ctx_str}")
        return "\n".join(parts)

    async def _translate_batch(self, texts, source_lang, target_lang, context):
        if settings.OPENAI_API_KEY:
            try:
                return await self._openai_translate(texts, source_lang, target_lang, context)
            except Exception as e:
                logger.warning(f"OpenAI failed: {e}")
        if settings.GEMINI_API_KEY:
            try:
                return await self._gemini_translate(texts, source_lang, target_lang, context)
            except Exception as e:
                logger.warning(f"Gemini failed: {e}")
        try:
            return await self._libre_translate(texts, source_lang, target_lang)
        except Exception as e:
            logger.warning(f"LibreTranslate failed: {e}")
        return texts

    async def _openai_translate(self, texts, source_lang, target_lang, context):
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        lang_names = {"ja": "Japanese", "zh": "Chinese", "ko": "Korean", "en": "English", "fr": "French", "de": "German", "es": "Spanish", "it": "Italian", "pt": "Portuguese", "ru": "Russian", "ar": "Arabic", "tr": "Turkish", "id": "Indonesian", "hi": "Hindi", "ur": "Urdu"}
        src_name = lang_names.get(source_lang, source_lang)
        tgt_name = lang_names.get(target_lang, target_lang)
        user_message = f"""Translate from {src_name} to {tgt_name}.\nContext:\n{context}\nTexts:\n{json.dumps(texts, ensure_ascii=False)}\nReturn ONLY a JSON array."""
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_message}],
            temperature=0.3, max_tokens=2000, response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        if isinstance(data, list):
            return data
        for key in ("translations", "translated", "results", "output"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return texts

    async def _gemini_translate(self, texts, source_lang, target_lang, context):
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        prompt = f"{SYSTEM_PROMPT}\nContext: {context}\nTranslate from {source_lang} to {target_lang}:\n{json.dumps(texts, ensure_ascii=False)}\nReturn ONLY a JSON array."
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        data = json.loads(text)
        return data if isinstance(data, list) else texts

    async def _libre_translate(self, texts, source_lang, target_lang):
        import httpx
        results = []
        async with httpx.AsyncClient(timeout=30) as client:
            for text in texts:
                try:
                    resp = await client.post("https://libretranslate.com/translate",
                        json={"q": text, "source": source_lang, "target": target_lang, "format": "text"})
                    results.append(resp.json().get("translatedText", text))
                except Exception:
                    results.append(text)
        return results
