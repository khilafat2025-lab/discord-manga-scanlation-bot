"""
Cog 5: Help & Info
===================
Slash commands:
  /help     — interactive help menu with category buttons
  /about    — bot info, version, stats
  /ping     — latency check
"""

import logging
import platform

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import Config

log = logging.getLogger("MangaBot.Help")
cfg = Config()


# ── Category Select ───────────────────────────────────────────────────────────

class HelpCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="📖 Manga OCR", value="ocr", description="Scan and translate manga panels"),
            discord.SelectOption(label="🎨 Colorizer", value="color", description="Colorize B&W manga panels"),
            discord.SelectOption(label="📄 File Translator", value="file", description="Translate entire text files"),
            discord.SelectOption(label="🔧 Admin Panel", value="admin", description="Bot administration commands"),
            discord.SelectOption(label="ℹ️ General", value="general", description="General bot commands"),
        ]
        super().__init__(placeholder="📚 Select a category…", options=options)

    async def callback(self, interaction: discord.Interaction):
        embeds = {
            "ocr": _ocr_help(),
            "color": _color_help(),
            "file": _file_help(),
            "admin": _admin_help(),
            "general": _general_help(),
        }
        await interaction.response.edit_message(embed=embeds[self.values[0]])


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpCategorySelect())


# ── Cog ───────────────────────────────────────────────────────────────────────

class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="📚 Show all bot commands and how to use them")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Manga Scanlation Bot — Help",
            description=(
                "Welcome! I'm your **Manga Scanlation & File Processing Assistant**.\n\n"
                "Use the dropdown below to explore commands by category, "
                "or use `/about` for bot info."
            ),
            color=cfg.COLOR_MANGA,
        )
        embed.add_field(
            name="🚀 Quick Start",
            value=(
                "• `/scan_manga` — Upload a manga panel to OCR + translate\n"
                "• `/colorize` — Colorize a B&W manga panel\n"
                "• `/translate_file` — Translate an entire text file\n"
                "• `/translate_text` — Translate a text snippet"
            ),
            inline=False,
        )
        embed.add_field(
            name="🌐 Supported Languages",
            value="Urdu · English · Chinese · Russian · Arabic · French · Spanish · German · Japanese · Korean · Hindi · Turkish",
            inline=False,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Select a category below for detailed command info →")

        await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)

    @app_commands.command(name="about", description="ℹ️ About this bot")
    async def about(self, interaction: discord.Interaction):
        stats = await self.bot.db.get_global_stats()
        uptime = discord.utils.utcnow() - self.bot.start_time
        hours, rem = divmod(int(uptime.total_seconds()), 3600)
        minutes, _ = divmod(rem, 60)

        embed = discord.Embed(
            title="🤖 Manga Scanlation Bot",
            description="Advanced Manga Scanlation & File Processing Assistant for Discord",
            color=cfg.COLOR_MANGA,
        )
        embed.add_field(name="⏱️ Uptime", value=f"{hours}h {minutes}m", inline=True)
        embed.add_field(name="🏠 Guilds", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="👥 Users", value=str(stats["total_users"]), inline=True)
        embed.add_field(name="📨 Requests", value=str(stats["total_requests"]), inline=True)
        embed.add_field(name="🐍 Python", value=platform.python_version(), inline=True)
        embed.add_field(name="📦 discord.py", value=discord.__version__, inline=True)
        embed.add_field(
            name="✨ Features",
            value=(
                "• Manga OCR (EasyOCR + pytesseract)\n"
                "• Auto Colorization (OpenCV DNN)\n"
                "• File Translation (12 languages)\n"
                "• Admin Panel with SQLite logging"
            ),
            inline=False,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Built with discord.py • Use /help for commands")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ping", description="🏓 Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        color = cfg.COLOR_SUCCESS if latency < 100 else cfg.COLOR_WARNING if latency < 200 else cfg.COLOR_ERROR
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**Latency:** `{latency}ms`",
            color=color,
        )
        await interaction.response.send_message(embed=embed)


# ── Help page builders ────────────────────────────────────────────────────────

def _ocr_help() -> discord.Embed:
    e = discord.Embed(title="📖 Manga OCR Commands", color=cfg.COLOR_INFO)
    e.add_field(
        name="/scan_manga",
        value=(
            "Upload a manga panel image → extract text via OCR → translate it.\n"
            "**Options:**\n"
            "• `image` — the manga panel (PNG/JPG/WEBP)\n"
            "• `target_language` — language code (e.g. `ur`, `en`, `zh-cn`)\n"
            "• `preprocess` — enhance image for better OCR (default: True)\n\n"
            "If no language is specified, a dropdown menu appears."
        ),
        inline=False,
    )
    e.add_field(
        name="/detect_text",
        value="OCR only — extract text without translating.",
        inline=False,
    )
    return e


def _color_help() -> discord.Embed:
    e = discord.Embed(title="🎨 Colorizer Commands", color=cfg.COLOR_INFO)
    e.add_field(
        name="/colorize",
        value=(
            "Upload a B&W manga panel → get a colorized version.\n"
            "**Styles:** `warm` · `cool` · `vivid` · `sepia`\n"
            "After colorizing, use the style buttons to try other looks."
        ),
        inline=False,
    )
    e.add_field(
        name="/colorize_help",
        value="Detailed explanation of how colorization works.",
        inline=False,
    )
    return e


def _file_help() -> discord.Embed:
    e = discord.Embed(title="📄 File Translator Commands", color=cfg.COLOR_INFO)
    e.add_field(
        name="/translate_file",
        value=(
            "Upload a text file → translate it line-by-line → download result.\n"
            "**Supported formats:** `.txt` `.md` `.srt` `.csv` `.log` `.rst`\n"
            "**Max:** 500 lines, 10MB"
        ),
        inline=False,
    )
    e.add_field(
        name="/translate_text",
        value="Translate a text snippet (up to 2000 chars) directly in Discord.",
        inline=False,
    )
    e.add_field(
        name="/languages",
        value="List all 12 supported language codes.",
        inline=False,
    )
    return e


def _admin_help() -> discord.Embed:
    e = discord.Embed(title="🔧 Admin Commands", color=cfg.COLOR_WARNING)
    e.description = "All `/admin` commands require **Administrator** permission or bot owner status."
    e.add_field(name="/admin stats", value="Global bot statistics (2-page paginated)", inline=False)
    e.add_field(name="/admin ban <user>", value="Ban a user from using the bot", inline=False)
    e.add_field(name="/admin unban <user_id>", value="Unban a user", inline=False)
    e.add_field(name="/admin premium <user> <grant>", value="Grant/revoke premium status", inline=False)
    e.add_field(name="/admin broadcast <message>", value="Send announcement to all guilds", inline=False)
    e.add_field(name="/admin logs", value="View recent audit logs", inline=False)
    e.add_field(name="/admin recent", value="View recent bot requests", inline=False)
    e.add_field(name="/admin reload <cog>", value="Reload a cog without restarting", inline=False)
    e.add_field(name="/admin sync", value="Sync slash commands globally", inline=False)
    e.add_field(name="/admin shutdown", value="Gracefully shut down the bot", inline=False)
    return e


def _general_help() -> discord.Embed:
    e = discord.Embed(title="ℹ️ General Commands", color=cfg.COLOR_INFO)
    e.add_field(name="/help", value="Show this help menu", inline=False)
    e.add_field(name="/about", value="Bot info, version, and statistics", inline=False)
    e.add_field(name="/ping", value="Check bot latency", inline=False)
    e.add_field(name="/languages", value="List all supported translation languages", inline=False)
    return e


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
