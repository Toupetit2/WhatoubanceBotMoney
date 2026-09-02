import discord
from discord import app_commands
import custom_titles as titles


def setup(bot):
    async def title_autocomplete(interaction: discord.Interaction, current: str):
        data = titles.list_titles()
        return [
            app_commands.Choice(name=title, value=title)
            for title in data.keys()
            if current.lower() in title.lower()
        ][:25]

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="titre_create", description="Crée un titre custom")
    async def titre_create_command(interaction: discord.Interaction, title: str, description: str):
        titles.add_title(title, description)
        await interaction.response.send_message(f"✅ Le titre **{title}** a été créé", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(title=title_autocomplete)
    @bot.tree.command(name="titre_give", description="Donne un titre custom à un membre")
    async def titre_give_command(interaction: discord.Interaction, member: discord.Member, title: str):
        already_had = titles.give_title(member, title)

        if already_had is None:
            await interaction.response.send_message(f"❌ Le titre **{title}** n'existe pas", ephemeral=True)
        elif already_had:
            await interaction.response.send_message(f"ℹ️ {member.display_name} avait déjà le titre **{title}**", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ {member.display_name} a reçu le titre **{title}**", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(title=title_autocomplete)
    @bot.tree.command(name="titre_take", description="Retire un titre donné à un membre")
    async def titre_take_command(interaction: discord.Interaction, member: discord.Member, title: str):
        success = titles.take_title(member, title)
        if success:
            await interaction.response.send_message(f"🗑️ Le titre **{title}** a été retiré à {member.display_name}", ephemeral=True)
        else:
            await interaction.response.send_message(f"ℹ️ {member.display_name} n'a pas le titre **{title}**", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(title=title_autocomplete)
    @bot.tree.command(name="titre_remove", description="Retire un titre custom du catalogue")
    async def titre_remove_command(interaction: discord.Interaction, title: str):
        removed = titles.remove_title(title)
        if removed:
            await interaction.response.send_message(f"🗑️ Le titre **{title}** a été supprimé", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Le titre **{title}** n'existe pas", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="titre_list", description="Affiche tous les titres disponibles")
    async def titre_list_command(interaction: discord.Interaction):
        data = titles.list_titles()
        if not data:
            await interaction.response.send_message("Aucun titre n'a été créé.", ephemeral=True)
            return

        message = "\n".join(f"**{title}** — {info['description']}" for title, info in data.items())
        await interaction.response.send_message(message, ephemeral=True)