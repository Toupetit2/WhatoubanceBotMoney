import discord
from discord import app_commands
import give
import json

def setup(bot):
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="unlock_success", description="Débloque un succès pour un membre")
    async def unlock_success_command(interaction: discord.Interaction, member: discord.Member, category: str, name: str):

        if give.has_success(member, category, name):
            await interaction.response.send_message(f"⚠️{member.display_name} possède déjà le succès `{name}` ({category})", ephemeral=True)
            return

        await give.unlock_success(member, name, category)
        await interaction.response.send_message(f"✅Succès `{name}` ({category}) débloqué pour {member.display_name}", ephemeral=True)


    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="list_success", description="Liste tous les succès disponibles avec leur catégorie")
    async def list_success_command(interaction: discord.Interaction):

        with open("successes.json", "r", encoding="utf-8") as f:
            successes = json.load(f)

        lines = []
        for category, entries in successes.items():
            lines.append(f"**{category}**")
            for success_id, info in entries.items():
                lines.append(f"• `{success_id}` — {info['title']}")

        message = "\n".join(lines)

        if len(message) > 4000:
            await interaction.response.send_message("⚠️Trop de succès pour être affichés en un seul message.", ephemeral=True)
            return

        embed = discord.Embed(title="📋 Liste des succès", description=message, color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed, ephemeral=True)