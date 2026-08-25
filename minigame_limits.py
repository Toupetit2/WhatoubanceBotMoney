import discord
import json
import os
from discord.ext import tasks
import zoneinfo
import datetime


DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")


def mark_played(user_ID: int):
    data = {}

    if os.path.exists(DATA_PATH) and os.path.getsize(DATA_PATH) > 0:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    
    user_id = str(user_ID)

    if user_id not in data:
        data[user_id] = {"has_played": True}

    if data[user_id].get("has_played") is None :
        data[user_id]["has_played"] = True
    else:
        data[user_id]["has_played"] = True

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return data[user_id]["has_played"]

def can_play_today(user_ID: int):
    data = {}

    if os.path.exists(DATA_PATH) and os.path.getsize(DATA_PATH) > 0:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    
    user_id = str(user_ID)

    if user_id not in data:
        return True

    return not data[user_id].get("has_played", False)


paris_tz = zoneinfo.ZoneInfo("Europe/Paris")

@tasks.loop(time=datetime.time(hour=10, minute=0, tzinfo=paris_tz))
async def reset_minigame():
    print("[INFO] RESET MINIGAME HAS_PLAYED FLAGS")

    if os.path.exists(DATA_PATH) and os.path.getsize(DATA_PATH) > 0:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        for user_id in data:
            data[user_id]["has_played"] = False

        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


@reset_minigame.error
async def reset_minigame_error(error):
    print(f"[ERROR] reset_minigame a planté : {error}")