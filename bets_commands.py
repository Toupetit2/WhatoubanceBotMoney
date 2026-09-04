import discord
from discord import app_commands
from discord.ext import tasks

import bets_data
import bets_display
import give
import success_checks

def hours_minutes_to_seconds(value: float) -> int:
    hours = int(value)
    minutes = int((value - hours) * 100)
    return hours * 3600 + minutes * 60


def setup(bot):
    bets = bets_data.load_bets()
    for bet_id, bet in bets.items():
        if bet.get("statut") in ("a_venir", "ouvert") and bet.get("message_id"):
            bot.add_view(bets_display.BetView(bet_id), message_id=bet["message_id"])

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="pari_creer", description="Crée un nouveau pari")
    @app_commands.describe(
        titre="Le titre du pari",
        description="La description du pari",
        temps_avant_ouverture="Temps avant l'ouverture du pari (en heures)",
        temps_pour_parier="Temps pour parier après l'ouverture (en heures)"
    )
    async def create_bet_command(interaction: discord.Interaction, titre: str, description: str, temps_avant_ouverture: float, temps_pour_parier: float):
        await interaction.response.defer(ephemeral=True)

        try:
            temps_avant_ouverture_seconds = hours_minutes_to_seconds(temps_avant_ouverture)
            temps_pour_parier_seconds = hours_minutes_to_seconds(temps_pour_parier)

            bet_id = bets_data.create_bet(titre, description, temps_avant_ouverture_seconds, temps_pour_parier_seconds, interaction.user.id)

            bet = bets_data.load_bets().get(bet_id, {})
            embed = bets_display.build_bet_embed(bet_id, bet)
            view = bets_display.BetView(bet_id)

            msg = await interaction.channel.send(embed=embed, view=view)

            bets_data.set_bet_message_ref(bet_id, interaction.channel.id, msg.id)

            await interaction.followup.send(f"✅ Le pari '{titre}' a été créé avec succès.", ephemeral=True)

        except Exception as e:
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Erreur lors de la création du pari : `{e}`", ephemeral=True)


    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="pari_ajouter_choix", description="Ajoute un choix à un pari existant")
    @app_commands.describe(
        bet_id="L'ID du pari",
        nom="Le nom du choix à ajouter",
        cote="La cote du choix à ajouter"
    )
    async def add_choice_command(interaction: discord.Interaction, bet_id: str, nom: str, cote: float):
        await interaction.response.defer(ephemeral=True)

        try:
            bets_data.add_choice(bet_id, nom, cote)
            await bets_display.update_bet_embed(bot, bet_id)

            await interaction.followup.send(f"✅ Le choix '{nom}' avec une cote de {cote} a été ajouté au pari #{bet_id}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur lors de l'ajout du choix : `{e}`", ephemeral=True)


    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="pari_supprimer_choix", description="Supprime un choix d'un pari existant")
    @app_commands.describe(
        bet_id="L'ID du pari",
        numero="Le numéro du choix à supprimer"
    )
    async def remove_choice_command(interaction: discord.Interaction, bet_id: str, numero: int):
        await interaction.response.defer(ephemeral=True)

        try:
            bets_data.remove_choice(bet_id, numero)
            await bets_display.update_bet_embed(bot, bet_id)

            await interaction.followup.send(f"✅ Le choix numéro {numero} a été supprimé du pari #{bet_id}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur lors de la suppression du choix : `{e}`", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        bet_id="L'ID du pari",
        temps_avant_ouverture="Nouvelle durée avant l'ouverture (Heures.Minutes)",
        temps_pour_parier="Nouvelle durée pour parier (Heures.Minutes)"
    )
    @bot.tree.command(name="pari_changer_dates", description="Change les dates d'un pari existant")
    async def change_bet_dates_command(interaction: discord.Interaction, bet_id: str, temps_avant_ouverture: float, temps_pour_parier: float):
        await interaction.response.defer(ephemeral=True)

        try:
            temps_avant_ouverture_seconds = hours_minutes_to_seconds(temps_avant_ouverture)
            temps_pour_parier_seconds = hours_minutes_to_seconds(temps_pour_parier)

            bets_data.change_bet_dates(bet_id, temps_avant_ouverture_seconds, temps_pour_parier_seconds)

            await bets_display.update_bet_embed(bot, bet_id)

            await interaction.followup.send(f"✅ Les dates du pari #{bet_id} ont été mises à jour.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur lors de la mise à jour des dates : `{e}`", ephemeral=True)


    @app_commands.guild_only
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="pari_valider", description="Valide le gagnant du paris")
    async def validate_bet_winner(interaction: discord.Interaction, bet_id: str, numero: int):
        await interaction.response.defer(ephemeral=True)

        bet = bets_data.load_bets().get(bet_id)
        if bet is None:
            await interaction.followup.send("❌ Ce pari n'existe pas.", ephemeral=True)
            return

        paris_joueurs = bet["paris_joueurs"]

        try:
            gains = bets_data.resolve_bet(bet_id, numero)
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        for user_id, pari in paris_joueurs.items():
            member = interaction.guild.get_member(int(user_id))
            if member is None:
                continue

            montant_mise = pari["montant"]
            a_gagne = user_id in gains

            # Stats
            give.set_statistic(member, "betting_total_bets", give.get_statistic(member, "betting_total_bets") + 1)
            give.set_statistic(member, "betting_total_wagered", give.get_statistic(member, "betting_total_wagered") + montant_mise)

            if a_gagne:
                gain_brut = gains[user_id]
                gain_net = gain_brut - montant_mise

                give.give_coins(gain_brut, member)

                give.set_statistic(member, "betting_wins", give.get_statistic(member, "betting_wins") + 1)
                give.set_statistic(member, "betting_net_whatoubiffs", give.get_statistic(member, "betting_net_whatoubiffs") + gain_net)

                if give.get_statistic(member, "betting_best_gain") < gain_net:
                    give.set_statistic(member, "betting_best_gain", gain_net)

            else:
                give.set_statistic(member, "betting_net_whatoubiffs", give.get_statistic(member, "betting_net_whatoubiffs") - montant_mise)

                if give.get_statistic(member, "betting_worst_loss") < montant_mise:
                    give.set_statistic(member, "betting_worst_loss", montant_mise)



            await success_checks.check_betting_success(interaction.user, montant_mise)



        from bets_display import update_bet_embed
        await update_bet_embed(interaction.client, bet_id)

        await interaction.followup.send(f"✅ Pari #{bet_id} résolu, {len(gains)} gagnant(s) payé(s).", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="pari_fermer", description="Ferme un pari avant sa date prévue")
    @app_commands.describe(bet_id="L'identifiant du pari à fermer")
    async def pari_fermer_command(interaction: discord.Interaction, bet_id: str):
        await interaction.response.defer(ephemeral=True)

        try:
            bets_data.close_bet(bet_id)
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        await bets_display.update_bet_embed(interaction.client, bet_id)

        await interaction.followup.send(f"✅ Pari #{bet_id} fermé.", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="pari_rouvrir", description="Rouvre un pari fermé")
    @app_commands.describe(bet_id="L'identifiant du pari à rouvrir")
    async def pari_rouvrir_command(interaction: discord.Interaction, bet_id: str):
        await interaction.response.defer(ephemeral=True)

        try:
            bets_data.reopen_bet(bet_id)
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        await bets_display.update_bet_embed(interaction.client, bet_id)

        await interaction.followup.send(f"✅ Pari #{bet_id} réouvert.", ephemeral=True)



    @tasks.loop(seconds=15)
    async def auto_refresh_bets():
        changed_bet_ids = bets_data.refresh_bet_statuses()
        for bet_id in changed_bet_ids:
            await bets_display.update_bet_embed(bot, bet_id)

    if not auto_refresh_bets.is_running():
        auto_refresh_bets.start()