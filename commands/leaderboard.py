import json
import os
import discord
from discord import app_commands
from discord.ext import tasks
from get_leaderboard import get_whatoubiffs_leaderboard, get_successes_leaderboard
from profile_see import get_profile_embed, ProfileView
from success_see import SuccessesView, build_page_embed, SUCCESSES_PATH
from give import unlock_success_and_notify, get_user_coins
import success_checks

REF_PATH = os.path.join(os.path.dirname(__file__), "leaderboard_ref.json")
PAGE_SIZE = 10
MEDALS = ["🥇", "🥈", "🥉"]
EMOJI_WTBIFF = os.getenv("EMOJI_WTBIFF", "💰")

def build_summary_embed(guild: discord.Guild):
    """Embed principal avec top 10 monnaie + top 10 succès côte à côte."""
    leaderboard = get_whatoubiffs_leaderboard()[:10]
    successes_leaderboard = get_successes_leaderboard()[:10]

    embed = discord.Embed(title="🏆 Leaderboards", color=discord.Color.gold())

    def display_name(user_id):
        member = guild.get_member(int(user_id))
        return member.display_name if member else f"Utilisateur inconnu"

    if leaderboard:
        lines = [
            f"{MEDALS[i] if i < 3 else f'#{i+1}'} {display_name(user_id)} — {monnaie:>6} {EMOJI_WTBIFF}"
            for i, (user_id, monnaie) in enumerate(leaderboard)
        ]
        embed.add_field(name="**Whatoubiffs**", value="\n".join(lines), inline=True)

    if leaderboard and successes_leaderboard:
        embed.add_field(name="\u200b", value="\u200b", inline=True)

    if successes_leaderboard:
        lines = [
            f"{MEDALS[i] if i < 3 else f'#{i+1}'} {display_name(user_id)} — {count:>3} succès"
            for i, (user_id, count) in enumerate(successes_leaderboard)
        ]
        embed.add_field(name="**Succès**", value="\n".join(lines), inline=True)

    if not leaderboard and not successes_leaderboard:
        embed.description = "Aucun membre trouvé."

    return embed

def build_paginated_embed(kind: str, page: int, guild: discord.Guild):
    """Embed d'une page (10 par page) pour un classement complet (monnaie ou succès)."""
    if kind == "monnaie":
        full_leaderboard = get_whatoubiffs_leaderboard()
        title = "Classement — Whatoubiffs"
        unit = lambda v: f"{v:>6} {EMOJI_WTBIFF}"
    else:
        full_leaderboard = get_successes_leaderboard()
        title = "Classement — Succès"
        unit = lambda v: f"{v:>3} succès"

    total_pages = max(1, (len(full_leaderboard) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    start = page * PAGE_SIZE
    chunk = full_leaderboard[start:start + PAGE_SIZE]

    def display_name(user_id):
        member = guild.get_member(int(user_id))
        return member.display_name if member else f"Utilisateur inconnu"

    if not chunk:
        description = "Aucun membre trouvé."
    else:
        lines = []
        for i, (user_id, value) in enumerate(chunk, start=start):
            rank = MEDALS[i] if i < 3 else f"#{i + 1}"
            lines.append(f"{rank} {display_name(user_id)} — {unit(value)}")
        description = "\n".join(lines)

    embed = discord.Embed(title=title, description=description, color=discord.Color.gold())
    embed.set_footer(text=f"Page {page + 1}/{total_pages}")
    return embed, page, total_pages


def get_user_rank(kind: str, user_id: str):
    """Retourne (rang (1-indexé), valeur, total_membres) ou None si absent."""
    full_leaderboard = get_whatoubiffs_leaderboard() if kind == "monnaie" else get_successes_leaderboard()
    for i, (uid, value) in enumerate(full_leaderboard):
        if uid == user_id:
            return i + 1, value, len(full_leaderboard)
    return None

def build_position_embed(member: discord.Member, viewer: discord.Member = None):
    is_self = viewer is None or viewer.id == member.id
    title = "Ta position" if is_self else f"Position de {member.display_name}"
    embed = discord.Embed(title=title, color=discord.Color.blurple())
    user_id = str(member.id)

    monnaie_rank = get_user_rank("monnaie", user_id)
    if monnaie_rank:
        rank, value, total = monnaie_rank
        embed.add_field(name=f"**Whatoubiffs**", value=f"#{rank}/{total} — {value} {EMOJI_WTBIFF}", inline=True)
    else:
        embed.add_field(name=f"**Whatoubiffs**", value="Non classé", inline=True)

    success_rank = get_user_rank("success", user_id)
    if success_rank:
        rank, value, total = success_rank
        embed.add_field(name=f"**Succès**", value=f"#{rank}/{total} — {value}", inline=True)
    else:
        embed.add_field(name=f"**Succès**", value="Non classé", inline=True)

    return embed


class UserPickerView(discord.ui.View):
    """Vue éphémère avec un sélecteur de membre, pour les actions 'de quelqu'un'."""
    def __init__(self, mode: str):
        super().__init__(timeout=60)
        self.mode = mode  # "position" | "profil" | "succes"

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Choisis un membre")
    async def select_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        target = select.values[0]

        if self.mode == "position":
            embed = build_position_embed(target, viewer=interaction.user)
            await interaction.response.edit_message(content=None, embed=embed, view=None)
        elif self.mode == "profil":
            embed = get_profile_embed(target)
            view = ProfileView(target)
            await interaction.response.edit_message(content=None, embed=embed, view=view)
        elif self.mode == "succes":
            successes_def = json.load(open(SUCCESSES_PATH, encoding="utf-8"))
            categories = list(successes_def.keys())
            view = SuccessesView(target, categories)
            embed = build_page_embed(target, categories[0], categories)
            await interaction.response.edit_message(content=None, embed=embed, view=view)

# ---------- Views ----------
class PaginatedLeaderboardView(discord.ui.View):
    def __init__(self, kind: str, guild: discord.Guild, page: int = 0):
        super().__init__(timeout=None)
        self.kind = kind
        self.guild = guild
        self.page = page
        self._update_button_states()

    def _update_button_states(self):
        _, page, total_pages = build_paginated_embed(self.kind, self.page, self.guild)
        self.page = page
        self.previous_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= total_pages - 1

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        embed, self.page, _ = build_paginated_embed(self.kind, self.page, self.guild)
        self._update_button_states()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        embed, self.page, _ = build_paginated_embed(self.kind, self.page, self.guild)
        self._update_button_states()
        await interaction.response.edit_message(embed=embed, view=self)


class LeaderboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # Row 0
    @discord.ui.button(label="💰 Ladder WhatouBiffs ", style=discord.ButtonStyle.secondary, custom_id="ranking_wtbiffs", row=0)
    async def full_monnaie_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed, page, _ = build_paginated_embed("monnaie", 0, interaction.guild)
        view = PaginatedLeaderboardView("monnaie", interaction.guild, page)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🏆 Ladder Succès", style=discord.ButtonStyle.secondary, custom_id="ranking_successes", row=0)
    async def full_success_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed, page, _ = build_paginated_embed("success", 0, interaction.guild)
        view = PaginatedLeaderboardView("success", interaction.guild, page)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # Row 1 — moi
    @discord.ui.button(label="📌 Mon Rang", style=discord.ButtonStyle.secondary, custom_id="see_position", row=1)
    async def my_position_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_position_embed(interaction.user, viewer=interaction.user)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="👤 Mon Profil", style=discord.ButtonStyle.secondary, custom_id="see_profile", row=1)
    async def my_profile_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = get_profile_embed(interaction.user)
        view = ProfileView(interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await unlock_success_and_notify(interaction.user, "profile_viewed", "Global", interaction)
        await success_checks.check_coins_success(interaction)
        await success_checks.check_riot_linked_success(interaction.user, interaction)
        await success_checks.check_twitch_wtb_linked_success(interaction.user, interaction)
        await success_checks.check_whatoubance_club_success(interaction.user, interaction)
        

    @discord.ui.button(label="🎖️ Mes Succès", style=discord.ButtonStyle.secondary, custom_id="see_successes", row=1)
    async def my_successes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        successes_def = json.load(open(SUCCESSES_PATH, encoding="utf-8"))
        categories = list(successes_def.keys()) + ["Boutique"]
        view = SuccessesView(interaction.user, categories)
        embed = build_page_embed(interaction.user, categories[0], categories)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # Row 2 — quelqu'un d'autre
    @discord.ui.button(label="❓ Rang de ...", style=discord.ButtonStyle.secondary, custom_id="see_position_other", row=2)
    async def other_position_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(view=UserPickerView("position"), ephemeral=True)

    @discord.ui.button(label="❓ Profil de ... ", style=discord.ButtonStyle.secondary, custom_id="see_profile_other", row=2)
    async def other_profile_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(view=UserPickerView("profil"), ephemeral=True)

    @discord.ui.button(label="❓ Succès de ...", style=discord.ButtonStyle.secondary, custom_id="see_successes_other", row=2)
    async def other_successes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(view=UserPickerView("succes"), ephemeral=True)


# ---------- Persistance du message principal ----------

leaderboard_message_ref = {"channel_id": None, "message_id": None}


def load_leaderboard_ref():
    if os.path.exists(REF_PATH) and os.path.getsize(REF_PATH) > 0:
        with open(REF_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"channel_id": None, "message_id": None}


def save_leaderboard_ref():
    with open(REF_PATH, "w", encoding="utf-8") as f:
        json.dump(leaderboard_message_ref, f)


leaderboard_message_ref.update(load_leaderboard_ref())

async def send_leaderboard(channel: discord.abc.GuildChannel):
    msg = await channel.send(embed=build_summary_embed(channel.guild), view=LeaderboardView())
    leaderboard_message_ref["channel_id"] = msg.channel.id
    leaderboard_message_ref["message_id"] = msg.id
    save_leaderboard_ref()
    return msg


async def update_leaderboard(bot: discord.Client):
    if leaderboard_message_ref["message_id"] is None:
        return False

    channel = bot.get_channel(leaderboard_message_ref["channel_id"])
    if channel is None:
        return False

    try:
        message = await channel.fetch_message(leaderboard_message_ref["message_id"])
        await message.edit(embed=build_summary_embed(channel.guild))
        return True
    except discord.NotFound:
        return False


# ---------- Commandes ----------

def setup(bot):
    bot.add_view(LeaderboardView()) 

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="setup_leaderboard", description="Envoie le leaderboard")
    async def setup_leaderboard_command(interaction: discord.Interaction):
        await send_leaderboard(interaction.channel)
        await interaction.response.send_message("Leaderboard envoyé ✅", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="update_leaderboard", description="update")
    async def update_leaderboard_command(interaction: discord.Interaction):
        success = await update_leaderboard(bot)
        message = "Leaderboard mis à jour ✅" if success else "Aucun leaderboard trouvé."
        await interaction.response.send_message(message, ephemeral=True)

    @tasks.loop(minutes=1)
    async def auto_update_leaderboard():
        await update_leaderboard(bot)

    if not auto_update_leaderboard.is_running():
        auto_update_leaderboard.start()