import discord
from discord import app_commands
import give

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