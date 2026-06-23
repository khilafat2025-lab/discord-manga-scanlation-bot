"""
Cog 4: Advanced Admin Panel
=============================
Slash commands (owner/admin only):
  /admin stats      — global bot statistics
  /admin users      — top users leaderboard
  /admin ban        — ban a user
  /admin unban      — unban a user
  /admin premium    — grant/revoke premium
  /admin broadcast  — send message to all guilds
  /admin logs       — recent audit log
  /admin reload     — reload a cog
  /admin shutdown   — graceful shutdown

Features:
  - Owner-only and admin-only permission checks
  - Paginated stats with interactive buttons
  - Broadcast with confirmation dialog
  - Full audit trail in SQLite
  - Real-time uptime display
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import Config

log = logging.getLogger("MangaBot.Admin")
cfg = Config()


def is_owner():
    """Check if the interaction user is a bot owner."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id in cfg.OWNER_IDS:
            return True
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🚫 Access Denied",
                description="This command is restricted to bot owners.",
                color=cfg.COLOR_ERROR,
            ),
            ephemeral=True,
        )
        return False
    return app_commands.check(predicate)


def is_admin():
    """Check if the user is a bot owner or has Administrator permission."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id in cfg.OWNER_IDS:
            return True
        if interaction.guild and interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🚫 Access Denied",
                description="This command requires Administrator permission.",
                color=cfg.COLOR_ERROR,
            ),
            ephemeral=True,
        )
        return False
    return app_commands.check(predicate)


# ── Broadcast Confirmation ────────────────────────────────────────────────────

class BroadcastConfirmView(discord.ui.View):
    def __init__(self, message: str, bot):
        super().__init__(timeout=60)
        self.message = message
        self.bot = bot
        self.confirmed = False

    @discord.ui.button(label="✅ Confirm Broadcast", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Broadcast cancelled.", ephemeral=True)
        self.stop()


# ── Stats Pagination ──────────────────────────────────────────────────────────

class StatsPaginationView(discord.ui.View):
    def __init__(self, pages: list[discord.Embed]):
        super().__init__(timeout=120)
        self.pages = pages
        self.current = 0
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.current == 0
        self.next_btn.disabled = self.current >= len(self.pages) - 1

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)


# ── Admin Cog ─────────────────────────────────────────────────────────────────

class AdminCog(commands.Cog, name="Admin"):
    """Full admin panel for bot management."""

    def __init__(self, bot):
        self.bot = bot

    admin_group = app_commands.Group(name="admin", description="🔧 Bot administration commands")

    # ── /admin stats ──────────────────────────────────────────────────────────
    @admin_group.command(name="stats", description="📊 View global bot statistics")
    @is_admin()
    async def stats(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        stats = await self.bot.db.get_global_stats()
        top_users = await self.bot.db.get_top_users(5)

        uptime = discord.utils.utcnow() - self.bot.start_time
        hours, rem = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # Page 1: Overview
        p1 = discord.Embed(title="📊 Bot Statistics — Overview", color=cfg.COLOR_PRIMARY)
        p1.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)
        p1.add_field(name="🏠 Guilds", value=str(stats["total_guilds"]), inline=True)
        p1.add_field(name="👥 Total Users", value=str(stats["total_users"]), inline=True)
        p1.add_field(name="🚫 Banned Users", value=str(stats["banned_users"]), inline=True)
        p1.add_field(name="⭐ Premium Users", value=str(stats["premium_users"]), inline=True)
        p1.add_field(name="📨 Total Requests", value=str(stats["total_requests"]), inline=True)
        p1.set_footer(text=f"Page 1/2 • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

        # Page 2: Command breakdown + top users
        p2 = discord.Embed(title="📊 Bot Statistics — Commands & Users", color=cfg.COLOR_PRIMARY)
        p2.add_field(name="🔍 OCR Requests", value=str(stats["ocr_requests"]), inline=True)
        p2.add_field(name="🎨 Colorize Requests", value=str(stats["colorize_reqs"]), inline=True)
        p2.add_field(name="📄 Translate Requests", value=str(stats["translate_reqs"]), inline=True)

        if top_users:
            top_str = "\n".join(
                f"`{i+1}.` {row[1] or 'Unknown'} — **{row[2]}** requests"
                for i, row in enumerate(top_users)
            )
            p2.add_field(name="🏆 Top Users", value=top_str, inline=False)
        p2.set_footer(text="Page 2/2")

        view = StatsPaginationView([p1, p2])
        await interaction.followup.send(embed=p1, view=view, ephemeral=True)

    # ── /admin ban ────────────────────────────────────────────────────────────
    @admin_group.command(name="ban", description="🚫 Ban a user from using the bot")
    @app_commands.describe(user="The user to ban", reason="Reason for ban")
    @is_owner()
    async def ban(self, interaction: discord.Interaction, user: discord.User, reason: str = "No reason provided"):
        await interaction.response.defer(ephemeral=True)

        if user.id in cfg.OWNER_IDS:
            await interaction.followup.send(
                embed=discord.Embed(description="❌ Cannot ban a bot owner.", color=cfg.COLOR_ERROR),
                ephemeral=True,
            )
            return

        await self.bot.db.ban_user(user.id, interaction.user.id)

        embed = discord.Embed(
            title="🚫 User Banned",
            color=cfg.COLOR_ERROR,
        )
        embed.add_field(name="User", value=f"{user.mention} (`{user.id}`)")
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Banned by", value=interaction.user.mention)
        await interaction.followup.send(embed=embed, ephemeral=True)
        log.info(f"User {user.id} banned by {interaction.user.id}: {reason}")

    # ── /admin unban ──────────────────────────────────────────────────────────
    @admin_group.command(name="unban", description="✅ Unban a user")
    @app_commands.describe(user_id="The user ID to unban")
    @is_owner()
    async def unban(self, interaction: discord.Interaction, user_id: str):
        await interaction.response.defer(ephemeral=True)

        try:
            uid = int(user_id)
        except ValueError:
            await interaction.followup.send(
                embed=discord.Embed(description="❌ Invalid user ID.", color=cfg.COLOR_ERROR),
                ephemeral=True,
            )
            return

        await self.bot.db.unban_user(uid, interaction.user.id)
        embed = discord.Embed(
            title="✅ User Unbanned",
            description=f"User `{uid}` has been unbanned.",
            color=cfg.COLOR_SUCCESS,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /admin premium ────────────────────────────────────────────────────────
    @admin_group.command(name="premium", description="⭐ Grant or revoke premium status")
    @app_commands.describe(user="Target user", grant="True to grant, False to revoke")
    @is_owner()
    async def premium(self, interaction: discord.Interaction, user: discord.User, grant: bool):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.set_premium(user.id, grant, interaction.user.id)
        action = "granted ⭐" if grant else "revoked"
        embed = discord.Embed(
            title=f"Premium {action.title()}",
            description=f"Premium has been **{action}** for {user.mention}.",
            color=cfg.COLOR_SUCCESS if grant else cfg.COLOR_WARNING,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /admin broadcast ──────────────────────────────────────────────────────
    @admin_group.command(name="broadcast", description="📢 Send a message to all guilds' system channels")
    @app_commands.describe(message="Message to broadcast")
    @is_owner()
    async def broadcast(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=True)

        preview_embed = discord.Embed(
            title="📢 Broadcast Preview",
            description=message,
            color=cfg.COLOR_WARNING,
        )
        preview_embed.add_field(name="Target Guilds", value=str(len(self.bot.guilds)))
        preview_embed.set_footer(text="Click Confirm to send to all guilds")

        view = BroadcastConfirmView(message, self.bot)
        await interaction.followup.send(embed=preview_embed, view=view, ephemeral=True)
        await view.wait()

        if not view.confirmed:
            return

        broadcast_embed = discord.Embed(
            title="📢 Announcement",
            description=message,
            color=cfg.COLOR_PRIMARY,
        )
        broadcast_embed.set_footer(text=f"From: {self.bot.user.name}")

        sent, failed = 0, 0
        for guild in self.bot.guilds:
            channel = guild.system_channel or next(
                (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),
                None,
            )
            if channel:
                try:
                    await channel.send(embed=broadcast_embed)
                    sent += 1
                except Exception:
                    failed += 1

        result_embed = discord.Embed(
            title="📢 Broadcast Complete",
            color=cfg.COLOR_SUCCESS,
        )
        result_embed.add_field(name="✅ Sent", value=str(sent))
        result_embed.add_field(name="❌ Failed", value=str(failed))
        await interaction.followup.send(embed=result_embed, ephemeral=True)

    # ── /admin logs ───────────────────────────────────────────────────────────
    @admin_group.command(name="logs", description="📋 View recent audit logs")
    @is_owner()
    async def logs(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        logs_data = await self.bot.db.get_audit_logs(15)
        if not logs_data:
            await interaction.followup.send(
                embed=discord.Embed(description="No audit logs yet.", color=cfg.COLOR_INFO),
                ephemeral=True,
            )
            return

        embed = discord.Embed(title="📋 Recent Audit Logs", color=cfg.COLOR_INFO)
        lines = []
        for row in logs_data:
            actor_id, action, target_id, details, created_at = row
            lines.append(f"`{created_at[:16]}` **{action}** by `{actor_id}` → `{target_id}`")

        embed.description = "\n".join(lines[:15])
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /admin recent ─────────────────────────────────────────────────────────
    @admin_group.command(name="recent", description="📜 View recent bot requests")
    @is_admin()
    async def recent(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        requests = await self.bot.db.get_recent_requests(15)
        if not requests:
            await interaction.followup.send(
                embed=discord.Embed(description="No requests yet.", color=cfg.COLOR_INFO),
                ephemeral=True,
            )
            return

        embed = discord.Embed(title="📜 Recent Requests", color=cfg.COLOR_INFO)
        lines = []
        for row in requests:
            user_id, username, command, status, created_at = row
            icon = "✅" if status == "success" else "❌"
            lines.append(f"`{created_at[:16]}` {icon} `/{command}` — {username or user_id}")

        embed.description = "\n".join(lines)
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /admin reload ─────────────────────────────────────────────────────────
    @admin_group.command(name="reload", description="🔄 Reload a cog")
    @app_commands.describe(cog="Cog name (e.g. manga_ocr, colorizer, file_translator, admin)")
    @is_owner()
    async def reload(self, interaction: discord.Interaction, cog: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"✅ Cog `{cog}` reloaded successfully.",
                    color=cfg.COLOR_SUCCESS,
                ),
                ephemeral=True,
            )
        except Exception as exc:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"❌ Failed to reload `{cog}`: {exc}",
                    color=cfg.COLOR_ERROR,
                ),
                ephemeral=True,
            )

    # ── /admin shutdown ───────────────────────────────────────────────────────
    @admin_group.command(name="shutdown", description="⛔ Gracefully shut down the bot")
    @is_owner()
    async def shutdown(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                description="⛔ Shutting down… goodbye!",
                color=cfg.COLOR_ERROR,
            ),
            ephemeral=True,
        )
        log.info(f"Shutdown initiated by {interaction.user.id}")
        await self.bot.close()

    # ── /admin sync ───────────────────────────────────────────────────────────
    @admin_group.command(name="sync", description="🔄 Sync slash commands globally")
    @is_owner()
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        synced = await self.bot.tree.sync()
        await interaction.followup.send(
            embed=discord.Embed(
                description=f"✅ Synced **{len(synced)}** slash commands globally.",
                color=cfg.COLOR_SUCCESS,
            ),
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
