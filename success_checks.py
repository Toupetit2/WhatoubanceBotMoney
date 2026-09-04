import discord
from give import get_statistic, set_statistic, increment_statistic ,unlock_success_and_notify, get_user_coins, give_coins, has_success, unlock_success

import os

WTB_TAG_ROLE_ID = int(os.getenv("ROLE_WTB_TAG_ID", 0)) or None
WHATOUBANCE_CLUB_ROLE_ID = int(os.getenv("ROLE_WHATOUBANCE_CLUB_ID", 0)) or None

def has_role(member: discord.Member, role_id: int) -> bool:
    return role_id is not None and any(role.id == role_id for role in member.roles)

# ---------------- Catégorie "Des" ----------------

async def check_golden_gamble_success(member: discord.Member, won: bool, interaction: discord.Interaction):
    """À appeler juste après chaque partie de Golden Gamble, une fois le résultat connu."""
    if won:
        set_statistic(member, "golden_gamble_lose_streak", 0)
        win_streak = increment_statistic(member, "golden_gamble_win_streak", 1)
        if win_streak >= 3:
            await unlock_success_and_notify(member, "win_3_golden_gamble", "Des", interaction)
    else:
        set_statistic(member, "golden_gamble_win_streak", 0)
        lose_streak = increment_statistic(member, "golden_gamble_lose_streak", 1)
        if lose_streak >= 6:
            await unlock_success_and_notify(member, "lose_6_golden_gamble", "Des", interaction)


async def check_magic_roll_success(member: discord.Member, dice_values: list[int], interaction: discord.Interaction):
    """dice_values = les 3 valeurs obtenues (ex: [1, 1, 1])."""
    if len(set(dice_values)) == 1 and dice_values[0] in (1, 6):
        await unlock_success_and_notify(member, "magic_roll_triple_1_or_6", "Des", interaction)


async def check_loaded_dice_success(member: discord.Member, score: int, interaction: discord.Interaction):
    """À appeler une fois par jour au Loaded Dice (le jeu semble déjà être quotidien vu last_played_date).
    Nécessite un tracking par jour, pas juste 'le dernier lancer'."""
    from datetime import date, timedelta
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    last_date = get_statistic(member, "loaded_dice_last_date", None)
    is_consecutive_day = last_date == yesterday

    # Streak de 6 exact
    if score == 6:
        streak = increment_statistic(member, "loaded_dice_six_streak", 1) if is_consecutive_day else set_statistic(member, "loaded_dice_six_streak", 1)
        if streak >= 3:
            await unlock_success_and_notify(member, "loaded_dice_3_consecutive_sixes", "Des", interaction)
    else:
        set_statistic(member, "loaded_dice_six_streak", 0)

    # Streak de 1 exact
    if score == 1:
        streak = increment_statistic(member, "loaded_dice_one_streak", 1) if is_consecutive_day else set_statistic(member, "loaded_dice_one_streak", 1)
        if streak >= 3:
            await unlock_success_and_notify(member, "loaded_dice_3_consecutive_ones", "Des", interaction)
    else:
        set_statistic(member, "loaded_dice_one_streak", 0)

    # Streak 10 ou 11
    if score in (10, 11):
        streak = increment_statistic(member, "loaded_dice_10_11_streak", 1) if is_consecutive_day else set_statistic(member, "loaded_dice_10_11_streak", 1)
        if streak >= 4:
            await unlock_success_and_notify(member, "loaded_dice_10_or_11_4_days", "Des", interaction)
    else:
        set_statistic(member, "loaded_dice_10_11_streak", 0)

    set_statistic(member, "loaded_dice_last_date", today)


# ---------------- Catégorie "Paris" ----------------

async def check_betting_success(member: discord.Member, single_bet_amount: int):
    """À appeler juste après register_bet(), avec le montant misé sur CE pari précis."""
    net = get_statistic(member, "betting_net_whatoubiffs", 0)
    if net >= 5000:
        await unlock_success(member, "bet_profit_5000", "Paris")
        
    if single_bet_amount >= 1000:
        await unlock_success(member, "single_bet_1000", "Paris")


# ---------------- Catégorie "Mini jeu" ----------------

async def check_minigame_success(member: discord.Member, error: int, interaction: discord.Interaction):
    """error = écart absolu entre le score trouvé et le score exact (0 = exact)."""

    if error == 0:
        streak = increment_statistic(member, "minigame_exact_streak", 1)
        if streak >= 5:
            await unlock_success_and_notify(member, "minigame_exact_score_5_times", "Mini jeu", interaction)
    else:
        set_statistic(member, "minigame_exact_streak", 0)

    if error == 1:
        streak = increment_statistic(member, "minigame_one_away_streak", 1)
        if streak >= 3:
            await unlock_success_and_notify(member, "minigame_one_away_3_times", "Mini jeu", interaction)
    else:
        set_statistic(member, "minigame_one_away_streak", 0)

    if error==7:
        await unlock_success_and_notify(member, "minigame_opposite_total", "Mini jeu", interaction)


# ---------------- Catégorie "Global" ----------------

async def check_coins_success(interaction: discord.Interaction):
    if get_user_coins(interaction.user) >= 50000:
        await unlock_success_and_notify(interaction.user, "reach_50000_whatoubiffs", "Global", interaction)


async def check_streak_success(member: discord.Member, interaction: discord.Interaction):
    streak = get_statistic(member, "current_streak", 0)
    if streak >= 30:
        await unlock_success_and_notify(member, "streak_30_days", "Global", interaction)


async def check_riot_linked_success(member: discord.Member, interaction: discord.Interaction):
    from boutique import has_riot_linked
    if has_riot_linked(member) and not has_success(member, "Global", "riot_account_linked"):
        give_coins(100, member)
        await unlock_success_and_notify(member, "riot_account_linked", "Global", interaction)


async def check_twitch_wtb_linked_success(member: discord.Member, interaction: discord.Interaction):
    if has_role(member, WTB_TAG_ROLE_ID) and not has_success(member, "Global", "twitch_wtb_tag_linked"):
        give_coins(200, member)
        await unlock_success_and_notify(member, "twitch_wtb_tag_linked", "Global", interaction)


async def check_whatoubance_club_success(member: discord.Member, interaction: discord.Interaction):
    from boutique import has_riot_linked
    if has_role(member, WHATOUBANCE_CLUB_ROLE_ID) and has_riot_linked(member) and not has_success(member, "Global", "whatoubance_club_riot_linked"):
        give_coins(100, member)
        await unlock_success_and_notify(member, "whatoubance_club_riot_linked", "Global", interaction)


async def check_full_shop_success(member: discord.Member, interaction: discord.Interaction):
    """Appelée après chaque achat de titre en boutique — vérifie si les 4 titres sont possédés."""
    from give import get_unlocked_titles
    TITRES_BOUTIQUE = ["Client de Passage", "Actionnaire", "Membre du conseil", "Propriétaire des lieux"]
    possedes = get_unlocked_titles(member)
    if all(t in possedes for t in TITRES_BOUTIQUE):
        await unlock_success_and_notify(member, "full_shop_unlocked", "Global", interaction)


def register_day_played(member: discord.Member):
    """À appeler une fois par jour, dès la première action du joueur ce jour-là (pas à chaque partie).
    Incrémente le total de jours joués (distinct du streak, qui repart à 0 si interruption)."""
    from datetime import date
    today = date.today().isoformat()
    last_counted = get_statistic(member, "last_day_counted", None)
    if last_counted != today:
        set_statistic(member, "last_day_counted", today)
        return increment_statistic(member, "played_total_days", 1)
    return get_statistic(member, "played_total_days", 0)


async def check_played_days_success(member: discord.Member, interaction: discord.Interaction):
    total_days = get_statistic(member, "played_total_days", 0)
    if total_days >= 100:
        await unlock_success_and_notify(member, "played_100_days", "Global", interaction)