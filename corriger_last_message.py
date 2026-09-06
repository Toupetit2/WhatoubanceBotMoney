import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import asyncio

import discord
from discord import Intents

PARIS_TZ = ZoneInfo("Europe/Paris")

DISCORD_TOKEN = os.getenv("TOKEN_DISCORD")
GUILD_ID = int(os.getenv("GUILD_ID"))

async def corriger_message(message_id: int, channel_id: int = None):
    """Supprime juste les boutons du message."""
    
    # Si channel_id n'est pas fourni, utiliser celui de l'archive
    if channel_id is None:
        channel_id = archive.get("channel_id")
    
    if not channel_id:
        print("❌ ID du canal introuvable.")
        return False
    
    print(f"🔄 Suppression des boutons du message {message_id}...")
    
    intents = Intents.default()
    client = discord.Client(intents=intents)
    
    async with client:
        await client.login(DISCORD_TOKEN)
        
        channel = client.get_channel(channel_id)
        if channel is None:
            print(f"❌ Canal {channel_id} introuvable.")
            return False
        
        try:
            message = await channel.fetch_message(message_id)
            await message.edit(view=discord.ui.View())  # Juste ça !
            print(f"✅ Boutons supprimés du message {message_id} !")
            return True
            
        except discord.NotFound:
            print(f"❌ Message {message_id} introuvable.")
            return False
        except discord.Forbidden:
            print(f"❌ Permission refusée.")
            return False
        except Exception as e:
            print(f"❌ Erreur : {e}")
            return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python corriger_dernier_message.py <message_id> [channel_id]")
        print("")
        print("Exemple:")
        print("  python corriger_dernier_message.py 123456789")
        print("  python corriger_dernier_message.py 123456789 987654321")
        sys.exit(1)
    
    message_id = int(sys.argv[1])
    channel_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if not DISCORD_TOKEN:
        print("❌ Erreur : DISCORD_TOKEN non défini.")
        print("Définissez la variable d'environnement DISCORD_TOKEN avant de lancer le script.")
        sys.exit(1)
    
    asyncio.run(corriger_message(message_id, channel_id))


if __name__ == "__main__":
    main()