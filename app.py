import os
import dotenv
import asyncio
import signal
import logging
import discord

from bot import Bot
from bot_setup import bot_setup
from minigame_api import shutdown_browser  # ton module screenshot.py

dotenv.load_dotenv()

TOKEN = os.getenv("TOKEN_DISCORD")

if not TOKEN:
    raise ValueError("TOKEN_DISCORD est introuvable dans les variables d'environnement.")

bot = Bot()

log = logging.getLogger("app")

async def cleanup():
    log.info("🧹 Fermeture propre en cours...")
    await shutdown_browser()
    if not bot.is_closed():
        await bot.close()
    log.info("✅ Nettoyage terminé.")

async def main():
    discord.utils.setup_logging(level=logging.INFO)
    await bot_setup(bot)

    import platform

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _on_signal(sig):
        log.info(f"Signal {sig.name} reçu, arrêt en cours...")
        stop_event.set()

    # SIGTERM = envoyé par systemctl restart/stop
    # SIGINT  = Ctrl+C
    # add_signal_handler n'est pas supporté sur Windows
    if platform.system() != "Windows":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _on_signal, sig)

    async with bot:
        bot_task = asyncio.create_task(bot.start(TOKEN))
        stop_task = asyncio.create_task(stop_event.wait())

        done, pending = await asyncio.wait(
            {bot_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
        )

        await cleanup()

        for task in pending:
            task.cancel()

        # Si c'est bot_task qui a fini en premier (crash/déconnexion),
        # on remonte l'exception éventuelle pour la voir dans les logs
        if bot_task in done and not bot_task.cancelled():
            exc = bot_task.exception()
            if exc:
                raise exc

asyncio.run(main())