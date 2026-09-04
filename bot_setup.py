from commands.give_command import setup as setup_give
from commands.minigames_send_buttons import setup as setup_minigames_send_buttons
from commands.leaderboard import setup as setup_leaderboard
from bets_commands import setup as setup_bets
from boutique import setup as setup_boutique
from tickets import setup as setup_tickets
from loterie import setup as setup_loterie
from minigame_clear import setup as setup_minigameclear
from commands.custom_titles_command import setup as setup_custom_titles
from commands.unlock_success_command import setup as setup_unlock_success

async def bot_setup(bot):
    setup_give(bot)
    setup_minigames_send_buttons(bot)
    setup_leaderboard(bot)
    setup_bets(bot)
    setup_tickets(bot)
    setup_boutique(bot)
    setup_loterie(bot)
    setup_minigameclear(bot)
    setup_custom_titles(bot)
    setup_unlock_success(bot)