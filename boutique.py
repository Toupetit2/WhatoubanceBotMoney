import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import tasks

from tickets import create_ticket_channel

import loterie

DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")
BOUTIQUE_PATH = os.path.join(os.path.dirname(__file__), "boutique.json")
USERS_PATH = os.path.join(os.path.dirname(__file__), "users.json")

BOUTIQUE_REF_PATH = os.path.join(os.path.dirname(__file__), "boutique_ref.json")

boutique_message_ref = {"channel_id": None, "message_id": None}

ROLE_IDS = {
    "role_esclave_bot": int(os.getenv("ROLE_ESCLAVE_BOT_ID", 0)) or None,
}

PRICE_INCREMENT = 500

EMOJI_WTBIFF = os.getenv("EMOJI_WTBIFF", "💰")

PALIER_EMOJIS = {
    "1": "⭐️",
    "2": "🌟",
    "3": "✨",
    "4": "💥",
}

DEFAULT_CATALOGUE = {
    "1": [
        {"id": "ticket_loterie", "nom": "Ticket de loterie", "prix": 10,
         "quantite": None, "limit_par_jour": True},
        {"id": "ticket_gold_lancement", "nom": "Ticket Goldé (Lancement)", "prix": 1,
         "quantite": None, "limit_per_personne": 1, "requires_riot": True},
        {"id": "titre_client_passage", "nom": "Client de Passage", "prix": 300,
         "quantite": None, "limit_per_personne": 1, "titre": True, "unlocks_palier": 2},
    ],
    "2": [
        {"id": "role_esclave_bot", "nom": "Esclave du Bot", "prix": 1000,
         "quantite": None, "limit_per_personne": 1, "role_id_key": "role_esclave_bot"},
        {"id": "titre_actionnaire", "nom": "Actionnaire", "prix": 1200,
         "quantite": None, "limit_per_personne": 1, "titre": True, "unlocks_palier": 3},
    ],
    "3": [
        {"id": "code_100_tokens", "nom": "Code 100 Tokens", "prix": 1500,
         "quantite": None, "limit_per_personne": 1, "manual": True},
        {"id": "titre_membre_conseil", "nom": "Membre du conseil", "prix": 2500,
         "quantite": None, "limit_per_personne": 1, "titre": True, "unlocks_palier": 4},
    ],
    "4": [
        {"id": "titre_proprietaire", "nom": "Propriétaire des lieux", "prix": 3000,
         "quantite": None, "limit_per_personne": 1, "titre": True},
        {"id": "vip_gobosteur", "nom": "VIP Gobosteur", "prix": 5000,
         "quantite": None, "prix_augmente": True, "increment": 1000, "manual": True},
        {"id": "vip_opesanec", "nom": "VIP Opesanec", "prix": 5000,
         "quantite": None, "prix_augmente": True, "increment": 1000, "manual": True},
        {"id": "code_chibi_medaillons", "nom": "Code Chibi 10 médaillons", "prix": 5000,
         "quantite": 1, "manual": True},
        {"id": "coaching_yaroy", "nom": "Coaching Yaroy", "prix": 5000,
         "quantite": None, "prix_augmente": True, "increment": 500,
         "cooldown_jours": 14, "last_purchase_global": None, "manual": True},
    ],
}

def load_boutique_ref():
    if os.path.exists(BOUTIQUE_REF_PATH) and os.path.getsize(BOUTIQUE_REF_PATH) > 0:
        with open(BOUTIQUE_REF_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"channel_id": None, "message_id": None}


def save_boutique_ref():
    with open(BOUTIQUE_REF_PATH, "w", encoding="utf-8") as f:
        json.dump(boutique_message_ref, f)


boutique_message_ref.update(load_boutique_ref())


async def update_boutique_message(bot: discord.Client):
    if boutique_message_ref["message_id"] is None:
        return False
    channel = bot.get_channel(boutique_message_ref["channel_id"])
    if channel is None:
        return False
    try:
        message = await channel.fetch_message(boutique_message_ref["message_id"])
        await message.edit(embed=build_boutique_embed())
        return True
    except discord.NotFound:
        return False

@tasks.loop(hours=1)
async def auto_update_boutique_message(bot: discord.Client):
    await update_boutique_message(bot)

PARIS_TZ = ZoneInfo("Europe/Paris")
RESET_HOUR = 10


def get_current_reset_boundary() -> datetime:
    """Renvoie l'horodatage du dernier passage à 10h Paris (aujourd'hui si on est après 10h, hier sinon)."""
    now = datetime.now(PARIS_TZ)
    boundary = now.replace(hour=RESET_HOUR, minute=0, second=0, microsecond=0)
    if now < boundary:
        boundary -= timedelta(days=1)
    return boundary

def parse_last_purchase(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PARIS_TZ)
    return dt

def get_cooldown_status(item: dict) -> str | None:
    """Renvoie un texte de statut si l'item est en cooldown global, sinon None."""
    if not item.get("cooldown_jours") or not item.get("last_purchase_global"):
        return None
    last_purchase_dt = parse_last_purchase(item["last_purchase_global"])
    next_available = last_purchase_dt + timedelta(days=item["cooldown_jours"])
    now = datetime.now(PARIS_TZ)
    if now >= next_available:
        return None
    jours_restants = (next_available - now).days
    heures_restantes = (next_available - now).seconds // 3600
    if jours_restants > 0:
        return f"⏳ Cooldown : {jours_restants}j {heures_restantes}h"
    return f"⏳ Cooldown : {heures_restantes}h"

def get_limit_text(item: dict) -> str:
    if item.get("titre") or item.get("role_id_key"):
        return ""
    if item.get("limit_per_personne"):
        n = item["limit_per_personne"]
        return f" (limité à {n} par personne)"
    return ""

def get_titre_text(item: dict) -> str:
    if item.get("titre"):
        return f' — Titre "{item["nom"]}"'
    return ""

def get_unlock_text(item: dict) -> str:
    if item.get("unlocks_palier"):
        return f" — Débloque le Palier {item['unlocks_palier']}"
    return ""

def get_display_name(item: dict) -> str:
    if item.get("titre"):
        return f'Titre "{item["nom"]}"'
    if item.get("role_id_key"):
        return f'Rôle discord "{item["nom"]}"'
    return item["nom"]

RANK_ROLE_IDS = {
    int(role_id) for role_id in os.getenv("RANK_ROLE_IDS", "").split(",") if role_id
}


def has_riot_linked(member: discord.Member) -> bool:
    member_role_ids = {role.id for role in member.roles}
    return bool(member_role_ids & RANK_ROLE_IDS)

def load_data() -> dict:
    if os.path.exists(DATA_PATH) and os.path.getsize(DATA_PATH) > 0:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data: dict):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_users() -> dict:
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_users(users: dict):
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_boutique() -> dict:
    if os.path.exists(BOUTIQUE_PATH) and os.path.getsize(BOUTIQUE_PATH) > 0:
        with open(BOUTIQUE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    save_boutique(DEFAULT_CATALOGUE)
    return DEFAULT_CATALOGUE


def save_boutique(boutique: dict):
    with open(BOUTIQUE_PATH, "w", encoding="utf-8") as f:
        json.dump(boutique, f, ensure_ascii=False, indent=2)

def find_item(palier: str, item_id: str = None, nom: str = None):
    boutique = get_boutique()
    for item in boutique.get(palier, []):
        if (item_id and item["id"] == item_id) or (nom and item["nom"].lower() == nom.lower()):
            return item
    return None


def update_item(palier: str, item_id: str = None, nom: str = None, **changes):
    """Charge, modifie en une seule passe, sauvegarde. Évite les incohérences
    entre plusieurs get_boutique()/save_boutique() séparés."""
    boutique = get_boutique()
    for item in boutique.get(palier, []):
        if (item_id and item["id"] == item_id) or (nom and item["nom"].lower() == nom.lower()):
            item.update(changes)
            save_boutique(boutique)
            return item
    return None


def get_user_boutique_state(user_id: str) -> dict:
    users = load_users()
    user_data = users.setdefault(user_id, {})
    state = user_data.setdefault("boutique", {"palier_debloque": 1, "achats": {}})
    save_users(users)
    return state


def has_access_to_palier(user_id: str, palier: int) -> bool:
    if palier == 1:
        return True
    state = get_user_boutique_state(user_id)
    return state.get("palier_debloque", 1) >= palier


def try_purchase(guild_member: discord.Member, palier: str, item: dict):
    user_id = str(guild_member.id)
    users = load_users()
    user_data = users.setdefault(user_id, {"monnaie": 0})
    state = user_data.setdefault("boutique", {"palier_debloque": 1, "achats": {}})
    achats = state.setdefault("achats", {})
    item_id = item["id"]
    now = datetime.now(PARIS_TZ)
    historique = achats.get(item_id, {"count": 0, "last_purchase": None})

    prix = item["prix"]
    monnaie = user_data.get("monnaie", 0)

    if monnaie < prix:
        return False, f"Il te manque {prix - monnaie} {EMOJI_WTBIFF} pour acheter **{item['nom']}**."

    if item.get("requires_riot") and not has_riot_linked(guild_member):
        return False, "Tu dois avoir lié ton compte Riot pour acheter ça."

    if item.get("quantite") is not None and item["quantite"] <= 0:
        return False, f"**{item['nom']}** est en rupture de stock."

    if item.get("limit_per_personne") and historique["count"] >= item["limit_per_personne"]:
        return False, f"Tu as déjà atteint la limite d'achat pour **{item['nom']}**."

    if item.get("limit_par_jour") and historique["last_purchase"]:
        last_purchase_dt = datetime.fromisoformat(historique["last_purchase"])
        if last_purchase_dt >= get_current_reset_boundary():
            return False, f"Tu as déjà acheté **{item['nom']}** aujourd'hui (reset à 10h)."

    if item.get("cooldown_jours") and item.get("last_purchase_global"):
        last_purchase_dt = parse_last_purchase(item["last_purchase_global"])
        next_available = last_purchase_dt + timedelta(days=item["cooldown_jours"])
        if now < next_available:
            jours_restants = (next_available - now).days
            return False, f"**{item['nom']}** est en cooldown encore {jours_restants} jour(s)."

    user_data["monnaie"] = monnaie - prix
    historique["count"] += 1
    historique["last_purchase"] = now.isoformat()
    achats[item_id] = historique

    if item.get("titre"):
        titres = user_data.setdefault("titres_possedes", [])
        if item["nom"] not in titres:
            titres.append(item["nom"])

    if item.get("unlocks_palier"):
        state["palier_debloque"] = max(state.get("palier_debloque", 1), item["unlocks_palier"])

    users[user_id] = user_data
    save_users(users)

    changes = {}
    if item.get("quantite") is not None:
        changes["quantite"] = item["quantite"] - 1
    if item.get("prix_augmente"):
        changes["prix"] = item["prix"] + item.get("increment", PRICE_INCREMENT)
    if item.get("cooldown_jours"):
        changes["last_purchase_global"] = now.isoformat()
    if changes:
        update_item(palier, item_id=item_id, **changes)

    if item_id == "ticket_loterie":
        loterie.add_ticket(user_id)
    return True, f"Achat de **{item['nom']}** confirmé pour {prix} {EMOJI_WTBIFF} !"


async def deliver_item(interaction: discord.Interaction, item: dict):
    if item.get("role_id_key"):
        role_id = ROLE_IDS.get(item["role_id_key"])
        role = interaction.guild.get_role(role_id) if role_id else None
        if role:
            await interaction.user.add_roles(role, reason=f"Achat boutique : {item['nom']}")
        else:
            item["manual"] = True

    if item.get("manual"):
        await create_ticket_channel(
            interaction.guild,
            interaction.user,
            f"{interaction.user.name}-{item['id']}",
            description=(
                f"{interaction.user.mention} a acheté **{item['nom']}** "
                f"({item['prix']} {EMOJI_WTBIFF})."
            ),
        )


def build_boutique_embed() -> discord.Embed:
    boutique = get_boutique()
    embed = discord.Embed(title="Boutique", color=discord.Color.gold())
    for palier, items in boutique.items():
        lignes = []
        for item in items:
            nom = get_display_name(item)
            stock = f" (stock: {item['quantite']})" if item.get("quantite") is not None else ""
            limite = get_limit_text(item)
            cooldown = get_cooldown_status(item)
            statut = f" — {cooldown}" if cooldown else ""
            unlock = get_unlock_text(item)
            lignes.append(f"• {nom} — {item['prix']} {EMOJI_WTBIFF}{stock}{limite}{unlock}{statut}")
        emoji = PALIER_EMOJIS.get(palier, "")
        embed.add_field(name=f"{emoji} Palier {palier}", value="\n".join(lignes) or "Aucun lot", inline=False)
    return embed


def build_palier_embed(palier: str) -> discord.Embed:
    boutique = get_boutique()
    items = boutique.get(palier, [])
    embed = discord.Embed(title=f"Palier {palier}", color=discord.Color.blurple())
    for item in items:
        nom = get_display_name(item)
        stock = f" (stock: {item['quantite']})" if item.get("quantite") is not None else ""
        limite = get_limit_text(item)
        cooldown = get_cooldown_status(item)
        unlock = get_unlock_text(item)
        valeur = f"{item['prix']} {EMOJI_WTBIFF}{stock}{limite}{unlock}"
        if cooldown:
            valeur += f"\n{cooldown}"
        embed.add_field(name=nom, value=valeur, inline=False)
    return embed


class ConfirmAchatView(discord.ui.View):
    def __init__(self, palier: str, item: dict):
        super().__init__(timeout=60)
        self.palier = palier
        self.item = item

    @discord.ui.button(label="Confirmer l'achat", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, message = try_purchase(interaction.user, self.palier, self.item)
        if success:
            await deliver_item(interaction, self.item)
            await update_boutique_message(interaction.client)
        await interaction.response.edit_message(content=message, embed=None, view=None)


class PalierItemSelect(discord.ui.Select):
    def __init__(self, palier: str):
        boutique = get_boutique()
        options = [
            discord.SelectOption(label=item["nom"], description=f"{item['prix']}", value=item["id"])
            for item in boutique.get(palier, [])
        ]
        super().__init__(placeholder="Choisis un lot", options=options)
        self.palier = palier

    async def callback(self, interaction: discord.Interaction):
        item = find_item(self.palier, item_id=self.values[0])
        if item is None:
            await interaction.response.edit_message(content="Ce lot n'existe plus.", embed=None, view=None)
            return
        await interaction.response.edit_message(
            content=f"Confirmer l'achat de **{item['nom']}** pour {item['prix']} {EMOJI_WTBIFF} ?",
            embed=None,
            view=ConfirmAchatView(self.palier, item),
        )


class PalierView(discord.ui.View):
    def __init__(self, palier: str):
        super().__init__(timeout=60)
        self.add_item(PalierItemSelect(palier))


class BoutiqueView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket loterie", style=discord.ButtonStyle.primary, custom_id="boutique_loterie")
    async def loterie_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        item = find_item("1", item_id="ticket_loterie")
        await interaction.response.send_message(
            content=f"Confirmer l'achat de **{item['nom']}** pour {item['prix']} {EMOJI_WTBIFF} ?",
            view=ConfirmAchatView("1", item),
            ephemeral=True,
        )

    async def palier_callback(self, interaction: discord.Interaction, palier: str):
        if not has_access_to_palier(str(interaction.user.id), int(palier)):
            await interaction.response.send_message(
                f"Tu n'as pas encore débloqué le Palier {palier}.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=build_palier_embed(palier), view=PalierView(palier), ephemeral=True
        )

    @discord.ui.button(label=f"{PALIER_EMOJIS['1']} Palier 1", style=discord.ButtonStyle.secondary, custom_id="boutique_palier_1")
    async def palier1_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.palier_callback(interaction, "1")

    @discord.ui.button(label=f"{PALIER_EMOJIS['2']} Palier 2", style=discord.ButtonStyle.secondary, custom_id="boutique_palier_2")
    async def palier2_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.palier_callback(interaction, "2")

    @discord.ui.button(label=f"{PALIER_EMOJIS['3']} Palier 3", style=discord.ButtonStyle.secondary, custom_id="boutique_palier_3")
    async def palier3_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.palier_callback(interaction, "3")

    @discord.ui.button(label=f"{PALIER_EMOJIS['4']} Palier 4", style=discord.ButtonStyle.secondary, custom_id="boutique_palier_4")
    async def palier4_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.palier_callback(interaction, "4")

def setup(bot):
    bot.add_view(BoutiqueView())

    if not auto_update_boutique_message.is_running():
        auto_update_boutique_message.start(bot)

    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="setup_boutique", description="Envoie le message de la boutique")
    async def setup_boutique(interaction: discord.Interaction):
        msg = await interaction.channel.send(embed=build_boutique_embed(), view=BoutiqueView())
        boutique_message_ref["channel_id"] = msg.channel.id
        boutique_message_ref["message_id"] = msg.id
        save_boutique_ref()
        await interaction.response.send_message("Boutique envoyée ✅", ephemeral=True)

    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="boutique_add", description="Ajoute un lot à la boutique")
    async def boutique_add(
        interaction: discord.Interaction,
        palier: str,
        nom: str,
        prix: int,
        quantite: int = None,
        limite_par_personne: int = None,
    ):
        boutique = get_boutique()
        if palier not in boutique:
            await interaction.response.send_message("Palier invalide (1 à 4).", ephemeral=True)
            return
        item_id = nom.lower().replace(" ", "_")
        nouvel_item = {
            "id": item_id,
            "nom": nom,
            "prix": prix,
            "quantite": quantite,
            "manual": True,
        }
        if limite_par_personne is not None:
            nouvel_item["limit_per_personne"] = limite_par_personne
        boutique[palier].append(nouvel_item)
        save_boutique(boutique)
        await update_boutique_message(interaction.client)
        await interaction.response.send_message(f"**{nom}** ajouté au Palier {palier} ✅", ephemeral=True)

    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="boutique_delete", description="Supprime un lot de la boutique")
    async def boutique_delete(interaction: discord.Interaction, palier: str, nom: str):
        boutique = get_boutique()
        item = find_item(palier, nom=nom)
        if item is None:
            await interaction.response.send_message("Lot introuvable.", ephemeral=True)
            return
        boutique[palier].remove(item)
        save_boutique(boutique)
        await update_boutique_message(interaction.client)
        await interaction.response.send_message(f"**{nom}** supprimé ✅", ephemeral=True)

    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="boutique_change_quantity", description="Modifie la quantité d'un lot (laisser vide = illimité)")
    async def boutique_change_quantity(interaction: discord.Interaction, palier: str, nom: str, quantite: int = None):
        item = update_item(palier, nom=nom, quantite=quantite)
        if item is None:
            await interaction.response.send_message("Lot introuvable.", ephemeral=True)
            return
        await update_boutique_message(interaction.client)
        valeur_affichee = quantite if quantite is not None else "illimitée"
        await interaction.response.send_message(f"Quantité de **{nom}** mise à {valeur_affichee} ✅", ephemeral=True)

    @app_commands.default_permissions(administrator=True)
    @bot.tree.command(name="boutique_change_price", description="Modifie le prix d'un lot")
    async def boutique_change_price(interaction: discord.Interaction, palier: str, nom: str, prix: int):
        item = update_item(palier, nom=nom, prix=prix)
        if item is None:
            await interaction.response.send_message("Lot introuvable.", ephemeral=True)
            return
        await update_boutique_message(interaction.client)
        await interaction.response.send_message(f"Prix de **{nom}** mis à {prix} ✅", ephemeral=True)