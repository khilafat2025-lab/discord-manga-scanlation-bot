"""
Cog 1: Manga OCR + Translation
================================
Slash commands:
  /scan_manga  — upload a manga panel → OCR → translate → embed result
  /detect_text — OCR only, no translation

Features:
  - EasyOCR with pytesseract fallback
  - Language selection via Discord Select Menu
  - Paginated results for long text
  - Rate limiting per user
  - Full audit logging
"""

import io
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import Config
from utils.image_processor import extract_text_from_image, validate_image, preprocess_for_ocr
from utils.translator import translate_text

log = logging.getLogger("MangaBot.MangaOCR")
cfg = Config()


# ── Language Select Menu ──────────────────────────────────────────────────────

class LanguageSelect(discord.ui.Select):
    def __init__(self, image_bytes: bytes, extracted_text: str):
        self.image_bytes = image_bytes
        self.extracted_text = extracted_text

        options = [
            discord.SelectOption(label=name, value=code, emoji=name.split()[0])
            for code, name in cfg.LANGUAGES.items()
        ][:25]  # Discord limit

        super().__init__(
            placeholder="🌐 Choose translation language…",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        target_lang = self.values[0]
        lang_name = cfg.LANGUAGES.get(target_lang, target_lang)

        try:
            translated = await translate_text(self.extracted_text, target_lang)
        except Exception as exc:
            await interaction.followup.send(
                embed=_error_embed(f"Translation failed: {exc}"), ephemeral=True
            )
            return

        embed = _result_embed(
            original=self.extracted_text,
            translated=translated,
            lang_name=lang_name,
            user=interaction.user,
        )
        await interaction.followup.send(embed=embed)

        # Log to DB
        bot = interaction.client
        await bot.db.log_request(
            interaction.user.id, "manga_ocr",
            guild_id=interaction.guild_id if interaction.guild else None,
            details=f"lang={target_lang}",
        )


class LanguageSelectView(discord.ui.View):
    def __init__(self, image_bytes: bytes, extracted_text: str):
        super().__init__(timeout=120)
        self.add_item(LanguageSelect(image_bytes, extracted_text))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# ── Pagination View ───────────────────────────────────────────────────────────

class PaginatedTextView(discord.ui.View):
    """Paginate long translated text across multiple embeds."""

    def __init__(self, pages: list[str], title: str, color: int):
        super().__init__(timeout=180)
        self.pages = pages
        self.title = title
        self.color = color
        self.current = 0
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.current == 0
        self.next_btn.disabled = self.current >= len(self.pages) - 1

    def _make_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.title,
            description=self.pages[self.current],
            color=self.color,
        )
        embed.set_footer(text=f"Page {self.current + 1} / {len(self.pages)}")
        return embed

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self._make_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self._make_embed(), view=self)


# ── Cog ───────────────────────────────────────────────────────────────────────

class MangaOCRCog(commands.Cog, name="Manga OCR"):
    """OCR and translation for manga panels."""

    def __init__(self, bot):
        self.bot = bot

    # ── /scan_manga ───────────────────────────────────────────────────────────
    @app_commands.command(
        name="scan_manga",
        description="📖 Upload a manga panel → extract text → translate it",
    )
    @app_commands.describe(
        image="The manga panel image (PNG/JPG/WEBP)",
        target_language="Target language code (e.g. ur, en, zh-cn, ru). Leave blank to choose via menu.",
        preprocess="Enhance image for better OCR accuracy (default: True)",
    )
    @app_commands.checks.cooldown(1, cfg.OCR_COOLDOWN_SECONDS, key=lambda i: i.user.id)
    async def scan_manga(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        target_language: Optional[str] = None,
        preprocess: Optional[bool] = True,
    ):
        await interaction.response.defer(thinking=True)

        # ── Validate ──────────────────────────────────────────────────────────
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.followup.send(
                embed=_error_embed("Please upload a valid image file (PNG, JPG, WEBP)."),
                ephemeral=True,
            )
            return

        if image.size > cfg.MAX_FILE_SIZE_BYTES:
            await interaction.followup.send(
                embed=_error_embed(f"Image too large. Max size: {cfg.MAX_FILE_SIZE_MB}MB."),
                ephemeral=True,
            )
            return

        # ── Check ban ─────────────────────────────────────────────────────────
        if await self.bot.db.is_banned(interaction.user.id):
            await interaction.followup.send(
                embed=_error_embed("You are banned from using this bot."), ephemeral=True
            )
            return

        # ── Download image ────────────────────────────────────────────────────
        image_bytes = await image.read()
        valid, err = validate_image(image_bytes)
        if not valid:
            await interaction.followup.send(embed=_error_embed(err), ephemeral=True)
            return

        # ── Preprocess ────────────────────────────────────────────────────────
        if preprocess:
            try:
                image_bytes = preprocess_for_ocr(image_bytes)
            except Exception as exc:
                log.warning(f"Preprocess failed: {exc}")

        # ── OCR ───────────────────────────────────────────────────────────────
        await interaction.followup.send(
            embed=discord.Embed(
                description="🔍 Scanning image for text…",
                color=cfg.COLOR_INFO,
            )
        )

        extracted_text, detected_lang = await extract_text_from_image(image_bytes)

        if not extracted_text.strip():
            await interaction.edit_original_response(
                embed=_error_embed(
                    "No text detected in this image.\n"
                    "Tips: ensure the image is clear, high-contrast, and contains readable text."
                )
            )
            return

        # ── Translate or show language picker ─────────────────────────────────
        if target_language:
            target_language = target_language.lower().strip()
            if target_language not in cfg.LANGUAGES:
                await interaction.edit_original_response(
                    embed=_error_embed(
                        f"Unknown language code `{target_language}`.\n"
                        f"Supported: {', '.join(cfg.LANGUAGES.keys())}"
                    )
                )
                return

            try:
                translated = await translate_text(extracted_text, target_language)
            except Exception as exc:
                await interaction.edit_original_response(
                    embed=_error_embed(f"Translation failed: {exc}")
                )
                return

            lang_name = cfg.LANGUAGES[target_language]
            embed = _result_embed(extracted_text, translated, lang_name, interaction.user)
            await interaction.edit_original_response(embed=embed, view=None)

            await self.bot.db.log_request(
                interaction.user.id, "manga_ocr",
                guild_id=interaction.guild_id if interaction.guild else None,
                details=f"lang={target_language}",
            )

        else:
            # Show language picker
            ocr_embed = discord.Embed(
                title="📖 Text Detected!",
                description=f"```\n{extracted_text[:1500]}\n```",
                color=cfg.COLOR_SUCCESS,
            )
            ocr_embed.add_field(name="Detected Language", value=f"`{detected_lang}`", inline=True)
            ocr_embed.add_field(name="Characters", value=str(len(extracted_text)), inline=True)
            ocr_embed.set_footer(text="Select a language below to translate →")

            view = LanguageSelectView(image_bytes, extracted_text)
            await interaction.edit_original_response(embed=ocr_embed, view=view)

    # ── /detect_text ──────────────────────────────────────────────────────────
    @app_commands.command(
        name="detect_text",
        description="🔍 Extract text from an image (OCR only, no translation)",
    )
    @app_commands.describe(image="Image to extract text from")
    @app_commands.checks.cooldown(1, cfg.OCR_COOLDOWN_SECONDS, key=lambda i: i.user.id)
    async def detect_text(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
    ):
        await interaction.response.defer(thinking=True)

        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.followup.send(
                embed=_error_embed("Please upload a valid image."), ephemeral=True
            )
            return

        image_bytes = await image.read()
        extracted_text, detected_lang = await extract_text_from_image(image_bytes)

        if not extracted_text.strip():
            await interaction.followup.send(
                embed=_error_embed("No text detected in this image.")
            )
            return

        # Paginate if long
        chunks = _chunk_text(extracted_text, 1800)
        if len(chunks) > 1:
            view = PaginatedTextView(
                [f"```\n{c}\n```" for c in chunks],
                title="🔍 Extracted Text",
                color=cfg.COLOR_INFO,
            )
            await interaction.followup.send(embed=view._make_embed(), view=view)
        else:
            embed = discord.Embed(
                title="🔍 Extracted Text",
                description=f"```\n{extracted_text[:1900]}\n```",
                color=cfg.COLOR_INFO,
            )
            embed.add_field(name="Detected Language", value=f"`{detected_lang}`")
            embed.set_footer(text=f"Use /scan_manga to also translate this text")
            await interaction.followup.send(embed=embed)

        await self.bot.db.log_request(
            interaction.user.id, "detect_text",
            guild_id=interaction.guild_id if interaction.guild else None,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _result_embed(
    original: str,
    translated: str,
    lang_name: str,
    user: discord.User,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"✅ Translation Complete → {lang_name}",
        color=cfg.COLOR_SUCCESS,
    )
    embed.add_field(
        name="📝 Original Text",
        value=f"```\n{original[:900]}\n```",
        inline=False,
    )
    embed.add_field(
        name=f"🌐 Translated ({lang_name})",
        value=f"```\n{translated[:900]}\n```",
        inline=False,
    )
    embed.set_footer(
        text=f"Requested by {user.display_name}",
        icon_url=user.display_avatar.url,
    )
    return embed


def _error_embed(message: str) -> discord.Embed:
    return discord.Embed(
        title="❌ Error",
        description=message,
        color=cfg.COLOR_ERROR,
    )


def _chunk_text(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


async def setup(bot):
    await bot.add_cog(MangaOCRCog(bot))
