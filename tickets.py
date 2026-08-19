import json
import os

import discord

DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")


def load_data() -> dict:
    if os.path.exists(DATA_PATH) and os.path.getsize(DATA_PATH) > 0:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data: dict):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)


async def get_or_create_ticket_category(guild: discord.Guild) -> discord.CategoryChannel:
    """Récupère la catégorie 'Tickets' depuis data.json, ou la crée si absente/invalide."""
    data = load_data()
    category_id = data.get("ticket_category_id")

    if category_id is not None:
        category = guild.get_channel(category_id)
        if isinstance(category, discord.CategoryChannel):
            return category

    category = await guild.create_category("Tickets", reason="Création de la catégorie tickets")
    data["ticket_category_id"] = category.id
    save_data(data)
    return category


class DeleteTicketView(discord.ui.View):
    """Vue attachée au message d'un ticket, avec confirmation en 2 clics."""

    def __init__(self):
        super().__init__(timeout=None)
        self.confirming = False

    @discord.ui.button(label="Supprimer le salon", style=discord.ButtonStyle.danger, custom_id="delete_ticket")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Seuls les administrateurs peuvent supprimer ce salon.", ephemeral=True
            )
            return

        if not self.confirming:
            self.confirming = True
            button.label = "⚠️ Cliquer pour confirmer"
            await interaction.response.edit_message(view=self)
            return

        await interaction.response.send_message("Suppression du salon...", ephemeral=True)
        await interaction.channel.delete(reason=f"Ticket fermé par {interaction.user}")



def build_ticket_embed(member: discord.Member, description: str) -> discord.Embed:
    embed = discord.Embed(
        title="Ticket ouvert",
        description=f"{description}",
        color=discord.Color.blurple(),
    )
    embed.set_footer(text="Ton ticket est ouvert, on arrive dès que possible.")
    return embed


async def create_ticket_channel(
    guild: discord.Guild,
    member: discord.Member,
    channel_name: str,
    description: str
) -> discord.TextChannel:

    category = await get_or_create_ticket_category(guild)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }

    channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        reason=f"Ticket créé par {member}",
    )

    await channel.send(
        content=f"{member.mention}",
        embed=build_ticket_embed(member, description),
        view=DeleteTicketView(),
    )

    return channel


def setup(bot):
    bot.add_view(DeleteTicketView())

    @bot.tree.command(name="create_ticket", description="Crée un ticket privé")
    async def create_ticket(interaction: discord.Interaction, nom: str, description: str):
        channel = await create_ticket_channel(interaction.guild, interaction.user, nom, description)
        await interaction.response.send_message(f"Ticket créé : {channel.mention}", ephemeral=True)