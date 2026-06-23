"""
Cog 3: Advanced File Translator
=================================
Slash commands:
  /translate_file  — upload .txt/.md/.srt → translate line-by-line → download result
  /translate_text  — translate a text snippet directly in Discord

Features:
  - Async line-by-line translation with progress updates
  - Supports .txt, .md, .srt, .csv (text columns)
  - Language selection via dropdown
  - Progress bar embed updated in real-time
  - Returns translated file as downloadable attachment
  - Preserves original formatting (blank lines, indentation)
"""

import io
import logging
import os
import re
import tempfile
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import Config
from utils.translator import translate_text, translate_lines

log = logging.getLogger("MangaBot.FileTranslator")
cfg = Config()

SUPPORTED_EXTENSIONS = {".txt", ".md", ".srt", ".csv", ".log", ".rst"}
MAX_LINES = 500  # free API limit guard


# ── Language Select for file translation ─────────────────────────────────────

class FileLangSelect(discord.ui.Select):
    def __init__(self, file_bytes: bytes, filename: str, interaction_ref):
        self.file_bytes = file_bytes
        self.filename = filename
        self.interaction_ref = interaction_ref

        options = [
            discord.SelectOption(label=name, value=code, emoji=name.split()[0])
            for code, name in cfg.LANGUAGES.items()
        ][:25]

        super().__init__(
            placeholder="🌐 Select target language…",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        target_lang = self.values[0]
        lang_name = cfg.LANGUAGES.get(target_lang, target_lang)

        await _do_file_translation(interaction, self.file_bytes, self.filename, target_lang, lang_name)


class FileLangView(discord.ui.View):
    def __init__(self, file_bytes: bytes, filename: str, interaction_ref):
        super().__init__(timeout=120)
        self.add_item(FileLangSelect(file_bytes, filename, interaction_ref))


# ── Cog ───────────────────────────────────────────────────────────────────────

class FileTranslatorCog(commands.Cog, name="File Translator"):
    """Translate entire text files into any language."""

    def __init__(self, bot):
        self.bot = bot

    # ── /translate_file ───────────────────────────────────────────────────────
    @app_commands.command(
        name="translate_file",
        description="📄 Upload a text file → translate it → download the result",
    )
    @app_commands.describe(
        file="Text file to translate (.txt, .md, .srt, .csv)",
        target_language="Target language code (e.g. ur, en, zh-cn, ru). Leave blank to choose via menu.",
    )
    @app_commands.checks.cooldown(1, cfg.TRANSLATE_COOLDOWN_SECONDS, key=lambda i: i.user.id)
    async def translate_file(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
        target_language: Optional[str] = None,
    ):
        await interaction.response.defer(thinking=True)

        # ── Validate ──────────────────────────────────────────────────────────
        if await self.bot.db.is_banned(interaction.user.id):
            await interaction.followup.send(
                embed=_error_embed("You are banned from using this bot."), ephemeral=True
            )
            return

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            await interaction.followup.send(
                embed=_error_embed(
                    f"Unsupported file type `{ext}`.\n"
                    f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
                ),
                ephemeral=True,
            )
            return

        if file.size > cfg.MAX_FILE_SIZE_BYTES:
            await interaction.followup.send(
                embed=_error_embed(f"File too large. Max: {cfg.MAX_FILE_SIZE_MB}MB."),
                ephemeral=True,
            )
            return

        # ── Read file ─────────────────────────────────────────────────────────
        file_bytes = await file.read()
        try:
            content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = file_bytes.decode("latin-1")
            except Exception:
                await interaction.followup.send(
                    embed=_error_embed("Could not decode file. Please ensure it's a UTF-8 text file."),
                    ephemeral=True,
                )
                return

        lines = content.splitlines()
        if len(lines) > MAX_LINES:
            await interaction.followup.send(
                embed=_error_embed(
                    f"File has {len(lines)} lines. Maximum is {MAX_LINES} lines per request.\n"
                    "Please split the file into smaller chunks."
                ),
                ephemeral=True,
            )
            return

        if not content.strip():
            await interaction.followup.send(
                embed=_error_embed("The file appears to be empty."), ephemeral=True
            )
            return

        # ── Language selection ────────────────────────────────────────────────
        if target_language:
            target_language = target_language.lower().strip()
            if target_language not in cfg.LANGUAGES:
                await interaction.followup.send(
                    embed=_error_embed(
                        f"Unknown language `{target_language}`.\n"
                        f"Supported: {', '.join(cfg.LANGUAGES.keys())}"
                    ),
                    ephemeral=True,
                )
                return
            lang_name = cfg.LANGUAGES[target_language]
            await _do_file_translation(interaction, file_bytes, file.filename, target_language, lang_name)
        else:
            # Show file info + language picker
            info_embed = discord.Embed(
                title="📄 File Ready for Translation",
                color=cfg.COLOR_INFO,
            )
            info_embed.add_field(name="📁 Filename", value=file.filename, inline=True)
            info_embed.add_field(name="📏 Lines", value=str(len(lines)), inline=True)
            info_embed.add_field(name="📦 Size", value=f"{file.size // 1024}KB", inline=True)
            info_embed.add_field(
                name="👀 Preview (first 3 lines)",
                value=f"```\n{chr(10).join(lines[:3])}\n```",
                inline=False,
            )
            info_embed.set_footer(text="Select a target language below →")

            view = FileLangView(file_bytes, file.filename, interaction)
            await interaction.followup.send(embed=info_embed, view=view)

    # ── /translate_text ───────────────────────────────────────────────────────
    @app_commands.command(
        name="translate_text",
        description="💬 Translate a text snippet into any language",
    )
    @app_commands.describe(
        text="Text to translate (max 2000 characters)",
        target_language="Target language code (e.g. ur, en, zh-cn, ru, ar, fr)",
        source_language="Source language code (default: auto-detect)",
    )
    @app_commands.checks.cooldown(1, cfg.TRANSLATE_COOLDOWN_SECONDS, key=lambda i: i.user.id)
    async def translate_text_cmd(
        self,
        interaction: discord.Interaction,
        text: str,
        target_language: str = "ur",
        source_language: str = "auto",
    ):
        await interaction.response.defer(thinking=True)

        if len(text) > 2000:
            await interaction.followup.send(
                embed=_error_embed("Text too long. Max 2000 characters. Use `/translate_file` for longer content."),
                ephemeral=True,
            )
            return

        target_language = target_language.lower().strip()
        if target_language not in cfg.LANGUAGES:
            await interaction.followup.send(
                embed=_error_embed(f"Unknown language `{target_language}`. Supported: {', '.join(cfg.LANGUAGES.keys())}"),
                ephemeral=True,
            )
            return

        try:
            translated = await translate_text(text, target_language, source_language)
        except Exception as exc:
            await interaction.followup.send(embed=_error_embed(f"Translation failed: {exc}"))
            return

        lang_name = cfg.LANGUAGES[target_language]
        embed = discord.Embed(
            title=f"🌐 Translation → {lang_name}",
            color=cfg.COLOR_SUCCESS,
        )
        embed.add_field(name="📝 Original", value=f"```\n{text[:900]}\n```", inline=False)
        embed.add_field(name=f"✅ {lang_name}", value=f"```\n{translated[:900]}\n```", inline=False)
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.followup.send(embed=embed)

        await self.bot.db.log_request(
            interaction.user.id, "translate_text",
            guild_id=interaction.guild_id if interaction.guild else None,
            details=f"lang={target_language}",
        )

    # ── /languages ────────────────────────────────────────────────────────────
    @app_commands.command(
        name="languages",
        description="🌐 List all supported translation languages",
    )
    async def languages(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🌐 Supported Languages",
            color=cfg.COLOR_INFO,
        )
        lang_list = "\n".join(
            f"`{code}` — {name}" for code, name in cfg.LANGUAGES.items()
        )
        embed.description = lang_list
        embed.set_footer(text="Use the language code in /translate_file or /scan_manga")
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ── Shared translation worker ─────────────────────────────────────────────────

async def _do_file_translation(
    interaction: discord.Interaction,
    file_bytes: bytes,
    filename: str,
    target_lang: str,
    lang_name: str,
):
    """Translate file content and send back as attachment."""
    try:
        content = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = file_bytes.decode("latin-1")

    lines = content.splitlines()
    total = len(lines)

    # Progress embed
    progress_embed = discord.Embed(
        title="⏳ Translating File…",
        description=_progress_bar(0, total),
        color=cfg.COLOR_INFO,
    )
    progress_embed.add_field(name="Target Language", value=lang_name)
    progress_embed.add_field(name="Total Lines", value=str(total))

    try:
        msg = await interaction.followup.send(embed=progress_embed)
    except Exception:
        msg = None

    # Translate in batches with progress updates
    translated_lines = []
    batch_size = 20
    update_every = max(1, total // 5)  # update progress ~5 times

    for i in range(0, total, batch_size):
        batch = lines[i : i + batch_size]
        # Preserve blank lines
        non_empty = [l for l in batch if l.strip()]
        if non_empty:
            try:
                joined = "\n".join(non_empty)
                result = await translate_text(joined, target_lang)
                result_lines = result.split("\n")
                # Re-insert blank lines
                result_iter = iter(result_lines)
                for orig in batch:
                    if orig.strip():
                        translated_lines.append(next(result_iter, orig))
                    else:
                        translated_lines.append("")
            except Exception as exc:
                log.warning(f"Batch {i} translation failed: {exc}")
                translated_lines.extend(batch)
        else:
            translated_lines.extend(batch)

        # Update progress
        if msg and (i % update_every == 0 or i + batch_size >= total):
            progress_embed.description = _progress_bar(min(i + batch_size, total), total)
            try:
                await msg.edit(embed=progress_embed)
            except Exception:
                pass

    # Build output file
    translated_content = "\n".join(translated_lines)
    base, ext = os.path.splitext(filename)
    out_filename = f"{base}_translated_{target_lang}{ext}"
    out_bytes = translated_content.encode("utf-8")

    # Final embed
    done_embed = discord.Embed(
        title="✅ Translation Complete!",
        color=cfg.COLOR_SUCCESS,
    )
    done_embed.add_field(name="📁 Original File", value=filename, inline=True)
    done_embed.add_field(name="🌐 Language", value=lang_name, inline=True)
    done_embed.add_field(name="📏 Lines Translated", value=str(total), inline=True)
    done_embed.add_field(
        name="👀 Preview (first 3 lines)",
        value=f"```\n{chr(10).join(translated_lines[:3])}\n```",
        inline=False,
    )
    done_embed.set_footer(text="Translated file attached below ↓")

    out_file = discord.File(io.BytesIO(out_bytes), filename=out_filename)

    if msg:
        await msg.edit(embed=done_embed, attachments=[out_file])
    else:
        await interaction.followup.send(embed=done_embed, file=out_file)

    # Log
    bot = interaction.client
    await bot.db.log_request(
        interaction.user.id, "translate_file",
        guild_id=interaction.guild_id if interaction.guild else None,
        details=f"lang={target_lang}, lines={total}",
    )


def _progress_bar(current: int, total: int, width: int = 20) -> str:
    if total == 0:
        return "No lines to translate."
    pct = current / total
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"`[{bar}]` {current}/{total} lines ({pct:.0%})"


def _error_embed(message: str) -> discord.Embed:
    return discord.Embed(title="❌ Error", description=message, color=cfg.COLOR_ERROR)


async def setup(bot):
    await bot.add_cog(FileTranslatorCog(bot))
