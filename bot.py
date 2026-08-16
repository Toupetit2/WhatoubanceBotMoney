import discord
from discord.ext import commands, tasks
import os
from minigame_limits import reset_minigame
import minigame_queue
from minigames_view import MinigamesView


GUILD_ID = int(os.getenv("GUILD_ID"))

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.messages = True

        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        print(f"INFO - Synchronized commands: {[cmd.name for cmd in synced]}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        import traceback
        traceback.print_exception(type(error), error, error.__traceback__)

    async def on_ready(self):

        print(f"INFO - Connected as {self.user}", flush=True)

        if not reset_minigame.is_running():
            reset_minigame.start()

        if not refill_minigame_queue_loop.is_running():
            refill_minigame_queue_loop.start()

        self.add_view(MinigamesView())


@tasks.loop(minutes=5)
async def refill_minigame_queue_loop():
    await minigame_queue.refill_queue()
