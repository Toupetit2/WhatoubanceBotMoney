import json
import os

TITLES_PATH = "titles.json"
USER_TITLES_PATH = "user_titles.json"
USERS_PATH = "users.json"

def add_title(title: str, description: str):
    title_data = {}

    if os.path.exists(TITLES_PATH) and os.path.getsize(TITLES_PATH) > 0:
        with open(TITLES_PATH, "r", encoding="utf-8") as f:
            title_data = json.load(f)

    title_data[title] = {
        "description": description
    }

    with open(TITLES_PATH, "w", encoding="utf-8") as f:
        json.dump(title_data, f, indent=4, ensure_ascii=False)


def list_titles():
    """Catalogue de tous les titres custom disponibles."""
    if os.path.exists(TITLES_PATH) and os.path.getsize(TITLES_PATH) > 0:
        with open(TITLES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def remove_title(title: str):
    if not (os.path.exists(TITLES_PATH) and os.path.getsize(TITLES_PATH) > 0):
        return False

    with open(TITLES_PATH, "r", encoding="utf-8") as f:
        title_data = json.load(f)

    if title not in title_data:
        return False

    del title_data[title]

    with open(TITLES_PATH, "w", encoding="utf-8") as f:
        json.dump(title_data, f, indent=4, ensure_ascii=False)

    # Retire le titre à tous les membres qui l'avaient
    if os.path.exists(USER_TITLES_PATH) and os.path.getsize(USER_TITLES_PATH) > 0:
        with open(USER_TITLES_PATH, "r", encoding="utf-8") as f:
            user_titles = json.load(f)

        user_titles = {uid: t for uid, t in user_titles.items() if t != title}

        with open(USER_TITLES_PATH, "w", encoding="utf-8") as f:
            json.dump(user_titles, f, indent=4, ensure_ascii=False)

    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            users_data = json.load(f)

        for user_data in users_data.values():
            if user_data.get("equiped_title") == title:
                user_data["equiped_title"] = ""

        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=4, ensure_ascii=False)

    return True


def give_title(member, title: str):
    """
    Donne le titre au membre.
    Renvoie None si le titre n'existe pas dans le catalogue,
    True si le membre l'avait déjà,
    False si c'est une nouvelle attribution.
    """
    data = list_titles()

    if title not in data:
        return None

    user_titles = {}
    if os.path.exists(USER_TITLES_PATH) and os.path.getsize(USER_TITLES_PATH) > 0:
        with open(USER_TITLES_PATH, "r", encoding="utf-8") as f:
            user_titles = json.load(f)

    already_had = user_titles.get(str(member.id)) == title

    user_titles[str(member.id)] = title

    with open(USER_TITLES_PATH, "w", encoding="utf-8") as f:
        json.dump(user_titles, f, indent=4, ensure_ascii=False)

    return already_had


def take_title(member, title: str):
    """
    Retire le titre `title` du membre, uniquement si c'est bien celui qu'il possède.
    Renvoie True si retiré, False si le membre n'a pas ce titre.
    """
    if not (os.path.exists(USER_TITLES_PATH) and os.path.getsize(USER_TITLES_PATH) > 0):
        return False

    with open(USER_TITLES_PATH, "r", encoding="utf-8") as f:
        user_titles = json.load(f)

    if user_titles.get(str(member.id)) != title:
        return False

    del user_titles[str(member.id)]

    with open(USER_TITLES_PATH, "w", encoding="utf-8") as f:
        json.dump(user_titles, f, indent=4, ensure_ascii=False)

    with open(USERS_PATH, "r", encoding="utf-8") as f:
        users_data = json.load(f)

    user_data = users_data.get(str(member.id))

    if user_data and user_data.get("equiped_title") == title:
        user_data["equiped_title"] = ""

        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=4, ensure_ascii=False)

    return True

def get_given_titles(member) -> list[str]:
    """Renvoie la liste des titres custom donnés au membre (0 ou 1 actuellement)."""
    if os.path.exists(USER_TITLES_PATH) and os.path.getsize(USER_TITLES_PATH) > 0:
        with open(USER_TITLES_PATH, "r", encoding="utf-8") as f:
            user_titles = json.load(f)

        title = user_titles.get(str(member.id))
        if title:
            return [title]

    return []