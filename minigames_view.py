import discord
from minigame_command import launch_minigame
from dices_command import launch_minigame as launch_dice_minigame

class MinigamesView(discord.ui.View): 
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Master Mind", style=discord.ButtonStyle.gray, custom_id="minigame_1_button") 
    async def minigame_button_one(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await launch_minigame(interaction)

    @discord.ui.button(label="Lucky Dice", style=discord.ButtonStyle.gray, custom_id="minigame_2_button") 
    async def minigame_button_two(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await launch_dice_minigame(interaction)