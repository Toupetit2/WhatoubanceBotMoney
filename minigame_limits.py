import discord
import json
import os
from discord.ext import tasks
import zoneinfo
import datetime


DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")
USER_DATA_PATH = os.path.join(os.path.dirname(__file__), "users.json")


def mark_played(user_ID: int, game: str):
    """game = 'luckydice' ou 'mastermind' (ou tout autre identifiant de jeu à limite quotidienne)."""
    data = {}

    if os.path.exists(USER_DATA_PATH) and os.path.getsize(USER_DATA_PATH) > 0:
        with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    user_id = str(user_ID)

    if user_id not in data:
        data[user_id] = {}

    data[user_id][f"has_played_{game}"] = True

    with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return data[user_id][f"has_played_{game}"]


def can_play_today(user_ID: int, game: str):
    data = {}

    if os.path.exists(USER_DATA_PATH) and os.path.getsize(USER_DATA_PATH) > 0:
        with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    user_id = str(user_ID)

    if user_id not in data:
        return True

    return not data[user_id].get(f"has_played_{game}", False)


paris_tz = zoneinfo.ZoneInfo("Europe/Paris")

@tasks.loop(time=datetime.time(hour=10, minute=0, tzinfo=paris_tz))
async def reset_minigame():
    print("[INFO] RESET MINIGAME HAS_PLAYED FLAGS")

    if os.path.exists(USER_DATA_PATH) and os.path.getsize(USER_DATA_PATH) > 0:
        with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        for user_id in data:
            for key in list(data[user_id].keys()):
                if key.startswith("has_played_"):
                    data[user_id][key] = False

        with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


@reset_minigame.error
async def reset_minigame_error(error):
    print(f"[ERROR] reset_minigame a planté : {error}")