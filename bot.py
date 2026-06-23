"""
Discord Manga Scanlation & File Processing Assistant
=====================================================
Main entry point — loads all cogs, sets up logging, connects to Discord.

Environment variables required:
  DISCORD_TOKEN   — your bot token from Discord Developer Portal
  OWNER_IDS       — comma-separated Discord user IDs of bot owners
  GOOGLE_API_KEY  — AI Studio key (aistudio.google.com) for Gemini OCR/Translation/Image Gen
  OPENAI_API_KEY  — (optional) for GPT-powered translation fallback
  LOG_CHANNEL_ID  — (optional) Discord channel ID for audit logs
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.database import Database
from utils.config import Config

# ─── Load environment ────────────────────────────────────────────────────────
load_dotenv()

# ─── Logging setup ───────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("MangaBot")

# Silence noisy third-party loggers
for noisy in ("discord", "httpx", "httpcore", "PIL", "easyocr"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


# ─── Bot class ───────────────────────────────────────────────────────────────
class MangaBot(commands.Bot):
    """Core bot class with database, config, and cog management."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            help_command=None,
            description="Advanced Manga Scanlation & File Processing Assistant",
        )

        self.config = Config()
        self.db: Database = None  # initialised in setup_hook
        self.start_time = discord.utils.utcnow()

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    async def setup_hook(self):
        """Called once before the bot connects — load DB and cogs."""
        # Ensure data/temp dirs exist
        Path("data").mkdir(exist_ok=True)
        Path("temp").mkdir(exist_ok=True)

        # Initialise database
        self.db = Database("data/manga_bot.db")
        await self.db.init()
        log.info("Database initialised ✓")

        # Load all cogs
        cogs = [
            "cogs.manga_ocr",
            "cogs.colorizer",
            "cogs.file_translator",
            "cogs.image_gen",
            "cogs.admin",
            "cogs.help",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                log.info(f"Loaded cog: {cog}")
            except Exception as exc:
                log.error(f"Failed to load cog {cog}: {exc}", exc_info=True)

        # Sync slash commands globally (or to a test guild for instant sync)
        test_guild_id = os.getenv("TEST_GUILD_ID")
        if test_guild_id:
            guild = discord.Object(id=int(test_guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info(f"Slash commands synced to test guild {test_guild_id}")
        else:
            await self.tree.sync()
            log.info("Slash commands synced globally")

    async def on_ready(self):
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        log.info(f"Serving {len(self.guilds)} guild(s)")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="manga panels | /help",
            )
        )

    async def on_guild_join(self, guild: discord.Guild):
        await self.db.register_guild(guild.id, guild.name)
        log.info(f"Joined guild: {guild.name} ({guild.id})")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        log.error(f"Command error in {ctx.command}: {error}", exc_info=True)

    async def on_app_command_error(self, interaction: discord.Interaction, error):
        msg = "An unexpected error occurred. Please try again."
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            msg = f"⏳ Slow down! Try again in **{error.retry_after:.1f}s**."
        elif isinstance(error, discord.app_commands.MissingPermissions):
            msg = "🚫 You don't have permission to use this command."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass
        log.error(f"App command error: {error}", exc_info=True)


# ─── Entry point ─────────────────────────────────────────────────────────────
async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        log.critical("DISCORD_TOKEN environment variable is not set. Exiting.")
        sys.exit(1)

    bot = MangaBot()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())