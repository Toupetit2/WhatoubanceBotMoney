import discord
from discord import app_commands
from minigames_view import MinigamesView


def setup(bot):
    @app_commands.guild_only()
    @bot.tree.command(name="setup_minigames", description="Lance le panneau des minijeu")
    async def setup_minigames_command(interaction: discord.Interaction):
        image = discord.File("Images/wtbgame.jpg", filename="image.jpg")

        await interaction.channel.send(
            "",
            file=image,
            view=MinigamesView()
        )

        await interaction.response.send_message(
            "Panneau envoyé !",
            ephemeral=True
        )