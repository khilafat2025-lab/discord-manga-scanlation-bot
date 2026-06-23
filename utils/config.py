"""
Configuration manager — reads all env vars in one place.
"""

import os
from typing import List


class Config:
    """Central config object populated from environment variables."""

    # ── Discord ───────────────────────────────────────────────────────────────
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    OWNER_IDS: List[int] = [
        int(x.strip())
        for x in os.getenv("OWNER_IDS", "").split(",")
        if x.strip().isdigit()
    ]
    LOG_CHANNEL_ID: int = int(os.getenv("LOG_CHANNEL_ID", "0")) or None
    TEST_GUILD_ID: int = int(os.getenv("TEST_GUILD_ID", "0")) or None

    # ── AI / Translation ──────────────────────────────────────────────────────
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEEPL_API_KEY: str = os.getenv("DEEPL_API_KEY", "")

    # ── Rate limits ───────────────────────────────────────────────────────────
    OCR_COOLDOWN_SECONDS: int = int(os.getenv("OCR_COOLDOWN_SECONDS", "10"))
    TRANSLATE_COOLDOWN_SECONDS: int = int(os.getenv("TRANSLATE_COOLDOWN_SECONDS", "5"))
    COLORIZE_COOLDOWN_SECONDS: int = int(os.getenv("COLORIZE_COOLDOWN_SECONDS", "30"))

    # ── Limits ────────────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

    # ── Supported languages ───────────────────────────────────────────────────
    LANGUAGES = {
        "ur": "🇵🇰 Urdu",
        "en": "🇬🇧 English",
        "zh-cn": "🇨🇳 Chinese (Simplified)",
        "ru": "🇷🇺 Russian",
        "ar": "🇸🇦 Arabic",
        "fr": "🇫🇷 French",
        "es": "🇪🇸 Spanish",
        "de": "🇩🇪 German",
        "ja": "🇯🇵 Japanese",
        "ko": "🇰🇷 Korean",
        "hi": "🇮🇳 Hindi",
        "tr": "🇹🇷 Turkish",
    }

    # ── Colours (Discord embed hex) ───────────────────────────────────────────
    COLOR_PRIMARY = 0x5865F2    # Discord blurple
    COLOR_SUCCESS = 0x57F287    # Green
    COLOR_WARNING = 0xFEE75C    # Yellow
    COLOR_ERROR   = 0xED4245    # Red
    COLOR_INFO    = 0x5DADE2    # Blue
    COLOR_MANGA   = 0x2C3E50    # Dark slate (manga theme)
