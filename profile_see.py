import discord
import give
import os
from get_leaderboard import get_whatoubiffs_leaderboard, get_successes_leaderboard

EMOJI_WTBIFF = os.getenv("EMOJI_WTBIFF", "💰")

def format_dice_faces(faces: dict) -> str:
    order = ["1", "2", "3", "4", "5", "6"]
    return " | ".join(f"{f}: {faces.get(f, 0)}" for f in order)


def get_rank(leaderboard: list, user_id: str):
    for i, (uid, _) in enumerate(leaderboard):
        if uid == user_id:
            return i + 1, len(leaderboard)
    return None


def get_profile_embed(user: discord.Member, page: int = 1):
    embed = discord.Embed(
        title=f"Profil de {user.display_name}",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text=f"Whatoubot - Page {page}/4")

    if page == 1:
        equiped_title = give.get_equiped_title(user)
        coins = give.get_user_coins(user)

        minigame1_count = give.get_statistic(user, "minigame1_game_count")
        luckydice_count = give.get_statistic(user, "luckydice_game_count")
        current_streak = give.get_statistic(user, "current_streak")
        best_streak = give.get_statistic(user, "best_streak")
        favorite_lucky_dice = give.get_favorite_lucky_dice(user)

        embed.add_field(name=equiped_title, value="", inline=False)
        embed.add_field(name=f"{EMOJI_WTBIFF} WhatouBiffs", value=str(coins), inline=True)

        user_id = str(user.id)

        coins_rank = get_rank(get_whatoubiffs_leaderboard(), user_id)
        success_rank = get_rank(get_successes_leaderboard(), user_id)

        coins_rank_text = f"#{coins_rank[0]}/{coins_rank[1]}" if coins_rank else "Non classé"
        success_rank_text = f"#{success_rank[0]}/{success_rank[1]}" if success_rank else "Non classé"

        classement_text = (
            f"WhatouBiffs : {coins_rank_text}\n"
            f"Succès : {success_rank_text}"
        )
        embed.add_field(name="📈 Classements", value=classement_text, inline=False)

        stats_text = (
            f"Parties de Master Mind : {minigame1_count}\n"
            f"Parties de Lucky Dice : {luckydice_count}\n"
            f"Série en cours : {current_streak} jour(s)\n"
            f"Meilleure série : {best_streak} jour(s)\n"
            f"Lucky Dice préféré : {favorite_lucky_dice}"
        )
        embed.add_field(name="📊 Statistiques Globales", value=stats_text, inline=False)

    elif page == 2:
        minigame1_count = give.get_statistic(user, "minigame1_game_count")
        minigame1_avg_error = round(give.get_statistic(user, "minigame1_average_error"), 2)
        minigame1_coins = give.get_statistic(user, "minigame1_whatoubiffs_total")

        embed.add_field(
            name="🎯 Master Mind",
            value=(
                f"Nombre de parties : {minigame1_count}\n"
                f"Moyenne de distance : {minigame1_avg_error}\n"
                f"WhatouBiffs gagnés : {minigame1_coins}"
            ),
            inline=False
        )

        gg_count = give.get_statistic(user, "golden_gamble_game_count")
        gg_wins = give.get_statistic(user, "golden_gamble_total_wins")
        gg_coins = give.get_statistic(user, "golden_gamble_whatoubiffs_total")

        embed.add_field(
            name="🎲 Golden Gamble",
            value=(
                f"Nombre de parties : {gg_count}\n"
                f"Nombre de victoires : {gg_wins}\n"
                f"WhatouBiffs gagnés : {gg_coins}"
            ),
            inline=False
        )

        mr_count = give.get_statistic(user, "magic_roll_game_count")
        mr_triple = give.get_statistic(user, "magic_roll_triple16")
        mr_coins = give.get_statistic(user, "magic_roll_whatoubiffs_total")

        embed.add_field(
            name="🎲 Magic Roll",
            value=(
                f"Nombre de parties : {mr_count}\n"
                f"Triple 1 ou Triple 6 : {mr_triple}\n"
                f"WhatouBiffs gagnés : {mr_coins}"
            ),
            inline=False
        )

        ld_count = give.get_statistic(user, "loaded_dice_game_count")
        ld_faces = give.get_dice_faces_stats(user)
        ld_coins = give.get_statistic(user, "loaded_dice_whatoubiffs_total")

        embed.add_field(
            name="🎲 Loaded Dice",
            value=(
                f"Nombre de parties : {ld_count}\n"
                f"Stats des dés : {format_dice_faces(ld_faces)}\n"
                f"WhatouBiffs gagnés : {ld_coins}"
            ),
            inline=False
        )

    elif page == 3:
        total_bets = give.get_statistic(user, "betting_total_bets")
        win_rate = give.get_betting_win_rate(user)
        total_wagered = give.get_statistic(user, "betting_total_wagered")
        best_gain = give.get_statistic(user, "betting_best_gain")
        worst_loss = give.get_statistic(user, "betting_worst_loss")
        net = give.get_statistic(user, "betting_net_whatoubiffs")

        embed.add_field(
            name="🎰 Résultats des Paris",
            value=(
                f"Nombre de paris joués : {total_bets}\n"
                f"Taux de victoire : {win_rate}%\n"
                f"WhatouBiffs misés : {total_wagered}\n"
                f"Plus gros gain : {best_gain}\n"
                f"Plus grosse perte : {worst_loss}\n"
                f"Whatoubiffs gagnés : {net}"
            ),
            inline=False
        )

    elif page == 4:
        categories = ["Des", "Mini jeu", "Paris", "Boutique", "Global"]
        labels = {
            "Des": "🎲 Lucky Dices",
            "Mini jeu": "🎮 Master Mind",
            "Paris": "🎰 Paris",
            "Boutique": "🛒 Boutique",
            "Global": "🌐 Global"
        }

        lines = []
        for cat in categories:
            unlocked, total = give.get_success_progress(user, cat)
            lines.append(f"{labels[cat]} : {unlocked}/{total}")

        global_unlocked, global_total = give.get_global_success_progress(user)
        lines.append(f"**Total : {global_unlocked}/{global_total}**")

        embed.add_field(name="🏆 Succès Débloqués", value="\n".join(lines), inline=False)
    
    return embed

class TitleSelect(discord.ui.Select):
    def __init__(self, user: discord.Member, titles: list[str], page: int = 0):
        self.user = user
        options = [
            discord.SelectOption(label=title, value=title)
            for title in titles[:25]
        ]
        start = page * 25 + 1
        end = start + len(titles) - 1
        placeholder = f"Titres {start}-{end}..." if page > 0 else "Choisis un titre..."

        super().__init__(placeholder=placeholder, options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Ce menu n'est pas pour toi.", ephemeral=True)
            return

        chosen_title = self.values[0]
        give.set_equiped_title(self.user, chosen_title)

        await interaction.response.edit_message(
            content=f"✅ Titre équipé : **{chosen_title}**",
            view=None
        )


class TitleSelectView(discord.ui.View):
    def __init__(self, user: discord.Member, titles: list[str], timeout: float = 60):
        super().__init__(timeout=timeout)
        for i in range(0, len(titles), 25):
            chunk = titles[i:i + 25]
            self.add_item(TitleSelect(user, chunk, i // 25))

class ProfileView(discord.ui.View):
    def __init__(self, user: discord.Member, max_pages: int = 4, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.user = user
        self.page = 1
        self.max_pages = max_pages
        self._update_buttons()

    def _update_buttons(self):
        self.previous_button.disabled = self.page <= 1
        self.next_button.disabled = self.page >= self.max_pages

    @discord.ui.button(label="◀ Précédent", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=get_profile_embed(self.user, self.page), view=self)

    @discord.ui.button(label="Suivant ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=get_profile_embed(self.user, self.page), view=self)

    @discord.ui.button(label="Changer de titre", style=discord.ButtonStyle.primary)
    async def set_title_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Ce n'est pas ton profil.", ephemeral=True)
            return

        titles = give.get_unlocked_titles(self.user)

        if not titles:
            await interaction.response.send_message("Tu n'as débloqué aucun titre pour l'instant.", ephemeral=True)
            return

        view = TitleSelectView(self.user, titles)
        await interaction.response.send_message("Choisis ton titre :", view=view, ephemeral=True)