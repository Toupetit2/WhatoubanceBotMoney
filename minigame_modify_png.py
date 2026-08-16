import random
import numpy as np
import os
from PIL import Image, ImageDraw

def process_minigame_screenshot(source_path: str, output_path: str):
    row_boundaries = [156, 316, 480, 644, 808, 972, 1136, 1300, 1456]
    shuffle_left = 228
    shuffle_right = 2500
    name_mask_left = 228
    name_mask_right = 450
    record_left = 600
    record_right = 800
    crop_box = (465, 156, 2300, 1500)
    bg_color = (15, 48, 88)
    img = Image.open(source_path)

    # 1. mélanger les lignes de joueurs, en gardant la trace des indices d'origine
    bands = []
    for i in range(8):
        top = row_boundaries[i]
        bottom = row_boundaries[i + 1]
        bands.append((i, img.crop((shuffle_left, top, shuffle_right, bottom))))
    random.shuffle(bands)

    # position finale -> index d'origine
    original_index_at = {new_position: original_index for new_position, (original_index, _) in enumerate(bands)}
    shuffled = img.copy()
    for new_position, (original_index, band) in enumerate(bands):
        shuffled.paste(band, (shuffle_left, row_boundaries[new_position]))

    # 2. anonymiser pseudo/avatar + supprimer la colonne record
    anonymized = shuffled.convert("RGB")
    draw = ImageDraw.Draw(anonymized)
    for i in range(8):
        top = row_boundaries[i]
        bottom = row_boundaries[i + 1]
        draw.rectangle([name_mask_left, top, name_mask_right, bottom], fill=bg_color)
        after_record = shuffled.crop((record_right, top, shuffled.width, bottom))
        draw.rectangle([record_left, top, shuffled.width, bottom], fill=bg_color)
        anonymized.paste(after_record, (record_left, top))

    # 3. crop final
    final = anonymized.crop(crop_box)

    # 4. détecter où s'arrête vraiment le contenu à droite (hors fond bleu uni)
    arr = np.array(final).astype(int)
    bg = np.array(bg_color)
    diff = np.abs(arr - bg).sum(axis=2)
    col_activity = (diff > 20).sum(axis=0) > 5  # au moins 5 pixels non-fond dans la colonne, pas juste 1 artefact isolé
    active_cols = np.where(col_activity)[0]
    content_right = int(active_cols.max()) if len(active_cols) else final.width

    margin = 35
    trimmed = final.crop((0, 0, min(content_right + margin, final.width), final.height))

    # 5. ajouter 35px de fond bleu à gauche
    padded = Image.new("RGB", (trimmed.width + margin, trimmed.height), bg_color)
    padded.paste(trimmed, (margin, 0))

    # 6. rectangle rouge de debug (dessiné en dernier, sur l'image finale paddée)
    draw_final = ImageDraw.Draw(padded)
    draw_final.rectangle([0, 490, padded.width, 490 + 160], fill=None, outline=(255, 0, 0), width=10)

    padded.save(output_path)

    return original_index_at

def crop_left_edge(source_path: str, output_path: str):
    px = 95
    img = Image.open(source_path)
    cropped = img.crop((px, 0, img.width, img.height))

    tmp_path = output_path + ".tmp"
    cropped.save(tmp_path, format="PNG")
    os.replace(tmp_path, output_path)