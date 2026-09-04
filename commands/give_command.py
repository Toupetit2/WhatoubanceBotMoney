import discord
from discord import app_commands
import give
import os

GUILD_ID = os.environ.get("GUILD_ID")

def setup(bot):
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="give_coins", description="Donne X coins au membre")
    async def give_coins_command(interaction: discord.Interaction, member: discord.Member, amount: int):

        new_balance = give.give_coins(amount, member)
        if amount > 0:
            await interaction.response.send_message(f"✅{member.display_name} a reçu {amount} coins, il en a maintenant {new_balance}", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅{member.display_name} a perdu {-amount} coins, il en a maintenant {new_balance}", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="give_coins_everyone", description="Donne X coins à tous les membres du serveur")
    async def give_coins_everyone_command(interaction: discord.Interaction, amount: int):
        await interaction.response.defer(ephemeral=True)
        guild = bot.get_guild(int(GUILD_ID))
        for member in guild.members:
            give.give_coins(amount, member)
            if amount > 0:
                await interaction.followup.send(f"✅ Tous les membres ont reçu {amount} coins", ephemeral=True)
            else:
                await interaction.followup.send(f"✅ Tous les membres ont perdu {-amount} coins", ephemeral=True)
