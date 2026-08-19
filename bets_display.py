import discord
import os
import bets_data

STATUT_LABELS = {
    "brouillon": "📝 Brouillon",
    "a_venir": "🕒 À venir",
    "ouvert": "✅ Ouvert",
    "ferme": "🔒 Fermé",
    "resolu": "🏁 Résolu",
    "annule": "❌ Annulé",
}

STATUT_COLORS = {
    "brouillon": discord.Color.light_grey(),
    "a_venir": discord.Color.blue(),
    "ouvert": discord.Color.green(),
    "ferme": discord.Color.orange(),
    "resolu": discord.Color.gold(),
    "annule": discord.Color.red(),
}

EMOJI_WTBIFF = os.getenv("EMOJI_WTBIFF", "💰")


def build_bet_embed(bet_id: str, bet: dict) -> discord.Embed:
    statut = bet["statut"]

    embed = discord.Embed(
        title=bet["titre"],
        description=bet["description"],
        color=STATUT_COLORS.get(statut, discord.Color.default())
    )

    embed.add_field(name="Statut", value=STATUT_LABELS.get(statut, statut), inline=False)

    if bet["choix"]:
        lines = []
        for choix in bet["choix"]:
            mise_totale = sum(
                p["montant"] for p in bet["paris_joueurs"].values()
                if p["choix_id"] == choix["id"]
            )
            lines.append(f"**{choix['id']}.** {choix['label']} — cote `x{choix['cote']}` — {mise_totale} {EMOJI_WTBIFF} misés")
        embed.add_field(name="🎯 Choix", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="🎯 Choix", value="Aucun choix pour l'instant.", inline=False)

    embed.add_field(
        name="📅 Ouverture",
        value=f"<t:{bet['date_ouverture']}:F>",
        inline=True
    )
    embed.add_field(
        name="📅 Fermeture",
        value=f"<t:{bet['date_fermeture']}:F>",
        inline=True
    )

    if statut == "resolu" and bet["resultat"] is not None:
        gagnant = next((c for c in bet["choix"] if c["id"] == bet["resultat"]), None)
        if gagnant:
            embed.add_field(name="🏆 Résultat", value=f"**{gagnant['label']}** a gagné !", inline=False)

    nb_joueurs = len(bet["paris_joueurs"])
    total_mise = sum(p["montant"] for p in bet["paris_joueurs"].values())
    embed.set_footer(text=f"Pari #{bet_id} • {nb_joueurs} joueur(s) • {total_mise} misés au total")

    return embed


async def update_bet_embed(bot: discord.Client, bet_id: str) -> bool:
    bet = bets_data.load_bets().get(bet_id)
    if bet is None:
        return False

    channel_id = bet.get("channel_id")
    message_id = bet.get("message_id")

    if channel_id is None or message_id is None:
        return False
    channel = bot.get_channel(channel_id)
    if channel is None:
        return False

    try:
        message = await channel.fetch_message(message_id)
        embed = build_bet_embed(bet_id, bet)
        view = BetView(bet_id)
        await message.edit(embed=embed, view=view)
        return True
    except discord.NotFound:
        return False


class NewBetModal(discord.ui.Modal, title="Placer un pari"):
    def __init__(self, bet_id: str, choix: list[dict], bot):
        super().__init__()
        self.bet_id = bet_id
        self.choix = choix
        self.bot = bot

        noms_disponibles = ", ".join(c["label"] for c in choix)

        self.choix_input = discord.ui.TextInput(
            label="Sur qui/quoi tu paries ?",
            placeholder=noms_disponibles[:100],
            required=True,
            max_length=100
        )
        self.montant_input = discord.ui.TextInput(
            label="Montant à parier",
            placeholder="1-1000",
            required=True,
            max_length=10
        )
        self.add_item(self.choix_input)
        self.add_item(self.montant_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            choix_saisi = self.choix_input.value.strip().lower()

            choix_trouve = next(
                (c for c in self.choix if c["label"].strip().lower() == choix_saisi),
                None
            )
            if choix_trouve is None:
                noms = ", ".join(c["label"] for c in self.choix)
                await interaction.response.send_message(
                    f"❌ Choix inconnu. Options valides : {noms}",
                    ephemeral=True
                )
                return

            try:
                montant = int(self.montant_input.value)
            except ValueError:
                await interaction.response.send_message("Montant invalide, entre un nombre entier.", ephemeral=True)
                return

            if montant <= 0:
                await interaction.response.send_message("Le montant doit être positif.", ephemeral=True)
                return

            if montant > 1000:
                await interaction.response.send_message(f"Le montant maximum par pari est de **1000** {EMOJI_WTBIFF}.", ephemeral=True)
                return

            try:
                bets_data.place_bet(self.bet_id, interaction.user, choix_trouve["id"], montant)
            except ValueError as e:
                await interaction.response.send_message(f"❌ {e}", ephemeral=True)
                return

            from bets_display import update_bet_embed
            await update_bet_embed(self.bot, self.bet_id)

            await interaction.response.send_message(
                f"✅ Pari de **{montant}** {EMOJI_WTBIFF} placé sur **{choix_trouve['label']}** !",
                ephemeral=True
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)

class AddToBetModal(discord.ui.Modal, title="Ajouter à ton pari"):
    def __init__(self, bet_id: str, choix_id: int, choix_label: str, bot):
        super().__init__()
        self.bet_id = bet_id
        self.choix_id = choix_id
        self.bot = bot

        self.montant_input = discord.ui.TextInput(
            label=f"Montant à ajouter sur \"{choix_label}\"",
            placeholder="1-1000",
            required=True,
            max_length=10
        )
        self.add_item(self.montant_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            montant = int(self.montant_input.value)
        except ValueError:
            await interaction.response.send_message("Montant invalide, entre un nombre entier.", ephemeral=True)
            return

        if montant <= 0:
            await interaction.response.send_message("Le montant doit être positif.", ephemeral=True)
            return

        bet = bets_data.load_bets().get(self.bet_id)
        mise_actuelle = bet["paris_joueurs"].get(str(interaction.user.id), {}).get("montant", 0)

        if mise_actuelle + montant > 1000:
            restant = 1000 - mise_actuelle
            await interaction.response.send_message(
                f"❌ Tu as déjà parié {mise_actuelle} {EMOJI_WTBIFF}. Tu peux encore ajouter au maximum **{restant}** {EMOJI_WTBIFF}.",
                ephemeral=True
            )
            return

        bets_data.add_to_bet(self.bet_id, interaction.user, montant)

        await update_bet_embed(self.bot, self.bet_id)

        await interaction.response.send_message(f"✅ **{montant}** {EMOJI_WTBIFF} ajouté à ton pari !", ephemeral=True)

class BetView(discord.ui.View):
    def __init__(self, bet_id: str):
        super().__init__(timeout=None)
        self.bet_id = bet_id

        bet = bets_data.load_bets().get(bet_id)
        statut = bet["statut"] if bet else None

        if statut not in ("a_venir", "ouvert"):
            self.remove_item(self.place_bet_button)

    @discord.ui.button(label="Parier", style=discord.ButtonStyle.success, custom_id="bet_place")
    async def place_bet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        bet = bets_data.load_bets().get(self.bet_id)

        if bet is None:
            await interaction.response.send_message("Ce pari n'existe plus.", ephemeral=True)
            return

        if bet["statut"] != "ouvert":
            await interaction.response.send_message("Ce pari n'est pas ouvert aux mises actuellement.", ephemeral=True)
            return

        if not bet["choix"]:
            await interaction.response.send_message("Ce pari n'a pas encore de choix disponibles.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        pari_existant = bet["paris_joueurs"].get(user_id)

        if pari_existant:
            choix_id = pari_existant["choix_id"]
            choix_label = next((c["label"] for c in bet["choix"] if c["id"] == choix_id), "?")
            modal = AddToBetModal(self.bet_id, choix_id, choix_label, interaction.client)
        else:
            modal = NewBetModal(self.bet_id, bet["choix"], interaction.client)

        await interaction.response.send_modal(modal)