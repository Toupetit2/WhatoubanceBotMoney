import os
import sys
import asyncio

import discord
from discord import Intents
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("TOKEN_DISCORD")


async def corriger_message(message_id: int, channel_id: int):
    intents = Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"🔌 Connecté en tant que {client.user}")
        print(f"🔄 Suppression des boutons du message {message_id}...")

        channel = client.get_channel(channel_id)
        if channel is None:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                print(f"❌ Canal {channel_id} introuvable.")
                await client.close()
                return
            except discord.Forbidden:
                print(f"❌ Permission refusée pour accéder au canal {channel_id}.")
                await client.close()
                return

        try:
            message = await channel.fetch_message(message_id)
            await message.edit(view=discord.ui.View())
            print(f"✅ Boutons supprimés du message {message_id} !")
        except discord.NotFound:
            print(f"❌ Message {message_id} introuvable dans le canal {channel_id}.")
        except discord.Forbidden:
            print(f"❌ Permission refusée sur le message {message_id}.")
        except Exception as e:
            print(f"❌ Erreur : {e}")

        await client.close()

    await client.start(DISCORD_TOKEN)


def main():
    if len(sys.argv) < 3:
        print("Usage: python corriger_dernier_message.py <message_id> <channel_id>")
        sys.exit(1)

    message_id = int(sys.argv[1])
    channel_id = int(sys.argv[2])

    if not DISCORD_TOKEN:
        print("❌ Erreur : TOKEN_DISCORD non défini dans le .env")
        sys.exit(1)

    asyncio.run(corriger_message(message_id, channel_id))


if __name__ == "__main__":
    main()