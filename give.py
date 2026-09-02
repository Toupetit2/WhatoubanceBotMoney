import discord
import json
import os

import custom_titles as titles

USERS_PATH = os.path.join(os.path.dirname(__file__), "users.json")
SUCCESSES_PATH = os.path.join(os.path.dirname(__file__), "successes.json")


def give_coins(amount: int, member: discord.Member):
    data = {}

    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    user_id = str(member.id)

    if user_id not in data:
        data[user_id] = {"monnaie": 50}

    if data[user_id].get("monnaie") is None :
        data[user_id]["monnaie"] = amount
    else:
        data[user_id]["monnaie"] += amount

    if data[user_id]["monnaie"] < 0:
        data[user_id]["monnaie"] = 0
    
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return data[user_id]["monnaie"]

def get_user_coins(member: discord.Member):
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        user_id = str(member.id)

        if user_id in data and "monnaie" in data[user_id]:
            return data[user_id]["monnaie"]

    return 0


def add_success(name: str, category: str, description: str, title: str):
    success_data = {}

    if os.path.exists(SUCCESSES_PATH) and os.path.getsize(SUCCESSES_PATH) > 0:
        with open(SUCCESSES_PATH, "r", encoding="utf-8") as f:
            success_data = json.load(f)

    if category not in success_data:
        success_data[category] = {}

    if name not in success_data[category]:
        success_data[category][name] = {
            "description": description,
            "title": title
        }
    else:
        success_data[category][name]["description"] = description
        success_data[category][name]["title"] = title

    with open(SUCCESSES_PATH, "w", encoding="utf-8") as f:
        json.dump(success_data, f, indent=4, ensure_ascii=False)

def list_successes():
    """Catalogue de tous les succès possibles."""
    if os.path.exists(SUCCESSES_PATH) and os.path.getsize(SUCCESSES_PATH) > 0:
        with open(SUCCESSES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def remove_success(name: str, category: str):
    if os.path.exists(SUCCESSES_PATH) and os.path.getsize(SUCCESSES_PATH) > 0:
        with open(SUCCESSES_PATH, "r", encoding="utf-8") as f:
            success_data = json.load(f)

        if category in success_data and name in success_data[category]:
            del success_data[category][name]

            with open(SUCCESSES_PATH, "w", encoding="utf-8") as f:
                json.dump(success_data, f, indent=4, ensure_ascii=False)


def unlock_success(member: discord.Member, name: str, category: str):
    """Débloque un succès POUR CET UTILISATEUR (stocké dans users.json).
    Retourne True si le succès vient d'être débloqué, False s'il l'était déjà."""
    data = {}
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    user_id = str(member.id)
    if user_id not in data:
        data[user_id] = {"monnaie": 50}
    if "success" not in data[user_id]:
        data[user_id]["success"] = {}
    if category not in data[user_id]["success"]:
        data[user_id]["success"][category] = []

    already_unlocked = name in data[user_id]["success"][category]

    if not already_unlocked:
        data[user_id]["success"][category].append(name)

        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    newly_unlocked = not already_unlocked
    return newly_unlocked

async def unlock_success_and_notify(member: discord.Member, name: str, category: str, interaction: discord.Interaction):
    newly_unlocked = unlock_success(member, name, category)

    if newly_unlocked:
        all_successes = list_successes()
        success_info = all_successes.get(category, {}).get(name, {})
        titre = success_info.get("title")

        message = ""
        if titre:
            message += f"Nouveau titre disponible : **{titre}** ! (tu peux le sélectionner dans ton profil)"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    return newly_unlocked


def list_successes_member(member: discord.Member):
    """Succès débloqués par l'utilisateur, avec titre/description tirés du catalogue."""
    data = {}
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    user_id = str(member.id)
    unlocked = data.get(user_id, {}).get("success", {})
    catalog = list_successes()

    result = []
    for category, names in unlocked.items():
        for name in names:
            details = catalog.get(category, {}).get(name)
            if details:
                result.append(f"{category} - {name}: {details['title']} - {details['description']}")
    return result





def get_success_progress(member: discord.Member, category: str):
    data = {}
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    user_id = str(member.id)
    unlocked_count = len(data.get(user_id, {}).get("success", {}).get(category, []))
    total_count = len(list_successes().get(category, {}))
    return unlocked_count, total_count


def get_global_success_progress(member: discord.Member):
    catalog = list_successes()
    data = {}
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    user_id = str(member.id)
    unlocked = data.get(user_id, {}).get("success", {})

    total_unlocked = sum(len(v) for v in unlocked.values())
    total_possible = sum(len(v) for v in catalog.values())
    return total_unlocked, total_possible


def get_equiped_title(member: discord.Member):
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        user_id = str(member.id)

        if user_id in data and "equiped_title" in data[user_id]:
            if data[user_id]["equiped_title"] is not "":
                return data[user_id]["equiped_title"]

    return "Aucun titre équipé"


def set_equiped_title(member: discord.Member, title: str):
    data = {}
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    user_id = str(member.id)
    if user_id not in data:
        data[user_id] = {"monnaie": 50}

    data[user_id]["equiped_title"] = title

    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_unlocked_titles(member: discord.Member) -> list[str]:

    data = {}
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    user_id = str(member.id)
    user_data = data.get(user_id, {})
    unlocked_by_category = user_data.get("success", {})

    all_successes = list_successes()

    titles_list = []
    for category, unlocked_ids in unlocked_by_category.items():
        category_successes = all_successes.get(category, {})
        for success_id in unlocked_ids:
            success_info = category_successes.get(success_id, {})
            titre = success_info.get("title")
            if titre:
                titles_list.append(titre)

    titles_list.extend(titles.get_given_titles(member))

    return titles_list


# ---------------- Statistiques ----------------

def set_statistic(member: discord.Member, statistic: str, value):
    data = {}
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    user_id = str(member.id)
    if user_id not in data:
        data[user_id] = {"monnaie": 50}
    if "stats" not in data[user_id]:
        data[user_id]["stats"] = {}

    data[user_id]["stats"][statistic] = value

    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return value


def get_statistic(member: discord.Member, statistic: str, default=0):
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        user_id = str(member.id)
        return data.get(user_id, {}).get("stats", {}).get(statistic, default)

    return default


def increment_statistic(member: discord.Member, statistic: str, amount=1):
    current = get_statistic(member, statistic, 0)
    return set_statistic(member, statistic, current + amount)


def update_daily_streak(member: discord.Member):
    from datetime import date, timedelta

    today = date.today().isoformat()
    last_played = get_statistic(member, "last_played_date", None)

    if last_played == today:
        return get_statistic(member, "current_streak", 0)

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    new_streak = get_statistic(member, "current_streak", 0) + 1 if last_played == yesterday else 1

    set_statistic(member, "current_streak", new_streak)
    set_statistic(member, "last_played_date", today)

    if new_streak > get_statistic(member, "best_streak", 0):
        set_statistic(member, "best_streak", new_streak)

    return new_streak


def get_favorite_lucky_dice(member: discord.Member):
    choices = {
        "Golden Gamble": get_statistic(member, "golden_gamble_game_count"),
        "Magic Roll": get_statistic(member, "magic_roll_game_count"),
        "Loaded Dice": get_statistic(member, "loaded_dice_game_count"),
    }
    if all(v == 0 for v in choices.values()):
        return "Aucun"

    return max(choices, key=choices.get)


def register_dice_roll(member: discord.Member, face: int):
    data = {}
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    user_id = str(member.id)
    if user_id not in data:
        data[user_id] = {"monnaie": 50}
    if "stats" not in data[user_id]:
        data[user_id]["stats"] = {}
    if "loaded_dice_faces" not in data[user_id]["stats"]:
        data[user_id]["stats"]["loaded_dice_faces"] = {str(i): 0 for i in range(1, 7)}

    data[user_id]["stats"]["loaded_dice_faces"][str(face)] += 1

    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_dice_faces_stats(member: discord.Member):
    return get_statistic(member, "loaded_dice_faces", {str(i): 0 for i in range(1, 7)})


def register_bet(member: discord.Member, amount: int, won: bool, gain: int):
    increment_statistic(member, "betting_total_bets", 1)
    increment_statistic(member, "betting_total_wagered", amount)
    increment_statistic(member, "betting_net_whatoubiffs", gain)

    if won:
        increment_statistic(member, "betting_total_wins", 1)

    if gain > get_statistic(member, "betting_best_gain", 0):
        set_statistic(member, "betting_best_gain", gain)

    if gain < get_statistic(member, "betting_worst_loss", 0):
        set_statistic(member, "betting_worst_loss", gain)


def get_betting_win_rate(member: discord.Member):
    total = get_statistic(member, "betting_total_bets", 0)
    if total == 0:
        return 0.0
    wins = get_statistic(member, "betting_wins", 0)
    return round((wins / total) * 100, 1)

def has_success(member: discord.Member, category: str, name: str) -> bool:
    import json, os
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        user_id = str(member.id)
        return name in data.get(user_id, {}).get("success", {}).get(category, [])
    return False