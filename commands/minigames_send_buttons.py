import discord
import json
import os
from discord import app_commands
from discord.ext import tasks
import zoneinfo
import datetime

from minigames_view import MinigamesView

REF_PATH = os.path.join(os.path.dirname(__file__), "minigames_panel_ref.json")
PARIS_TZ = zoneinfo.ZoneInfo("Europe/Paris")

minigames_message_ref = {"channel_id": None, "message_id": None}


def load_ref():
    if os.path.exists(REF_PATH) and os.path.getsize(REF_PATH) > 0:
        with open(REF_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"channel_id": None, "message_id": None}


def save_ref():
    with open(REF_PATH, "w", encoding="utf-8") as f:
        json.dump(minigames_message_ref, f)


minigames_message_ref.update(load_ref())


async def send_minigames_panel(channel: discord.abc.Messageable):
    image = discord.File("Images/wtbgame.jpg", filename="image.jpg")
    msg = await channel.send("", file=image, view=MinigamesView())
    minigames_message_ref["channel_id"] = msg.channel.id
    minigames_message_ref["message_id"] = msg.id
    save_ref()
    return msg


async def refresh_minigames_panel(bot: discord.Client):
    if minigames_message_ref["message_id"] is None:
        return False

    channel = bot.get_channel(minigames_message_ref["channel_id"])
    if channel is None:
        return False

    try:
        old_message = await channel.fetch_message(minigames_message_ref["message_id"])
        await old_message.delete()
    except discord.NotFound:
        pass

    await send_minigames_panel(channel)
    return True


def setup(bot):
    @app_commands.guild_only()
    @bot.tree.command(name="setup_minigames", description="Lance le panneau des minijeu")
    async def setup_minigames_command(interaction: discord.Interaction):
        await send_minigames_panel(interaction.channel)
        await interaction.response.send_message("Panneau envoyé !", ephemeral=True)

    @tasks.loop(time=datetime.time(hour=10, minute=0, tzinfo=PARIS_TZ))
    async def daily_refresh_minigames_panel():
        await refresh_minigames_panel(bot)

    if not daily_refresh_minigames_panel.is_running():
        daily_refresh_minigames_panel.start()

    @daily_refresh_minigames_panel.error
    async def daily_refresh_minigames_panel_error(error):
        print(f"[ERROR] daily_refresh_minigames_panel a planté : {error}")