import os
import dotenv
import asyncio
from bot import Bot
from bot_setup import bot_setup

dotenv.load_dotenv()

TOKEN = os.getenv("TOKEN_DISCORD")

if not TOKEN:
    raise ValueError("TOKEN_DISCORD est introuvable dans les variables d'environnement.")

bot = Bot()
    
async def main():
    await bot_setup(bot)

    async with bot:
        await bot.start(TOKEN)

asyncio.run(main())

