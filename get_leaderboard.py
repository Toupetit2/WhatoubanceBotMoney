import json
import os

USERS_PATH = os.path.join(os.path.dirname(__file__), "users.json")

def get_whatoubiffs_leaderboard():
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    leaderboard = sorted(
        ((user_id, infos.get("monnaie", 0)) for user_id, infos in data.items()),
        key=lambda item: item[1],
        reverse=True
    )

    return leaderboard

def get_successes_leaderboard():
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    def count_successes(infos):
        success = infos.get("success", {})
        return sum(len(unlocked) for unlocked in success.values())

    leaderboard = sorted(
        ((user_id, count_successes(infos)) for user_id, infos in data.items()),
        key=lambda item: item[1],
        reverse=True
    )

    return leaderboard
