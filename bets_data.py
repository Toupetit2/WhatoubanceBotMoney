import json
import os
import time
import discord
import give

BETS_PATH = os.path.join(os.path.dirname(__file__), "bets.json")


def load_bets() -> dict:
    if os.path.exists(BETS_PATH) and os.path.getsize(BETS_PATH) > 0:
        with open(BETS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_bets(bets: dict):
    with open(BETS_PATH, "w", encoding="utf-8") as f:
        json.dump(bets, f, indent=4, ensure_ascii=False)


def create_bet(titre: str, description: str, secondes_avant_ouverture: int = 0, secondes_pour_parier: int = 0, createur_id: int = 0) -> str:
    
    bets = load_bets()

    bet_id = max((int(k) for k in bets.keys()), default=0) + 1
    bet_id_str = str(bet_id)

    date_ouverture = int(time.time()) + secondes_avant_ouverture
    date_fermeture = date_ouverture + (secondes_avant_ouverture + secondes_pour_parier)

    bets[bet_id_str] = {
        "titre": titre,
        "description": description,
        "choix": [],
        "date_ouverture": date_ouverture,
        "date_fermeture": date_fermeture,
        "statut": "a_venir",
        "resultat": None,
        "channel_id": None,
        "message_id": None,
        "createur_id": createur_id,
        "paris_joueurs": {}
    }

    save_bets(bets)
    return bet_id_str

def add_choice(bet_id: str, choice_label: str, cote: float):
    bets = load_bets()
    if bet_id in bets:
        if "choix" not in bets[bet_id]:
            bets[bet_id]["choix"] = []

        if len(bets[bet_id]["choix"]) >= 8:
            raise ValueError("Limite de 8 choix atteinte.")

        new_id = len(bets[bet_id]["choix"])

        bets[bet_id]["choix"].append({
            "id": new_id,
            "label": choice_label,
            "cote": cote
        })
        save_bets(bets)
    else:
        raise ValueError(f"Bet ID {bet_id} does not exist.")

def remove_choice(bet_id:str, id: int):
    bets = load_bets()
    if bet_id in bets and "choix" in bets[bet_id]:
        bets[bet_id]["choix"] = [choice for choice in bets[bet_id]["choix"] if choice["id"] != id]
        save_bets(bets)
    else:
        raise ValueError(f"Bet ID {bet_id} does not exist or has no choices.")

def set_bet_message_ref(bet_id: str, channel_id: int, message_id: int):
    bets = load_bets()
    if bet_id in bets:
        bets[bet_id]["channel_id"] = channel_id
        bets[bet_id]["message_id"] = message_id
        save_bets(bets)

def change_bet_dates(bet_id: str, temps_avant_ouverture: int, temps_pour_parier: int):
    bets = load_bets()
    if bet_id in bets:
        date_ouverture = int(time.time()) + temps_avant_ouverture
        date_fermeture = date_ouverture + temps_pour_parier

        bets[bet_id]["date_ouverture"] = date_ouverture
        bets[bet_id]["date_fermeture"] = date_fermeture
        save_bets(bets)
    else:
        raise ValueError(f"Bet ID {bet_id} does not exist.")


def refresh_bet_statuses() ->list[str]:
    """Vérifie tous les paris et met à jour leur statut selon les dates.
    Retourne la liste des bet_id dont le statut a changé."""
    bets = load_bets()
    now = int(time.time())
    changed = []

    for bet_id, bet in bets.items():
        statut = bet["statut"]

        if statut == "a_venir" and now >= bet["date_ouverture"]:
            bet["statut"] = "ouvert"
            changed.append(bet_id)

        elif statut == "ouvert" and now >= bet["date_fermeture"]:
            bet["statut"] = "ferme"
            changed.append(bet_id)

    if changed:
        save_bets(bets)

    return changed
def place_bet(bet_id: str, member: discord.Member, choix_id: int, montant: int):
    bets = load_bets()
    if bet_id not in bets:
        raise ValueError(f"Bet ID {bet_id} does not exist.")

    bet = bets[bet_id]
    if bet["statut"] != "ouvert":
        raise ValueError("Le pari n'est pas ouvert pour les mises.")

    if choix_id not in [c["id"] for c in bet["choix"]]:
        raise ValueError("Choix invalide pour ce pari.")

    if montant <= 0:
        raise ValueError("Le montant doit être positif.")

    if give.get_user_coins(member) < montant:
        raise ValueError("Tu n'as pas assez de WhatouBiffs pour ce pari.")

    give.give_coins(-montant, member)  # ✅ déduit la mise

    bets[bet_id]["paris_joueurs"][str(member.id)] = {
        "choix_id": choix_id,
        "montant": montant
    }
    save_bets(bets)


def add_to_bet(bet_id: str, member: discord.Member, montant: int):
    bets = load_bets()
    if bet_id not in bets:
        raise ValueError(f"Bet ID {bet_id} does not exist.")

    bet = bets[bet_id]
    if bet["statut"] != "ouvert":
        raise ValueError("Le pari n'est pas ouvert pour les mises.")

    if str(member.id) not in bet["paris_joueurs"]:
        raise ValueError("Aucun pari existant pour cet utilisateur.")

    if montant <= 0:
        raise ValueError("Le montant doit être positif.")

    if give.get_user_coins(member) < montant:
        raise ValueError("Tu n'as pas assez de WhatouBiffs pour ce pari.")

    give.give_coins(-montant, member) 

    bets[bet_id]["paris_joueurs"][str(member.id)]["montant"] += montant
    save_bets(bets)


def resolve_bet(bet_id: str, choix_gagnant_id: int) -> dict:
    """Résout un pari : désigne le gagnant, calcule les gains (sans les distribuer).
    Retourne {user_id: gain} pour les joueurs gagnants."""
    bets = load_bets()

    if bet_id not in bets:
        raise ValueError(f"Bet ID {bet_id} does not exist.")

    bet = bets[bet_id]

    if bet["statut"] != "ferme":
        raise ValueError("Le pari doit être fermé avant d'être résolu.")

    if choix_gagnant_id not in [c["id"] for c in bet["choix"]]:
        raise ValueError("Choix gagnant invalide pour ce pari.")

    cote_gagnante = next(c["cote"] for c in bet["choix"] if c["id"] == choix_gagnant_id)

    gains = {}
    for user_id, pari in bet["paris_joueurs"].items():
        if pari["choix_id"] == choix_gagnant_id:
            gain = int(pari["montant"] * cote_gagnante)
            gains[user_id] = gain

    bet["statut"] = "resolu"
    bet["resultat"] = choix_gagnant_id

    save_bets(bets)

    return gains


def close_bet(bet_id: str):
    bets = load_bets()
    if bet_id not in bets:
        raise ValueError(f"Bet ID {bet_id} does not exist.")

    bet = bets[bet_id]

    if bet["statut"] not in ("a_venir", "ouvert"):
        raise ValueError("Ce pari ne peut pas être fermé (il est déjà fermé, résolu ou annulé).")

    bet["statut"] = "ferme"
    save_bets(bets) 