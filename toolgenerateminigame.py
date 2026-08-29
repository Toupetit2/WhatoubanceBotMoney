import os
import sys
import asyncio
import minigame_api
import minigame_modify_png

OUTPUT_PATH = "minigame.png"
RAW_PATH = "minigame_raw.png"


async def generate_from_id(game_id: str, region: str = "euw"):
    """
    Génère un minijeu à partir d'un game_id choisi manuellement,
    et enregistre le résultat final dans minigame.png.
    """
    url = f"https://tactics.tools/player/{region}/A/A/{game_id}"

    ok = await minigame_api.screenshot_url(url, RAW_PATH)
    if not ok:
        print(f"[ERROR] Échec du screenshot pour game_id={game_id} (layout à 2 lignes ou URL invalide ?)")
        if os.path.exists(RAW_PATH):
            os.remove(RAW_PATH)
        return None

    before_placements = await asyncio.to_thread(
        minigame_modify_png.process_minigame_screenshot,
        RAW_PATH,
        OUTPUT_PATH
    )

    if before_placements is None:
        print(f"[ERROR] Traitement de l'image échoué pour game_id={game_id}")
        for path in (RAW_PATH, OUTPUT_PATH):
            if os.path.exists(path):
                os.remove(path)
        return None

    answer = before_placements[3] + 1

    # on nettoie aussi le bord gauche du raw si besoin (comme dans le script original)
    minigame_modify_png.crop_left_edge(RAW_PATH, RAW_PATH)

    print(f"[INFO] Minijeu généré avec succès : {OUTPUT_PATH}")
    print(f"[INFO] Réponse attendue (placement) : {answer}")

    return {
        "game_id": game_id,
        "answer": answer,
        "raw_path": RAW_PATH,
        "final_path": OUTPUT_PATH,
    }


def main():
    if len(sys.argv) < 2:
        game_id = input("Entre le game_id : ").strip()
    else:
        game_id = sys.argv[1]

    region = sys.argv[2] if len(sys.argv) > 2 else "euw"

    result = asyncio.run(generate_from_id(game_id, region))

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()