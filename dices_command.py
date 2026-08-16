import discord
import os
from dices_backend import loaded_dice, magic_roll, golden_gamble
import asyncio
import random
import give


class DicesView(discord.ui.View):

    def __init__(self):
        super().__init__()
        self.answered = False

    async def handle_roll(self, interaction: discord.Interaction, roll_function):
        give.update_daily_streak(interaction.user)
        give.increment_statistic(interaction.user, "luckydice_game_count")
        if self.answered:
            await interaction.response.send_message(
                "Tu as déjà lancé les dés !", ephemeral=True
            )
            return

        self.answered = True

        for child in self.children:
            child.disabled = True

        try:
            dices, result, gain = roll_function()
            nb_dices = len(dices)
            give.give_coins(gain, interaction.user)

            await interaction.response.edit_message(content="Lancer en cours...", view=self)

            spins_per_die = [5, 8, 11]
            max_spins = max(spins_per_die)

            current = [random.randint(1, 6) for _ in range(nb_dices)]

            for frame in range(max_spins):
                for i in range(nb_dices):
                    if frame < spins_per_die[i]:
                        random_int = random.randint(1, 6)
                        while random_int == current[i]:
                            random_int = random.randint(1, 6)
                        current[i] = random_int
                    else:
                        current[i] = dices[i]

                faces_text = " - ".join(str(d) for d in current)

                # Ralentit progressivement vers la fin
                delay = 0.05 + (frame / max_spins) * 0.15

                await interaction.edit_original_response(
                    content=f"🎲 {faces_text}",
                    view=self
                )
                await asyncio.sleep(delay)

            # Résultat final (garanti d'afficher les vraies valeurs)
            dices_text = " - ".join(str(d) for d in dices)

            if roll_function == loaded_dice:
                final_content = f"Résultat du lancer de dé : {dices_text}"
            else:
                final_content = f"Résultat du lancer de dés : {dices_text} (Total : {result})"

            await interaction.edit_original_response(content=final_content, view=self)

            if roll_function == loaded_dice:
                message = f"Tu gagnes : {gain} points"
                give.increment_statistic(interaction.user, "loaded_dice_whatoubiffs_total", gain)
                give.register_dice_roll(interaction.user, dices[0])

            elif roll_function == magic_roll:
                message = f"Tu gagnes : {gain} points"
                give.increment_statistic(interaction.user, "magic_roll_whatoubiffs_total", gain)

                if dices == [1, 1, 1] or dices == [6, 6, 6]:
                    give.increment_statistic(interaction.user, "magic_roll_triple16")

            elif roll_function == golden_gamble:
                if gain > 0:
                    message = f"Félicitations ! Tu gagnes : {gain + 50} points"
                    give.increment_statistic(interaction.user, "golden_gamble_whatoubiffs_total", gain)
                    give.increment_statistic(interaction.user, "golden_gamble_total_wins")

                else:
                    message = f"Tu perd donc ta mise de {-gain} points"

            await interaction.followup.send(message, ephemeral=True)

        except Exception as e:
            print(f"Erreur pendant l'animation des dés : {e}")
            await interaction.followup.send(
                "Oups, une erreur est survenue pendant le lancer 😅", ephemeral=True
            )

    @discord.ui.button(label="Loaded Dice", style=discord.ButtonStyle.primary, custom_id="loaded_dice")
    async def loaded_dice_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        give.increment_statistic(interaction.user, "loaded_dice_game_count")
        await self.handle_roll(interaction, loaded_dice)

    @discord.ui.button(label="Magic Roll", style=discord.ButtonStyle.primary, custom_id="magic_roll")
    async def magic_roll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        give.increment_statistic(interaction.user, "magic_roll_game_count")
        await self.handle_roll(interaction, magic_roll)

    @discord.ui.button(label="Golden Gamble", style=discord.ButtonStyle.primary, custom_id="golden_gamble")
    async def golden_gamble_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        give.increment_statistic(interaction.user, "golden_gamble_game_count")
        await self.handle_roll(interaction, golden_gamble)


async def launch_minigame(interaction: discord.Interaction):
    await interaction.response.send_message("", view=DicesView(), ephemeral=True)