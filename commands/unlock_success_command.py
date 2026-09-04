import discord
from discord import app_commands
import give

def setup(bot):
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="unlock_success", description="Débloque un succès pour un membre")
    async def unlock_success_command(interaction: discord.Interaction, member: discord.Member, category: str, success_id: str):

        if give.has_success(member, category, success_id):
            await interaction.response.send_message(f"⚠️{member.display_name} possède déjà le succès `{success_id}` ({category})", ephemeral=True)
            return

        await give.unlock_success(member, success_id, category)
        await interaction.response.send_message(f"✅Succès `{success_id}` ({category}) débloqué pour {member.display_name}", ephemeral=True)