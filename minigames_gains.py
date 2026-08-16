import json

GAINS_FILE = "minigames_gains.json"


def get_gains(minigame: str):
    with open(GAINS_FILE, "r") as f:
        data = json.load(f)

    if minigame not in data:
        raise ValueError(f"Aucun gain défini pour le minijeu '{minigame}'")

    return data[minigame]