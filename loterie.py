import json
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import tasks

from tickets import create_ticket_channel

LOTERIE_PATH = os.path.join(os.path.dirname(__file__), "loterie.json")
LOTERIE_REF_PATH = os.path.join(os.path.dirname(__file__), "loterie_ref.json")

PARIS_TZ = ZoneInfo("Europe/Paris")
TIRAGE_WEEKDAY = 6   # 0 = lundi ... 6 = dimanche
TIRAGE_HOUR = 21

DEFAULT_LOTERIE = {
    "actif": True,
    "lot": "À définir",
    "tickets": {},
    "last_tirage_date": None,
    "next_message_at": None,
}

loterie_message_ref = {"channel_id": None, "message_id": None}


# ---------- Persistance loterie.json ----------

def load_loterie() -> dict:
    if os.path.exists(LOTERIE_PATH) and os.path.getsize(LOTERIE_PATH) > 0:
        with open(LOTERIE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    save_loterie(DEFAULT_LOTERIE)
    return DEFAULT_LOTERIE.copy()


def save_loterie(data: dict):
    with open(LOTERIE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_ticket(user_id: str):
    """Appelée depuis boutique.py à chaque achat réussi d'un ticket de loterie."""
    data = load_loterie()
    data["tickets"][user_id] = data["tickets"].get(user_id, 0) + 1
    save_loterie(data)



# ---------- Persistance du message ----------

def load_loterie_ref():
    if os.path.exists(LOTERIE_REF_PATH) and os.path.getsize(LOTERIE_REF_PATH) > 0:
        with open(LOTERIE_REF_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"channel_id": None, "message_id": None}


def save_loterie_ref():
    with open(LOTERIE_REF_PATH, "w", encoding="utf-8") as f:
        json.dump(loterie_message_ref, f)


loterie_message_ref.update(load_loterie_ref())


# ---------- Embed ----------

def get_next_tirage_date() -> datetime:
    now = datetime.now(PARIS_TZ)
    target = now.replace(hour=TIRAGE_HOUR, minute=0, second=0, microsecond=0)
    days_ahead = (TIRAGE_WEEKDAY - now.weekday()) % 7
    target += timedelta(days=days_ahead)
    if target <= now:
        target += timedelta(days=7)
    return target


def build_loterie_embed() -> discord.Embed:
    data = load_loterie()
    embed = discord.Embed(title="Loterie", color=discord.Color.purple())

    embed.add_field(name="Lot à gagner", value=data["lot"], inline=False)

    if data["actif"]:
        next_tirage = get_next_tirage_date()
        timestamp = int(next_tirage.timestamp())
        embed.add_field(name="Date du tirage", value=f"<t:{timestamp}:F>", inline=False)
    else:
        embed.add_field(name="Date du tirage", value="Aucun tirage prévu", inline=False)

    embed.add_field(name="Comment participer", value="Achète tes tickets dans la boutique !", inline=False)

    nb_participants = len(data["tickets"])
    nb_tickets = sum(data["tickets"].values())
    embed.add_field(name="Participants", value=str(nb_participants), inline=True)
    embed.add_field(name="Tickets vendus", value=str(nb_tickets), inline=True)

    return embed


async def update_loterie_message(bot: discord.Client):
    if loterie_message_ref["message_id"] is None:
        return False
    channel = bot.get_channel(loterie_message_ref["channel_id"])
    if channel is None:
        return False
    try:
        message = await channel.fetch_message(loterie_message_ref["message_id"])
        await message.edit(embed=build_loterie_embed())
        return True
    except discord.NotFound:
        return False


# ---------- Tirage ----------

def pick_winner(data: dict) -> str | None:
    pool = []
    for user_id, count in data["tickets"].items():
        pool.extend([user_id] * count)
    if not pool:
        return None
    return random.choice(pool)

async def effectuer_tirage(bot: discord.Client):
    data = load_loterie()

    if not data["actif"]:
        return

    winner_id = pick_winner(data)

    channel = bot.get_channel(loterie_message_ref["channel_id"])
    guild = channel.guild if channel else (bot.guilds[0] if bot.guilds else None)

    if winner_id and guild:
        member = guild.get_member(int(winner_id)) or await guild.fetch_member(int(winner_id))
        if member:
            if channel:
                await channel.send(f"{member.mention} a gagné la loterie et remporte {data['lot']} !")
            
            await create_ticket_channel(
                guild,
                member,
                f"loterie-gagnant-{member.name}",
                description=(
                    f"{member.mention} a gagné le tirage de la loterie !\n"
                    f"Lot : **{data['lot']}**"
                ),
            )

    # Reset pour le prochain tirage
    data["tickets"] = {}
    data["last_tirage_date"] = datetime.now(PARIS_TZ).date().isoformat()
    data["next_message_at"] = (datetime.now(PARIS_TZ) + timedelta(minutes=30)).isoformat()
    save_loterie(data)


async def send_new_loterie_message(bot: discord.Client):
    """Envoie un nouveau message loterie et vide l'échéance, appelé une fois le délai passé."""
    channel = bot.get_channel(loterie_message_ref["channel_id"])
    if channel is None:
        return

    msg = await channel.send(embed=build_loterie_embed())
    loterie_message_ref["channel_id"] = msg.channel.id
    loterie_message_ref["message_id"] = msg.id
    save_loterie_ref()

    data = load_loterie()
    data["next_message_at"] = None
    save_loterie(data)


# ---------- Commandes ----------

def setup(bot):

    @tasks.loop(minutes=1)
    async def refresh_loterie_embed():
        await update_loterie_message(bot)

    if not refresh_loterie_embed.is_running():
        refresh_loterie_embed.start()

    @tasks.loop(minutes=1)
    async def check_tirage():
        now = datetime.now(PARIS_TZ)
        data = load_loterie()
        today_str = now.date().isoformat()

        if (
            now.weekday() == TIRAGE_WEEKDAY
            and now.hour == TIRAGE_HOUR
            and now.minute == 0
            and data.get("last_tirage_date") != today_str
        ):
            await effectuer_tirage(bot)
            return  # évite de vérifier next_message_at sur le même tick

        next_message_at = data.get("next_message_at")
        if next_message_at and now >= datetime.fromisoformat(next_message_at):
            await send_new_loterie_message(bot)

    if not check_tirage.is_running():
        check_tirage.start()

    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="setup_loterie", description="Envoie le message de la loterie")
    async def setup_loterie(interaction: discord.Interaction):
        msg = await interaction.channel.send(embed=build_loterie_embed())
        loterie_message_ref["channel_id"] = msg.channel.id
        loterie_message_ref["message_id"] = msg.id
        save_loterie_ref()
        await interaction.response.send_message("Loterie envoyée ✅", ephemeral=True)

    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="loterie_activer_desactiver", description="Active ou désactive la loterie")
    async def loterie_activer_desactiver(interaction: discord.Interaction):
        data = load_loterie()
        data["actif"] = not data["actif"]
        save_loterie(data)
        await update_loterie_message(interaction.client)
        statut = "activée ✅" if data["actif"] else "désactivée ⏸️"
        await interaction.response.send_message(f"Loterie {statut}", ephemeral=True)

    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="loterie_nouveau_lot", description="Définit le lot à gagner")
    async def loterie_nouveau_lot(interaction: discord.Interaction, nom_du_lot: str):
        data = load_loterie()
        data["lot"] = nom_du_lot
        save_loterie(data)
        await update_loterie_message(interaction.client)
        await interaction.response.send_message(f"Lot mis à jour : **{nom_du_lot}** ✅", ephemeral=True)