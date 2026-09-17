from minigame_limits import set_status
import discord
from discord import app_commands
import os

def setup(bot):
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="minigame_limit_change_status", description="Change la limite pour les minijeu : illimité/1 par jour")
    async def status_update_command(ctx, member: discord.Member):
        nouveau = STATUS_DEFAULT if has_unlimited(member.id) else STATUS_UNLIMITED
        set_status(member.id, nouveau)

        if nouveau == STATUS_UNLIMITED:
            await interaction.response.send_message(f"{member.mention} passe en **illimité**")
        else:
            await interaction.response.send_message(f"{member.mention} repasse en **limité** (1 partie/jour)")