import json
import os
import discord
from discord import app_commands
from discord.ext import tasks
from get_leaderboard import get_whatoubiffs_leaderboard, get_successes_leaderboard

REF_PATH = os.path.join(os.path.dirname(__file__), "leaderboard_ref.json")
PAGE_SIZE = 10
MEDALS = ["🥇", "🥈", "🥉"]

def build_summary_embed():
    """Embed principal avec top 10 monnaie + top 10 succès côte à côte."""
    leaderboard = get_whatoubiffs_leaderboard()[:10]
    successes_leaderboard = get_successes_leaderboard()[:10]

    embed = discord.Embed(title="🏆 Leaderboards", color=discord.Color.gold())

    if leaderboard:
        lines = [
            f"{MEDALS[i] if i < 3 else f'#{i+1}'} <@{user_id}> — {monnaie:>6} 💰"
            for i, (user_id, monnaie) in enumerate(leaderboard)
        ]
        embed.add_field(name="**Whatoubiffs**", value="\n".join(lines), inline=True)

    if leaderboard and successes_leaderboard:
        embed.add_field(name="\u200b", value="\u200b", inline=True)

    if successes_leaderboard:
        lines = [
            f"{MEDALS[i] if i < 3 else f'#{i+1}'} <@{user_id}> — {count:>3} succès"
            for i, (user_id, count) in enumerate(successes_leaderboard)
        ]
        embed.add_field(name="**Succès**", value="\n".join(lines), inline=True)

    if not leaderboard and not successes_leaderboard:
        embed.description = "Aucun membre trouvé."

    return embed


def build_paginated_embed(kind: str, page: int):
    """Embed d'une page (10 par page) pour un classement complet (monnaie ou succès)."""
    if kind == "monnaie":
        full_leaderboard = get_whatoubiffs_leaderboard()
        title = "Classement — Whatoubiffs"
        unit = lambda v: f"{v:>6} 💰"
    else:
        full_leaderboard = get_successes_leaderboard()
        title = "Classement — Succès"
        unit = lambda v: f"{v:>3} succès"

    total_pages = max(1, (len(full_leaderboard) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    start = page * PAGE_SIZE
    chunk = full_leaderboard[start:start + PAGE_SIZE]

    if not chunk:
        description = "Aucun membre trouvé."
    else:
        lines = []
        for i, (user_id, value) in enumerate(chunk, start=start):
            rank = MEDALS[i] if i < 3 else f"#{i + 1}"
            lines.append(f"{rank} <@{user_id}> — {unit(value)}")
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


def build_position_embed(member: discord.Member):
    embed = discord.Embed(title="Ta position", color=discord.Color.blurple())
    user_id = str(member.id)

    monnaie_rank = get_user_rank("monnaie", user_id)
    if monnaie_rank:
        rank, value, total = monnaie_rank
        embed.add_field(name="**Whatoubiffs**", value=f"#{rank}/{total} — {value} 💰", inline=True)
    else:
        embed.add_field(name="**Whatoubiffs**", value="Non classé", inline=True)

    success_rank = get_user_rank("success", user_id)
    if success_rank:
        rank, value, total = success_rank
        embed.add_field(name="**Succès**", value=f"#{rank}/{total} — {value} succès", inline=True)
    else:
        embed.add_field(name="**Succès**", value="Non classé", inline=True)

    return embed


# ---------- Views ----------

class PaginatedLeaderboardView(discord.ui.View):
    def __init__(self, kind: str, page: int = 0):
        super().__init__(timeout=None)
        self.kind = kind
        self.page = page
        self._update_button_states()

    def _update_button_states(self):
        _, page, total_pages = build_paginated_embed(self.kind, self.page)
        self.page = page
        self.previous_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= total_pages - 1

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        embed, self.page, _ = build_paginated_embed(self.kind, self.page)
        self._update_button_states()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        embed, self.page, _ = build_paginated_embed(self.kind, self.page)
        self._update_button_states()
        await interaction.response.edit_message(embed=embed, view=self)


class LeaderboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Voir ma position", style=discord.ButtonStyle.primary, custom_id="see_position")
    async def my_position_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_position_embed(interaction.user)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Classement Whatoubiffs", style=discord.ButtonStyle.secondary, custom_id="ranking_wtbiffs")
    async def full_monnaie_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed, page, _ = build_paginated_embed("monnaie", 0)
        view = PaginatedLeaderboardView("monnaie", page)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Classement succès", style=discord.ButtonStyle.secondary, custom_id="ranking_successes")
    async def full_success_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed, page, _ = build_paginated_embed("success", 0)
        view = PaginatedLeaderboardView("success", page)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


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
    file = discord.File("Leaderboard.png", filename="leaderboards.png")
    msg = await channel.send(file=file, embed=build_summary_embed(), view=LeaderboardView())
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
        await message.edit(embed=build_summary_embed())
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