"""
cogs/image_gen.py
-----------------
Nano Banana Image Generation & Editing Cog
Uses Google Gemini image models via AI Studio API key:
  - models/gemini-2.5-flash-image  → "Nano Banana"
  - models/gemini-3.1-flash-image  → "Nano Banana 2"
  - models/nano-banana-pro-preview → "Nano Banana Pro"

Commands:
  /generate_image  — text prompt → AI-generated image
  /edit_image      — upload image + prompt → edited image
  /nano_models     — list available Nano Banana models
  /nano_help       — how to use Nano Banana commands
"""

import asyncio
import base64
import io
import json
import logging
import os
import ssl
import time
import urllib.request
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
try:
    from utils.config import Config
    GOOGLE_API_KEY = Config.GOOGLE_API_KEY
except Exception:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

try:
    from utils.database import Database
    _db_available = True
except Exception:
    _db_available = False

_ssl_ctx = ssl.create_default_context()

# ── Nano Banana model registry ────────────────────────────────────────────────
NANO_MODELS = {
    "nano_banana": {
        "id": "gemini-2.5-flash-image",
        "display": "Nano Banana",
        "emoji": "🍌",
        "description": "Fast, creative image generation",
    },
    "nano_banana_2": {
        "id": "gemini-3.1-flash-image",
        "display": "Nano Banana 2",
        "emoji": "🍌🍌",
        "description": "Enhanced quality & detail",
    },
    "nano_banana_pro": {
        "id": "nano-banana-pro-preview",
        "display": "Nano Banana Pro",
        "emoji": "🍌⭐",
        "description": "Highest quality, slower",
    },
}

DEFAULT_MODEL = "nano_banana"  # gemini-2.5-flash-image


# ── Style presets ─────────────────────────────────────────────────────────────
STYLE_PRESETS = {
    "manga": "black and white manga art style, clean line art, Japanese manga aesthetic",
    "anime": "colorful anime art style, vibrant colors, Studio Ghibli inspired",
    "realistic": "photorealistic, highly detailed, professional photography",
    "watercolor": "watercolor painting style, soft colors, artistic",
    "chibi": "cute chibi anime style, big eyes, small body, adorable",
    "cyberpunk": "cyberpunk aesthetic, neon lights, futuristic, dark atmosphere",
    "none": "",
}


# ── Gemini image generation ───────────────────────────────────────────────────
async def _call_gemini_image(
    prompt: str,
    model_id: str,
    image_bytes: Optional[bytes] = None,
    mime_type: str = "image/jpeg",
) -> Optional[bytes]:
    """
    Call Gemini image model. Returns PNG bytes or None on failure.
    Supports both text-to-image and image-to-image (edit).
    """
    if not GOOGLE_API_KEY:
        return None

    parts = []

    # If editing an existing image, include it first
    if image_bytes:
        b64 = base64.b64encode(image_bytes).decode()
        parts.append({"inline_data": {"mime_type": mime_type, "data": b64}})

    parts.append({"text": prompt})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
            "temperature": 1.0,
        },
    }

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model_id}:generateContent?key={GOOGLE_API_KEY}"
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
            with urllib.request.urlopen(req, timeout=60, context=_ssl_ctx) as r:
                return json.loads(r.read())

        data = await loop.run_in_executor(None, _call)

        # Extract image from response
        candidates = data.get("candidates", [])
        for candidate in candidates:
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                if "inline_data" in part:
                    img_data = part["inline_data"]
                    img_bytes = base64.b64decode(img_data["data"])
                    logger.info(f"Nano Banana ({model_id}) generated image: {len(img_bytes)} bytes")
                    return img_bytes

        # Log any text response for debugging
        for candidate in candidates:
            for part in candidate.get("content", {}).get("parts", []):
                if "text" in part:
                    logger.warning(f"Nano Banana text response (no image): {part['text'][:200]}")

        return None

    except Exception as e:
        logger.error(f"Gemini image generation failed ({model_id}): {e}")
        return None


async def _try_models_in_order(
    prompt: str,
    image_bytes: Optional[bytes] = None,
    mime_type: str = "image/jpeg",
    preferred_model: str = DEFAULT_MODEL,
) -> tuple[Optional[bytes], str]:
    """Try models in order, starting with preferred. Returns (bytes, model_display_name)."""
    # Build order: preferred first, then others
    order = [preferred_model] + [k for k in NANO_MODELS if k != preferred_model]

    for model_key in order:
        model = NANO_MODELS[model_key]
        logger.info(f"Trying {model['display']} ({model['id']})...")
        result = await _call_gemini_image(
            prompt, model["id"], image_bytes, mime_type
        )
        if result:
            return result, model["display"]

    return None, ""


# ── Model selector UI ─────────────────────────────────────────────────────────
class ModelSelectView(discord.ui.View):
    def __init__(self, prompt: str, style: str, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.prompt = prompt
        self.style = style
        self.chosen_model = DEFAULT_MODEL

    @discord.ui.select(
        placeholder="🍌 Choose Nano Banana model...",
        options=[
            discord.SelectOption(
                label="Nano Banana",
                value="nano_banana",
                description="Fast & creative (gemini-2.5-flash-image)",
                emoji="🍌",
                default=True,
            ),
            discord.SelectOption(
                label="Nano Banana 2",
                value="nano_banana_2",
                description="Enhanced quality (gemini-3.1-flash-image)",
                emoji="🍌",
            ),
            discord.SelectOption(
                label="Nano Banana Pro",
                value="nano_banana_pro",
                description="Highest quality (nano-banana-pro-preview)",
                emoji="⭐",
            ),
        ],
    )
    async def model_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        self.chosen_model = select.values[0]
        model = NANO_MODELS[self.chosen_model]
        await interaction.response.send_message(
            f"✅ Selected **{model['display']}** — generating now...",
            ephemeral=True,
        )
        self.stop()


# ── Main Cog ──────────────────────────────────────────────────────────────────
class ImageGenCog(commands.Cog, name="🍌 Nano Banana"):
    """AI Image Generation & Editing powered by Google Gemini Nano Banana models."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._rate_limits: dict[int, float] = {}  # user_id → last_request_time
        self._cooldown_seconds = 30  # 30s cooldown per user

    def _check_rate_limit(self, user_id: int) -> Optional[float]:
        """Returns remaining cooldown seconds, or None if OK."""
        last = self._rate_limits.get(user_id, 0)
        elapsed = time.time() - last
        if elapsed < self._cooldown_seconds:
            return self._cooldown_seconds - elapsed
        return None

    def _set_rate_limit(self, user_id: int):
        self._rate_limits[user_id] = time.time()

    # ── /generate_image ───────────────────────────────────────────────────────
    @app_commands.command(
        name="generate_image",
        description="🍌 Generate an AI image using Nano Banana (Gemini image model)",
    )
    @app_commands.describe(
        prompt="Describe the image you want to generate",
        style="Art style preset (optional)",
        model="Which Nano Banana model to use",
    )
    @app_commands.choices(
        style=[
            app_commands.Choice(name="🎌 Manga (B&W line art)", value="manga"),
            app_commands.Choice(name="🌸 Anime (colorful)", value="anime"),
            app_commands.Choice(name="📷 Realistic", value="realistic"),
            app_commands.Choice(name="🎨 Watercolor", value="watercolor"),
            app_commands.Choice(name="🐱 Chibi (cute)", value="chibi"),
            app_commands.Choice(name="🌆 Cyberpunk", value="cyberpunk"),
            app_commands.Choice(name="✏️ No style (raw prompt)", value="none"),
        ],
        model=[
            app_commands.Choice(name="🍌 Nano Banana (fast)", value="nano_banana"),
            app_commands.Choice(name="🍌🍌 Nano Banana 2 (better)", value="nano_banana_2"),
            app_commands.Choice(name="🍌⭐ Nano Banana Pro (best)", value="nano_banana_pro"),
        ],
    )
    async def generate_image(
        self,
        interaction: discord.Interaction,
        prompt: str,
        style: str = "anime",
        model: str = DEFAULT_MODEL,
    ):
        # Rate limit check
        remaining = self._check_rate_limit(interaction.user.id)
        if remaining:
            await interaction.response.send_message(
                f"⏳ Please wait **{remaining:.0f}s** before generating another image.",
                ephemeral=True,
            )
            return

        if not GOOGLE_API_KEY:
            await interaction.response.send_message(
                "❌ **GOOGLE_API_KEY** not configured. Add your AI Studio key to use Nano Banana.",
                ephemeral=True,
            )
            return

        if len(prompt) > 500:
            await interaction.response.send_message(
                "❌ Prompt too long (max 500 characters).", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        # Build full prompt with style
        style_suffix = STYLE_PRESETS.get(style, "")
        full_prompt = f"{prompt}, {style_suffix}".strip(", ") if style_suffix else prompt

        model_info = NANO_MODELS.get(model, NANO_MODELS[DEFAULT_MODEL])

        # Generate
        start = time.time()
        img_bytes, used_model = await _try_models_in_order(
            full_prompt, preferred_model=model
        )
        elapsed = time.time() - start

        if not img_bytes:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Generation Failed",
                    description=(
                        "Nano Banana couldn't generate an image for this prompt.\n"
                        "Try a different prompt or style."
                    ),
                    color=discord.Color.red(),
                )
            )
            return

        self._set_rate_limit(interaction.user.id)

        # Log to DB
        if _db_available:
            try:
                db = Database()
                await db.log_request(
                    user_id=interaction.user.id,
                    guild_id=interaction.guild_id or 0,
                    command="generate_image",
                    status="success",
                )
            except Exception:
                pass

        # Build embed
        embed = discord.Embed(
            title=f"🍌 Nano Banana — Image Generated!",
            color=discord.Color.yellow(),
        )
        embed.add_field(name="📝 Prompt", value=f"```{prompt[:200]}```", inline=False)
        embed.add_field(name="🎨 Style", value=style.title(), inline=True)
        embed.add_field(name="🤖 Model", value=used_model, inline=True)
        embed.add_field(name="⏱️ Time", value=f"{elapsed:.1f}s", inline=True)
        embed.set_footer(
            text=f"Generated by {interaction.user.display_name} • Powered by Google Gemini",
            icon_url=interaction.user.display_avatar.url,
        )
        embed.set_image(url="attachment://generated.png")

        file = discord.File(io.BytesIO(img_bytes), filename="generated.png")
        await interaction.followup.send(embed=embed, file=file)

    # ── /edit_image ───────────────────────────────────────────────────────────
    @app_commands.command(
        name="edit_image",
        description="🍌 Edit/transform an image using Nano Banana AI",
    )
    @app_commands.describe(
        image="Upload the image you want to edit",
        prompt="Describe how to edit or transform the image",
        model="Which Nano Banana model to use",
    )
    @app_commands.choices(
        model=[
            app_commands.Choice(name="🍌 Nano Banana (fast)", value="nano_banana"),
            app_commands.Choice(name="🍌🍌 Nano Banana 2 (better)", value="nano_banana_2"),
            app_commands.Choice(name="🍌⭐ Nano Banana Pro (best)", value="nano_banana_pro"),
        ],
    )
    async def edit_image(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        prompt: str,
        model: str = DEFAULT_MODEL,
    ):
        # Rate limit
        remaining = self._check_rate_limit(interaction.user.id)
        if remaining:
            await interaction.response.send_message(
                f"⏳ Please wait **{remaining:.0f}s** before another request.",
                ephemeral=True,
            )
            return

        if not GOOGLE_API_KEY:
            await interaction.response.send_message(
                "❌ **GOOGLE_API_KEY** not configured.", ephemeral=True
            )
            return

        # Validate attachment
        allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        content_type = image.content_type or ""
        if not any(ct in content_type for ct in ["jpeg", "png", "webp", "gif"]):
            await interaction.response.send_message(
                "❌ Please upload a JPG, PNG, WEBP, or GIF image.", ephemeral=True
            )
            return

        if image.size > 8 * 1024 * 1024:
            await interaction.response.send_message(
                "❌ Image too large (max 8MB).", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        # Download image
        try:
            loop = asyncio.get_event_loop()
            img_bytes = await image.read()
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to download image: {e}")
            return

        # Detect mime
        mime = "image/jpeg"
        if img_bytes[:4] == b'\x89PNG':
            mime = "image/png"
        elif b'WEBP' in img_bytes[:12]:
            mime = "image/webp"

        # Edit
        edit_prompt = (
            f"Edit this image: {prompt}. "
            f"Maintain the overall composition but apply the requested changes."
        )

        start = time.time()
        result_bytes, used_model = await _try_models_in_order(
            edit_prompt, image_bytes=img_bytes, mime_type=mime, preferred_model=model
        )
        elapsed = time.time() - start

        if not result_bytes:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Edit Failed",
                    description=(
                        "Nano Banana couldn't edit this image.\n"
                        "Try a clearer edit description or different image."
                    ),
                    color=discord.Color.red(),
                )
            )
            return

        self._set_rate_limit(interaction.user.id)

        # Log
        if _db_available:
            try:
                db = Database()
                await db.log_request(
                    user_id=interaction.user.id,
                    guild_id=interaction.guild_id or 0,
                    command="edit_image",
                    status="success",
                )
            except Exception:
                pass

        embed = discord.Embed(
            title="🍌 Nano Banana — Image Edited!",
            color=discord.Color.green(),
        )
        embed.add_field(name="✏️ Edit Prompt", value=f"```{prompt[:200]}```", inline=False)
        embed.add_field(name="🤖 Model", value=used_model, inline=True)
        embed.add_field(name="⏱️ Time", value=f"{elapsed:.1f}s", inline=True)
        embed.set_footer(
            text=f"Edited by {interaction.user.display_name} • Powered by Google Gemini",
            icon_url=interaction.user.display_avatar.url,
        )
        embed.set_image(url="attachment://edited.png")

        file = discord.File(io.BytesIO(result_bytes), filename="edited.png")
        await interaction.followup.send(embed=embed, file=file)

    # ── /nano_models ──────────────────────────────────────────────────────────
    @app_commands.command(
        name="nano_models",
        description="🍌 List all available Nano Banana image models",
    )
    async def nano_models(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🍌 Nano Banana — Available Models",
            description="Google Gemini image generation models accessible with your API key:",
            color=discord.Color.yellow(),
        )
        for key, info in NANO_MODELS.items():
            status = "✅ Active" if GOOGLE_API_KEY else "❌ No API key"
            embed.add_field(
                name=f"{info['emoji']} {info['display']}",
                value=(
                    f"**Model ID:** `{info['id']}`\n"
                    f"**Description:** {info['description']}\n"
                    f"**Status:** {status}"
                ),
                inline=False,
            )
        embed.add_field(
            name="📋 Also Available",
            value=(
                "`models/imagen-4.0-generate-001` — Imagen 4\n"
                "`models/imagen-4.0-ultra-generate-001` — Imagen 4 Ultra\n"
                "`models/imagen-4.0-fast-generate-001` — Imagen 4 Fast"
            ),
            inline=False,
        )
        embed.set_footer(text="Use /generate_image or /edit_image to create images")
        await interaction.response.send_message(embed=embed)

    # ── /nano_help ────────────────────────────────────────────────────────────
    @app_commands.command(
        name="nano_help",
        description="🍌 How to use Nano Banana image generation commands",
    )
    async def nano_help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🍌 Nano Banana — Help Guide",
            description="AI image generation & editing powered by Google Gemini",
            color=discord.Color.yellow(),
        )
        embed.add_field(
            name="🖼️ /generate_image",
            value=(
                "Generate a new image from a text prompt.\n"
                "**Usage:** `/generate_image prompt:a samurai in the rain style:anime`\n"
                "**Styles:** manga, anime, realistic, watercolor, chibi, cyberpunk\n"
                "**Models:** Nano Banana, Nano Banana 2, Nano Banana Pro"
            ),
            inline=False,
        )
        embed.add_field(
            name="✏️ /edit_image",
            value=(
                "Edit or transform an existing image.\n"
                "**Usage:** `/edit_image image:[upload] prompt:make it look like anime`\n"
                "**Tip:** Be specific about what to change!"
            ),
            inline=False,
        )
        embed.add_field(
            name="📋 /nano_models",
            value="List all available Nano Banana models and their status.",
            inline=False,
        )
        embed.add_field(
            name="⚡ Tips for Best Results",
            value=(
                "• Be descriptive: `a girl with blue hair reading manga in a cozy library`\n"
                "• Add style details: `soft lighting, detailed background, high quality`\n"
                "• For manga: use the **manga** style preset\n"
                "• Cooldown: 30 seconds between requests"
            ),
            inline=False,
        )
        embed.add_field(
            name="🔑 API Key Status",
            value=(
                "✅ **GOOGLE_API_KEY configured** — Nano Banana is active!"
                if GOOGLE_API_KEY
                else "❌ **No GOOGLE_API_KEY** — Add your AI Studio key to enable Nano Banana"
            ),
            inline=False,
        )
        embed.set_footer(text="Powered by Google Gemini • AI Studio API")
        await interaction.response.send_message(embed=embed)


# ── Setup ─────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(ImageGenCog(bot))
    logger.info("ImageGenCog (Nano Banana) loaded ✅")
