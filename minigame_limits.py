import discord
import json
import os
from discord.ext import tasks
import zoneinfo
import datetime


DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")
USER_DATA_PATH = os.path.join(os.path.dirname(__file__), "users.json")

# Statuts possibles, du plus faible au plus fort
STATUS_DEFAULT = "default"
STATUS_UNLIMITED = "unlimited"


def _load_users() -> dict:
    if os.path.exists(USER_DATA_PATH) and os.path.getsize(USER_DATA_PATH) > 0:
        with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_users(data: dict):
    with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_status(user_ID: int) -> str:
    data = _load_users()
    return data.get(str(user_ID), {}).get("status", STATUS_DEFAULT)


def set_status(user_ID: int, status: str) -> str:
    """status = 'default' ou 'unlimited'."""
    if status not in (STATUS_DEFAULT, STATUS_UNLIMITED):
        raise ValueError(f"Statut inconnu : {status}")

    data = _load_users()
    user_id = str(user_ID)
    data.setdefault(user_id, {})["status"] = status
    _save_users(data)
    return status


def has_unlimited(user_ID: int) -> bool:
    return get_status(user_ID) == STATUS_UNLIMITED


def mark_played(user_ID: int, game: str):
    """game = 'luckydice' ou 'mastermind' (ou tout autre identifiant de jeu à limite quotidienne)."""
    if has_unlimited(user_ID):
        return False  # on ne pose jamais le flag pour un joueur illimité

    data = _load_users()
    user_id = str(user_ID)
    data.setdefault(user_id, {})[f"has_played_{game}"] = True
    _save_users(data)

    return data[user_id][f"has_played_{game}"]


def can_play_today(user_ID: int, game: str):
    if has_unlimited(user_ID):
        return True

    data = _load_users()
    user_id = str(user_ID)

    if user_id not in data:
        return True

    return not data[user_id].get(f"has_played_{game}", False)


paris_tz = zoneinfo.ZoneInfo("Europe/Paris")

@tasks.loop(time=datetime.time(hour=10, minute=0, tzinfo=paris_tz))
async def reset_minigame():
    print("[INFO] RESET MINIGAME HAS_PLAYED FLAGS")

    data = _load_users()
    if not data:
        return

    for user_id in data:
        for key in list(data[user_id].keys()):
            if key.startswith("has_played_"):
                data[user_id][key] = False

    _save_users(data)


@reset_minigame.error
async def reset_minigame_error(error):
    print(f"[ERROR] reset_minigame a planté : {error}")