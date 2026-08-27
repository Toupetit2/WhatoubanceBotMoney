"""
Script de migration à lancer UNE SEULE FOIS.

1. Migre les anciens titres achetés en boutique (stockés dans
   "titres_possedes") vers le nouveau système de succès unifié
   (user["success"]["Boutique"]).
2. Remet à zéro la stat "minigame1_average_error", corrompue par
   l'ancienne formule de calcul (elle ne représentait plus une
   moyenne bornée entre 0 et 8).

Usage :
    cd /chemin/vers/ton/bot   # là où se trouvent users.json, boutique.py...
    python3 migration.py

Le script fait une sauvegarde de users.json avant toute modification
(users.json.bak), affiche un résumé, et ne modifie rien si aucune
donnée concernée n'est trouvée.
"""

import json
import os
import shutil
import sys

USERS_PATH = "users.json"
BOUTIQUE_PATH = "boutique.json"


def load_json(path: str) -> dict:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def migrate_titres_possedes(users: dict, boutique: dict) -> int:
    """Migre 'titres_possedes' vers success['Boutique']. Retourne le nombre
    de titres migrés."""
    migrated_count = 0

    for user_id, user_data in users.items():
        titres = user_data.pop("titres_possedes", None)
        if not titres:
            continue

        succes = user_data.setdefault("success", {}).setdefault("Boutique", [])

        for nom in titres:
            item = next(
                (
                    i
                    for items in boutique.values()
                    for i in items
                    if i.get("titre") and i["nom"] == nom
                ),
                None,
            )
            if item is None:
                print(f"  ⚠️  Titre '{nom}' (user {user_id}) introuvable dans la boutique actuelle, ignoré.")
                continue
            if item["id"] not in succes:
                succes.append(item["id"])
                migrated_count += 1
                print(f"  ✅ user {user_id} : titre '{nom}' -> succès Boutique '{item['id']}'")

    return migrated_count


def reset_minigame1_average_error(users: dict) -> int:
    """Remet à zéro la stat corrompue. Retourne le nombre d'utilisateurs concernés."""
    reset_count = 0

    for user_id, user_data in users.items():
        stats = user_data.get("stats", {})
        if "minigame1_average_error" in stats and stats["minigame1_average_error"] != 0:
            old_value = stats["minigame1_average_error"]
            stats["minigame1_average_error"] = 0
            reset_count += 1
            print(f"  ✅ user {user_id} : minigame1_average_error {old_value} -> 0")

    return reset_count


def main():
    if not os.path.exists(USERS_PATH):
        print(f"❌ Fichier '{USERS_PATH}' introuvable dans le dossier courant ({os.getcwd()}).")
        print("   Lance ce script depuis le dossier où se trouve users.json.")
        sys.exit(1)

    # Sauvegarde avant toute modification
    backup_path = USERS_PATH + ".bak"
    shutil.copyfile(USERS_PATH, backup_path)
    print(f"📦 Sauvegarde créée : {backup_path}\n")

    users = load_json(USERS_PATH)
    boutique = load_json(BOUTIQUE_PATH)

    print("== Migration des titres boutique -> succès ==")
    migrated_titles = migrate_titres_possedes(users, boutique)
    if migrated_titles == 0:
        print("  (rien à migrer)")

    print("\n== Reset de la stat minigame1_average_error ==")
    reset_stats = reset_minigame1_average_error(users)
    if reset_stats == 0:
        print("  (rien à réinitialiser)")

    save_json(USERS_PATH, users)

    print("\n---")
    print(f"Titres migrés     : {migrated_titles}")
    print(f"Stats réinitialisées : {reset_stats}")
    print(f"Fichier mis à jour : {USERS_PATH}")
    print(f"En cas de problème, restaure la sauvegarde avec :")
    print(f"  cp {backup_path} {USERS_PATH}")


if __name__ == "__main__":
    main()