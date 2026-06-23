"""
Cog 2: Manga Colorization
==========================
Slash commands:
  /colorize  — upload a B&W manga panel → get colorized version back

Features:
  - OpenCV DNN colorization (Zhang et al. model) with PIL fallback
  - Style selection buttons (Warm / Cool / Vivid / Sepia)
  - Before/after comparison embed
  - Rate limiting (colorization is CPU-heavy)
  - Progress indicator
"""

import io
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import Config
from utils.image_processor import colorize_manga_panel, validate_image

log = logging.getLogger("MangaBot.Colorizer")
cfg = Config()


# ── Style Buttons ─────────────────────────────────────────────────────────────

class ColorStyleView(discord.ui.View):
    """Buttons to re-colorize with different style presets."""

    def __init__(self, image_bytes: bytes, original_filename: str):
        super().__init__(timeout=180)
        self.image_bytes = image_bytes
        self.original_filename = original_filename

    async def _recolorize(self, interaction: discord.Interaction, style: str):
        await interaction.response.defer(thinking=True)
        try:
            colored_bytes = await colorize_manga_panel(self.image_bytes, style=style)
            file = discord.File(
                io.BytesIO(colored_bytes),
                filename=f"colorized_{style}_{self.original_filename}.png",
            )
            embed = discord.Embed(
                title=f"🎨 Colorized — {style.title()} Style",
                color=cfg.COLOR_SUCCESS,
            )
            embed.set_image(url=f"attachment://colorized_{style}_{self.original_filename}.png")
            embed.set_footer(text="Use the buttons to try other styles")
            await interaction.followup.send(embed=embed, file=file, view=self)
        except Exception as exc:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Colorization Failed",
                    description=str(exc),
                    color=cfg.COLOR_ERROR,
                ),
                ephemeral=True,
            )

    @discord.ui.button(label="🌅 Warm", style=discord.ButtonStyle.primary)
    async def warm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._recolorize(interaction, "warm")

    @discord.ui.button(label="❄️ Cool", style=discord.ButtonStyle.primary)
    async def cool(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._recolorize(interaction, "cool")

    @discord.ui.button(label="✨ Vivid", style=discord.ButtonStyle.success)
    async def vivid(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._recolorize(interaction, "vivid")

    @discord.ui.button(label="📜 Sepia", style=discord.ButtonStyle.secondary)
    async def sepia(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._recolorize(interaction, "sepia")


# ── Cog ───────────────────────────────────────────────────────────────────────

class ColorizerCog(commands.Cog, name="Colorizer"):
    """Automatic manga panel colorization."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="colorize",
        description="🎨 Colorize a black-and-white manga panel automatically",
    )
    @app_commands.describe(
        image="Black-and-white manga panel (PNG/JPG)",
        style="Color style: warm (default), cool, vivid, sepia",
    )
    @app_commands.choices(style=[
        app_commands.Choice(name="🌅 Warm (default)", value="warm"),
        app_commands.Choice(name="❄️ Cool / Blue tones", value="cool"),
        app_commands.Choice(name="✨ Vivid / Saturated", value="vivid"),
        app_commands.Choice(name="📜 Sepia / Vintage", value="sepia"),
    ])
    @app_commands.checks.cooldown(1, cfg.COLORIZE_COOLDOWN_SECONDS, key=lambda i: i.user.id)
    async def colorize(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        style: Optional[str] = "warm",
    ):
        await interaction.response.defer(thinking=True)

        # ── Validate ──────────────────────────────────────────────────────────
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.followup.send(
                embed=_error_embed("Please upload a valid image file."), ephemeral=True
            )
            return

        if image.size > cfg.MAX_FILE_SIZE_BYTES:
            await interaction.followup.send(
                embed=_error_embed(f"Image too large. Max: {cfg.MAX_FILE_SIZE_MB}MB."),
                ephemeral=True,
            )
            return

        if await self.bot.db.is_banned(interaction.user.id):
            await interaction.followup.send(
                embed=_error_embed("You are banned from using this bot."), ephemeral=True
            )
            return

        # ── Download ──────────────────────────────────────────────────────────
        image_bytes = await image.read()
        valid, err = validate_image(image_bytes)
        if not valid:
            await interaction.followup.send(embed=_error_embed(err), ephemeral=True)
            return

        # ── Progress message ──────────────────────────────────────────────────
        progress_embed = discord.Embed(
            description="🎨 Colorizing your manga panel… this may take 10–30 seconds.",
            color=cfg.COLOR_INFO,
        )
        await interaction.followup.send(embed=progress_embed)

        # ── Colorize ──────────────────────────────────────────────────────────
        try:
            colored_bytes = await colorize_manga_panel(image_bytes, style=style)
        except Exception as exc:
            log.error(f"Colorization error: {exc}", exc_info=True)
            await interaction.edit_original_response(
                embed=_error_embed(f"Colorization failed: {exc}")
            )
            return

        # ── Send result ───────────────────────────────────────────────────────
        safe_name = "".join(c for c in image.filename if c.isalnum() or c in "._-")[:30]
        out_filename = f"colorized_{style}_{safe_name}.png"

        original_file = discord.File(io.BytesIO(image_bytes), filename=f"original_{safe_name}")
        colored_file = discord.File(io.BytesIO(colored_bytes), filename=out_filename)

        embed = discord.Embed(
            title=f"🎨 Colorization Complete — {style.title()} Style",
            color=cfg.COLOR_SUCCESS,
        )
        embed.set_image(url=f"attachment://{out_filename}")
        embed.add_field(
            name="📊 Stats",
            value=(
                f"**Original size:** {len(image_bytes) // 1024}KB\n"
                f"**Output size:** {len(colored_bytes) // 1024}KB\n"
                f"**Style:** {style.title()}"
            ),
            inline=True,
        )
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name} • Use buttons to try other styles",
            icon_url=interaction.user.display_avatar.url,
        )

        view = ColorStyleView(image_bytes, safe_name)
        await interaction.edit_original_response(
            embed=embed,
            attachments=[colored_file],
            view=view,
        )

        await self.bot.db.log_request(
            interaction.user.id, "colorize",
            guild_id=interaction.guild_id if interaction.guild else None,
            details=f"style={style}",
        )

    @app_commands.command(
        name="colorize_help",
        description="ℹ️ Learn how the manga colorization works",
    )
    async def colorize_help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎨 Manga Colorization — How It Works",
            color=cfg.COLOR_MANGA,
        )
        embed.add_field(
            name="🔬 Technology",
            value=(
                "Uses **OpenCV DNN** with the Zhang et al. (2016) deep learning colorization model "
                "trained on millions of images. Falls back to an artistic PIL pipeline if the model "
                "is unavailable."
            ),
            inline=False,
        )
        embed.add_field(
            name="🎨 Available Styles",
            value=(
                "**🌅 Warm** — Natural skin tones, warm lighting\n"
                "**❄️ Cool** — Blue/purple tones, night scene feel\n"
                "**✨ Vivid** — High saturation, vibrant colors\n"
                "**📜 Sepia** — Vintage brown tones"
            ),
            inline=False,
        )
        embed.add_field(
            name="💡 Tips for Best Results",
            value=(
                "• Use clean, high-resolution scans\n"
                "• Black-and-white panels work best\n"
                "• Avoid heavily compressed JPEGs\n"
                "• Max file size: 10MB"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed)


def _error_embed(message: str) -> discord.Embed:
    return discord.Embed(title="❌ Error", description=message, color=cfg.COLOR_ERROR)


async def setup(bot):
    await bot.add_cog(ColorizerCog(bot))
