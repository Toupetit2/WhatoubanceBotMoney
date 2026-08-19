import os
import json
import asyncio
import uuid
import minigame_api
import minigame_modify_png

SCREENS_DIR = "minigame_screenshots"
QUEUE_FILE = "minigame_queue.json"
TARGET_SIZE = 10

os.makedirs(SCREENS_DIR, exist_ok=True)


def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE, "r") as f:
        content = f.read().strip()
        if not content:
            return []
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            print(f"[WARNING] {QUEUE_FILE} corrompu, réinitialisation à vide")
            return []


def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def queue_size():
    return len(load_queue())


async def generate_one():
    game_id = await asyncio.to_thread(minigame_api.get_random_gameid)

    entry_id = uuid.uuid4().hex
    raw_path = os.path.join(SCREENS_DIR, f"{entry_id}_raw.png")
    final_path = os.path.join(SCREENS_DIR, f"{entry_id}_final.png")

    await minigame_api.screenshot_url(
        f"https://tactics.tools/player/euw/A/A/{game_id}",
        raw_path
    )

    before_placements = await asyncio.to_thread(
        minigame_modify_png.process_minigame_screenshot,
        raw_path,
        final_path
    )
    answer = before_placements[3] + 1

    minigame_modify_png.crop_left_edge(raw_path, raw_path)

    queue = load_queue()
    queue.append({
        "id": entry_id,
        "answer": answer,
        "raw_path": raw_path,
        "final_path": final_path,
    })
    save_queue(queue)

    return entry_id


async def refill_queue():
    print("refill Q")
    while queue_size() < TARGET_SIZE:
        try:
            entry_id = await generate_one()
            print(f"[INFO] minijeu pré-généré ajouté : {entry_id} (file: {queue_size()}/{TARGET_SIZE})")
        except Exception as e:
            print(f"[ERROR] échec génération minijeu : {e}")
            break


def pop_one():
    queue = load_queue()
    if not queue:
        return None

    entry = queue.pop(0)
    save_queue(queue)
    return entry