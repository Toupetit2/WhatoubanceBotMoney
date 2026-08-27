import discord
import asyncio
import os
from minigame_limits import can_play_today, mark_played
import shutil
import minigame_queue
import give
import minigames_gains
import success_checks

EMOJI_WTBIFF = os.getenv("EMOJI_WTBIFF", "💰")

async def minigame_answer(answer: int, guess: int, interaction: discord.Interaction):
    points_repartition = minigames_gains.get_gains("find_placement")

    messages = {
        0: "Parfait, excellent, admirable…  **Tu as tout juste**, tu gagnes **{points}** {emoji}",
        1: "A un cheveu de la perfection… **Tu étais à 1 près**, tu gagnes **{points}** {emoji}\n*La réponse était : Top {answer}*",
        2: "On va dire que c'était presque ça ! **Mais à 2 près** ... tu gagnes **{points}** {emoji}\n*La réponse était : Top {answer}*",
        3: "Là on commence à être un poil loin… **A 3 près tu avais juste**, tu gagnes **{points}** {emoji}\n*La réponse était : Top {answer}*",
        4: "Bon, tu feras mieux demain ! **Tu étais à 4 près**  mais tu gagnes quand même **{points}** {emoji}\n*La réponse était : Top {answer}*",
        5: "C'était surement un miss click non ? **Tu es a 5 près** ! Lot de consolation tu gagnes **{points}** {emoji}\n*La réponse était : Top {answer}*",
        6: 'Je vais dire que j\'ai rien vu, parce que toi non plus… **Tu es à 6 près**. tu "gagnes" **{points}** {emoji}\n*La réponse était : Top {answer}*',
        7: "Ca t'amuses de troll ? **TU ES A L'OPPOSE DE LA REALITE**  , tu gagnes **{points}** {emoji}\n*La réponse était : Top {answer}*",
    }

    distance = abs(answer - guess)

    if distance not in messages:
        return "Raté, tu étais trop loin, aucun WhatouBiffs cette fois-ci."

    give.give_coins(points_repartition[distance], interaction.user)
    give.increment_statistic(interaction.user, "minigame1_whatoubiffs_total", points_repartition[distance])

    game_count = give.get_statistic(interaction.user, "minigame1_game_count")  # incrémenté AVANT ce calcul
    old_avg = give.get_statistic(interaction.user, "minigame1_average_error")
    new_value = distance  # pas points_repartition[distance]
    new_avg = old_avg + (new_value - old_avg) / game_count
    give.set_statistic(interaction.user, "minigame1_average_error", new_avg)

    await success_checks.check_minigame_success(interaction.user, distance, interaction)
    days_played = success_checks.register_day_played(interaction.user)
    await success_checks.check_played_days_success(interaction.user, interaction)

    return messages[distance].format(points=points_repartition[distance], emoji=EMOJI_WTBIFF, answer=answer)


class MinigameView(discord.ui.View):

    def __init__(self, answer, raw_path, timeout=600):
        super().__init__(timeout=timeout)
        self.answer = answer
        self.raw_path = raw_path
        self.answered = False

    async def handle_guess(self, interaction: discord.Interaction, guess: int):
        if self.answered:
            await interaction.response.send_message(
                "Tu as déjà répondu à ce minijeu !", ephemeral=True
            )
            return

        self.answered = True

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(view=self)
        message = await minigame_answer(self.answer, guess, interaction)

        if os.path.exists(self.raw_path):
            await interaction.followup.send(
                message,
                file=discord.File(self.raw_path),
                ephemeral=True
            )
            os.remove(self.raw_path)
        else:
            await interaction.followup.send(message, ephemeral=True)

        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

        if os.path.exists(self.raw_path):
            os.remove(self.raw_path)

    @discord.ui.button(label="🥇 TOP 1 🥇", style=discord.ButtonStyle.success, custom_id="1", row=0) 
    async def one_button(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.handle_guess(interaction, 1)

    @discord.ui.button(label="🥈 TOP 2 🥈", style=discord.ButtonStyle.gray, custom_id="2", row=0) 
    async def two_button(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.handle_guess(interaction, 2)

    @discord.ui.button(label="🥉 TOP 3 🥉", style=discord.ButtonStyle.gray, custom_id="3", row=0) 
    async def three_button(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.handle_guess(interaction, 3)

    @discord.ui.button(label="🏅TOP 4 🏅", style=discord.ButtonStyle.gray, custom_id="4", row=0) 
    async def four_button(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.handle_guess(interaction, 4)

    @discord.ui.button(label="🎖️TOP 5 🎖️", style=discord.ButtonStyle.gray, custom_id="5", row=1) 
    async def five_button(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.handle_guess(interaction, 5)

    @discord.ui.button(label="🔰 TOP 6 🔰", style=discord.ButtonStyle.gray, custom_id="6", row=1) 
    async def six_button(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.handle_guess(interaction, 6)

    @discord.ui.button(label="💩 TOP 7 💩", style=discord.ButtonStyle.gray, custom_id="7", row=1) 
    async def seven_button(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.handle_guess(interaction, 7)

    @discord.ui.button(label="💀 TOP 8 💀", style=discord.ButtonStyle.gray, custom_id="8", row=1) 
    async def eight_button(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.handle_guess(interaction, 8)


async def launch_minigame(interaction: discord.Interaction):
    try:
        print("[INFO] minijeu déclenché par", interaction.user.id)

        if not can_play_today(interaction.user.id, "mastermind"):
            await interaction.response.send_message(
                "Tu as déjà joué aujourd'hui, reviens demain !",
                ephemeral=True
            )
            return

        entry = minigame_queue.pop_one()

        if entry is None:
            await interaction.response.send_message(
                "Aucun minijeu prêt pour l'instant, réessaie dans une minute !",
                ephemeral=True
            )
            return
        
        give.update_daily_streak(interaction.user)
        give.increment_statistic(interaction.user, "minigame1_game_count")
        mark_played(interaction.user.id, "mastermind")
        await interaction.response.defer(ephemeral=True)

        user_raw_path = f"{interaction.user.id}_raw.png"
        shutil.copy(entry["raw_path"], user_raw_path)

        view = MinigameView(entry["answer"], user_raw_path)

        await interaction.followup.send(
            "Trouve le placement de ce joueur pour gagner ",
            file=discord.File(entry["final_path"]),
            view=view,
            ephemeral=True
        )

        os.remove(entry["raw_path"])
        os.remove(entry["final_path"])

        asyncio.create_task(minigame_queue.refill_queue())

    except Exception as e:
        import traceback
        print("[ERROR] exception dans launch_minigame:")
        traceback.print_exc()