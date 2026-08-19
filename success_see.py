import json
import os

import discord

USERS_PATH = "users.json"
SUCCESSES_PATH = "successes.json"
BOUTIQUE_PATH = "boutique.json"


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_category_embed(user: discord.User, category: str, categories: list) -> discord.Embed:
    users = load_json(USERS_PATH)
    successes_def = load_json(SUCCESSES_PATH)

    user_data = users.get(str(user.id), {})
    succes_debloques = set(user_data.get("success", {}).get(category, []))
    succes_dict = successes_def.get(category, {})

    embed = discord.Embed(
        title=category,
        color=discord.Color.gold(),
    )
    embed.set_author(name=f"Succès de {user.display_name}")

    for sid, info in succes_dict.items():
        description = info.get("description", sid)
        if sid in succes_debloques:
            valeur = f"✅ {info.get('title', sid)}"
        else:
            valeur = "❌"
        embed.add_field(name=description, value=valeur, inline=False)

    if not succes_dict:
        embed.description = "Aucun succès dans cette catégorie."

    embed.set_footer(text=f"Page {categories.index(category) + 1}/{len(categories)}")

    return embed


def get_boutique_titles_embed(user: discord.User, categories: list) -> discord.Embed:
    boutique = load_json(BOUTIQUE_PATH)
    users = load_json(USERS_PATH)

    user_data = users.get(str(user.id), {})
    titres_possedes = set(user_data.get("titres_possedes", []))

    embed = discord.Embed(
        title="Boutique",
        color=discord.Color.gold(),
    )
    embed.set_author(name=f"Succès de {user.display_name}")

    trouve_un_titre = False
    for palier, items in boutique.items():
        for item in items:
            if not item.get("titre"):
                continue
            trouve_un_titre = True
            nom = item["nom"]
            if nom in titres_possedes:
                valeur = f'✅ Titre "{nom}"'
            else:
                valeur = "❌"
            embed.add_field(name=f"Palier {palier} — {item['prix']} WhatouBiffs", value=valeur, inline=False)

    if not trouve_un_titre:
        embed.description = "Aucun titre disponible en boutique."

    embed.set_footer(text=f"Page {categories.index('Boutique') + 1}/{len(categories)}")

    return embed


def build_page_embed(user: discord.User, category: str, categories: list) -> discord.Embed:
    if category == "Boutique":
        return get_boutique_titles_embed(user, categories)
    return get_category_embed(user, category, categories)


class SuccessesView(discord.ui.View):
    def __init__(self, user: discord.User, categories: list):
        super().__init__(timeout=120)
        self.user = user
        self.categories = categories
        self.index = 0
        self._update_buttons()

    def _update_buttons(self):
        self.previous_button.disabled = self.index == 0
        self.next_button.disabled = self.index == len(self.categories) - 1

    @discord.ui.button(label="◀ Précédent", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index -= 1
        self._update_buttons()
        embed = build_page_embed(self.user, self.categories[self.index], self.categories)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Suivant ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index += 1
        self._update_buttons()
        embed = build_page_embed(self.user, self.categories[self.index], self.categories)
        await interaction.response.edit_message(embed=embed, view=self)


def setup(bot):
    @bot.tree.command(name="get_successes", description="Affiche tes succès débloqués !")
    async def get_successes(interaction: discord.Interaction, member: discord.Member = None):
        user = member or interaction.user
        successes_def = load_json(SUCCESSES_PATH)
        categories = list(successes_def.keys()) + ["Boutique"]

        view = SuccessesView(user, categories)
        embed = build_page_embed(user, categories[0], categories)

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )