from commands.give_command import setup as setup_give
from commands.minigames_send_buttons import setup as setup_minigames_send_buttons
from commands.profile_command import setup as setup_profile
from commands.leaderboard import setup as setup_leaderboard

async def bot_setup(bot):
    setup_give(bot)
    setup_minigames_send_buttons(bot)
    setup_profile(bot)
    setup_leaderboard(bot)
