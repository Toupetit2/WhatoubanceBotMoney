import discord
from profile_see import get_profile_embed, ProfileView
from give import unlock_success_and_notify

def setup(bot):
    @bot.tree.command(name="get_profile", description="Affiche ton profil et tes statistiques !")
    async def get_profile(interaction: discord.Interaction, member: discord.Member = None):
        user = member or interaction.user

        view = ProfileView(user)
        await interaction.response.send_message(
            embed=get_profile_embed(user, page=1),
            view=view,
            ephemeral=True
        )

        await unlock_success_and_notify(interaction.user, "get_profile", "Profil", interaction)