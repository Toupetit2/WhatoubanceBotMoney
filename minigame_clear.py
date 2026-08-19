import os
import glob
import json
import discord
from discord import app_commands

MINIGAME_SCREENSHOTS_DIR = "minigame_screenshots"
MINIGAME_QUEUE_FILE = "minigame_queue.json"


def setup(bot):
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="delete_all_mastermind", description="Supprime tous les screenshots et vide la queue des minijeux")
    async def delete_all_mastermind_command(interaction: discord.Interaction):
        deleted_count = 0
        errors = []

        # Suppression de tous les fichiers dans minigame_screenshots
        if os.path.isdir(MINIGAME_SCREENSHOTS_DIR):
            for filepath in glob.glob(os.path.join(MINIGAME_SCREENSHOTS_DIR, "*")):
                try:
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                        deleted_count += 1
                except Exception as e:
                    errors.append(f"{os.path.basename(filepath)}: {e}")
        else:
            errors.append(f"Dossier introuvable : {MINIGAME_SCREENSHOTS_DIR}")

        # Vidage du fichier minigame_queue.json
        try:
            with open(MINIGAME_QUEUE_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception as e:
            errors.append(f"{MINIGAME_QUEUE_FILE}: {e}")

        if errors:
            error_details = "\n".join(errors)
            await interaction.response.send_message(
                f"⚠️ {deleted_count} fichier(s) supprimé(s), mais des erreurs sont survenues :\n{error_details}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"✅ {deleted_count} fichier(s) supprimé(s) et {MINIGAME_QUEUE_FILE} vidé",
                ephemeral=True
            )