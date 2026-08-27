import json

USERS_PATH = "users.json"

with open(USERS_PATH, "r", encoding="utf-8") as f:
    users = json.load(f)

for user_data in users.values():
    stats = user_data.get("stats", {})
    if "minigame1_average_error" in stats:
        stats["minigame1_average_error"] = 0  # ou recalculer si tu gardes un historique par coup

with open(USERS_PATH, "w", encoding="utf-8") as f:
    json.dump(users, f, indent=4, ensure_ascii=False)