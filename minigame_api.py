import os
import requests
import random
import asyncio

from playwright.async_api import async_playwright


# ============================================================
# RIOT API
# ============================================================

RIOT_API_KEY = os.getenv("RIOT_API_KEY")

SERVER_LIST = [
    "na1",
    "euw1",
]


def get_cluster(platform: str) -> str:
    if platform in ("na1", "br1", "la1", "la2"):
        return "americas"

    if platform in ("kr", "jp1"):
        return "asia"

    if platform in ("eun1", "euw1", "tr1", "me1", "ru"):
        return "europe"

    if platform in ("oc1", "sg2", "tw2", "vn2"):
        return "sea"

    raise ValueError(f"Plateforme inconnue : {platform}")


TIERS = [
    ("challenger", None),
    ("grandmaster", None),
    ("master", None),

    ("diamond", "I"),
    ("diamond", "II"),
    ("diamond", "III"),
    ("diamond", "IV"),

    ("emerald", "I"),
    ("emerald", "II"),
    ("emerald", "III"),
    ("emerald", "IV"),

    ("platinum", "I"),
    ("platinum", "II"),
    ("platinum", "III"),
    ("platinum", "IV"),

    ("gold", "I"),
    ("gold", "II"),
    ("gold", "III"),
    ("gold", "IV"),

    ("silver", "I"),
    ("silver", "II"),
    ("silver", "III"),
    ("silver", "IV"),

    ("bronze", "I"),
    ("bronze", "II"),
    ("bronze", "III"),
    ("bronze", "IV"),

    ("iron", "I"),
    ("iron", "II"),
    ("iron", "III"),
    ("iron", "IV"),
]


def get_top_ladder(server, min_players=50):
    """
    Récupère une liste de joueurs du ladder classé, en descendant
    les tiers jusqu'à atteindre min_players.

    Ne renvoie jamais None :
    au pire, une liste vide si aucun tier n'a répondu correctement.
    """

    players = []

    base_url = (
        f"https://{server}.api.riotgames.com"
        "/tft/league/v1"
    )

    headers = {
        "X-Riot-Token": RIOT_API_KEY
    }

    for tier, division in TIERS:

        if division is None:
            url = f"{base_url}/{tier}"
        else:
            # L'endpoint /entries/{tier}/{division} attend
            # le tier en MAJUSCULES.
            url = (
                f"{base_url}/entries/"
                f"{tier.upper()}/{division}"
            )

        try:
            response = requests.get(
                url,
                headers=headers,
                params={"queue": "RANKED_TFT"},
                timeout=10,
            )

        except requests.RequestException as exc:
            print(
                f"Erreur réseau sur {url} : {exc}"
            )
            continue

        if response.status_code != 200:
            print(
                f"Erreur Riot API ({response.status_code}) "
                f"sur {url} : {response.text[:300]}"
            )
            continue

        data = response.json()

        # /challenger, /grandmaster, /master
        # renvoient {"entries": [...]}
        #
        # /entries/{tier}/{division}
        # renvoie directement une liste.
        if isinstance(data, list):
            entries = data
        else:
            entries = data.get("entries", [])

        players.extend(entries)

        if len(players) >= min_players:
            break

    return players


def get_random_puuid():
    server = random.choice(SERVER_LIST)

    player_list = get_top_ladder(server)

    if not player_list:
        print(
            f"Aucun joueur récupéré pour le serveur {server}."
        )
        return None, server

    return random.choice(player_list)["puuid"], server


def get_random_gameid():
    puuid, platform = get_random_puuid()

    if puuid is None:
        print(
            "Impossible de récupérer un puuid, abandon."
        )
        return None

    cluster = get_cluster(platform)

    url = (
        f"https://{cluster}.api.riotgames.com"
        f"/tft/match/v1/matches/by-puuid/{puuid}/ids"
    )

    headers = {
        "X-Riot-Token": RIOT_API_KEY
    }

    params = {
        "count": 5,  # game count
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10,
        )
    except requests.RequestException as exc:
        print(
            f"Erreur réseau Riot API : {exc}"
        )
        return None

    if response.status_code != 200:
        print(
            f"Erreur Riot API ({response.status_code}) "
            f"sur {url} : {response.text[:300]}"
        )
        return None

    match_ids = response.json()

    if not match_ids:
        print(
            "Aucun match trouvé pour ce joueur."
        )
        return None

    while match_ids:

        match_id = random.choice(match_ids)

        url = (
            f"https://{cluster}.api.riotgames.com"
            f"/tft/match/v1/matches/{match_id}"
        )

        headers = {
            "X-Riot-Token": RIOT_API_KEY
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=10,
            )
        except requests.RequestException as exc:
            print(
                f"Erreur réseau Riot API : {exc}"
            )
            match_ids.remove(match_id)
            continue

        if response.status_code != 200:
            print(
                f"Erreur Riot API ({response.status_code}) "
                f"sur {url} : {response.text[:300]}"
            )
            match_ids.remove(match_id)
            continue

        match_info = response.json()["info"]

        is_ranked_solo = (
            match_info["queue_id"] == 1100
        )

        is_set_18 = (
            match_info.get("tft_set_number") == 18
        )

        if is_ranked_solo and is_set_18:
            return match_id

        match_ids.remove(match_id)

    # Plus aucun match ranked solo trouvé parmi les candidats :
    # on retente avec un autre joueur plutôt que de boucler
    # indéfiniment sur le même.
    return get_random_gameid()


# ============================================================
# PLAYWRIGHT / SCREENSHOTS
# ============================================================

CUSTOM_CSS = """
.bg-bg2 {
    background-color: #0F3058 !important;
}

[class*='gap-y-5'][class*='grid'] {
    grid-template-columns: repeat(
        15,
        minmax(0, 1fr)
    ) !important;
}

* {
    animation: none !important;
    transition: none !important;
}

html {
    scrollbar-width: none;
}

html::-webkit-scrollbar {
    display: none;
}

.pt-\\[1px\\].text-white2.text-xs.font-medium {
    white-space: nowrap !important;
}
"""


screenshot_semaphore = asyncio.Semaphore(1)

_playwright = None
_browser = None


MAX_ITEMS_PER_ROW = 15

GRID_SELECTOR = (
    "[class*='gap-y-5'][class*='grid']"
)


async def get_browser():
    """
    Réutilise une seule instance de navigateur
    au lieu d'en relancer une à chaque capture.
    """

    global _playwright, _browser

    if (
        _browser is None
        or not _browser.is_connected()
    ):
        if _playwright is None:
            _playwright = (
                await async_playwright().start()
            )

        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

    return _browser


async def wait_for_grids(
    page,
    timeout_ms=15000,
):
    """
    Attend que tactics.tools ait terminé de construire
    les grids dans le DOM.

    IMPORTANT :
    les grids n'existent pas forcément immédiatement après
    domcontentloaded.

    On utilise directement document.querySelectorAll()
    plutôt que page.wait_for_selector(), car le rendu
    de tactics.tools est dynamique.
    """

    loop = asyncio.get_running_loop()

    deadline = (
        loop.time()
        + timeout_ms / 1000
    )

    while loop.time() < deadline:

        count = await page.evaluate(
            """
            selector => {
                return document.querySelectorAll(
                    selector
                ).length;
            }
            """,
            GRID_SELECTOR,
        )

        if count > 0:
            return count

        await asyncio.sleep(0.1)

    return 0


async def has_too_many_items(page) -> bool:
    """
    True si une grille contient plus de 15 enfants.

    Le CSS force 15 colonnes.
    Au-delà de 15 éléments, le contenu passerait
    sur une deuxième ligne.
    """

    max_children = await page.evaluate(
        """
        selector => {
            const grids =
                document.querySelectorAll(selector);

            let max = 0;

            for (const grid of grids) {
                if (grid.children.length > max) {
                    max = grid.children.length;
                }
            }

            return max;
        }
        """,
        GRID_SELECTOR,
    )

    return max_children > MAX_ITEMS_PER_ROW


async def screenshot_url(
    url: str,
    output_path: str = "screenshot.png",
) -> bool:
    """
    Capture une page tactics.tools.

    Retourne False si :
    - les grids n'apparaissent pas ;
    - une grille contient plus de 15 éléments ;
    - une erreur survient pendant la capture.

    Retourne True si le screenshot a été créé.
    """

    async with screenshot_semaphore:

        browser = await get_browser()

        context = await browser.new_context(
            viewport={
                "width": 1280,
                "height": 750,
            },
            device_scale_factor=2,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )

        # Réduit les différences de comportement
        # entre le serveur et le navigateur classique.
        await context.add_init_script(
            """
            Object.defineProperty(
                navigator,
                'webdriver',
                {
                    get: () => undefined
                }
            );

            Object.defineProperty(
                navigator,
                'languages',
                {
                    get: () => [
                        'fr-FR',
                        'fr',
                        'en-US',
                        'en'
                    ]
                }
            );

            Object.defineProperty(
                navigator,
                'plugins',
                {
                    get: () => [1, 2, 3, 4, 5]
                }
            );

            window.chrome = {
                runtime: {}
            };
            """
        )

        page = await context.new_page()

        try:

            # --------------------------------------------------------
            # 1. Navigation
            # --------------------------------------------------------

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            # =========================
            # COOKIES
            # =========================
            print("🍪 Recherche du bandeau cookies...")

            try:
                # Cherche tous les éléments contenant "Accepter" ou "Accept"
                cookie_elements = await page.locator(
                    "text=/Accepter|Accept/i"
                ).all()

                print(f"🍪 Éléments trouvés : {len(cookie_elements)}")

                for i, element in enumerate(cookie_elements):
                    try:
                        visible = await element.is_visible()
                        text = await element.inner_text()

                        print(
                            f"🍪 [{i}] visible={visible} "
                            f"text={text!r}"
                        )

                        if visible:
                            await element.click(
                                timeout=3000,
                                force=True,
                            )

                            print("🍪 Bouton cookies cliqué")
                            await page.wait_for_timeout(1000)
                            break

                    except Exception as e:
                        print(f"🍪 Erreur élément {i}: {e}")

            except Exception as e:
                print(f"🍪 Erreur recherche cookies : {e}")

            # --------------------------------------------------------
            # 2. Attendre le rendu dynamique
            # --------------------------------------------------------

            grid_count = await wait_for_grids(
                page,
                timeout_ms=15000,
            )

            if grid_count == 0:
                print(
                    f"[screenshot] Aucun grid trouvé : {url}"
                )
                return False

            # --------------------------------------------------------
            # 3. Accepter les cookies si présents
            # --------------------------------------------------------

            try:
                await page.click(
                    "text=Accept",
                    timeout=3000,
                )
            except Exception:
                pass

            # --------------------------------------------------------
            # 4. Ajouter notre CSS
            # --------------------------------------------------------

            await page.add_style_tag(
                content=CUSTOM_CSS
            )

            # --------------------------------------------------------
            # 5. Attendre très brièvement que le layout
            #    se stabilise après le CSS
            # --------------------------------------------------------

            await page.wait_for_timeout(300)

            # --------------------------------------------------------
            # 6. Vérifier la taille des grids
            # --------------------------------------------------------

            if await has_too_many_items(page):
                print(
                    "[screenshot] Trop d'éléments dans "
                    f"une grille : {url}"
                )
                return False

            # --------------------------------------------------------
            # 7. Fonts
            #
            # Ne pas laisser Playwright bloquer indéfiniment
            # sur document.fonts.ready.
            # --------------------------------------------------------

            try:
                await page.evaluate(
                    """
                    async () => {
                        if (!document.fonts) {
                            return;
                        }

                        await Promise.race([
                            document.fonts.ready,
                            new Promise(resolve => {
                                setTimeout(
                                    resolve,
                                    3000
                                );
                            })
                        ]);
                    }
                    """
                )
            except Exception:
                pass

            # --------------------------------------------------------
            # 8. Revenir en haut
            # --------------------------------------------------------

            await page.evaluate(
                "window.scrollTo(0, 0)"
            )

            await page.wait_for_timeout(200)

            # --------------------------------------------------------
            # 9. Screenshot
            # --------------------------------------------------------

            await page.screenshot(
                path=output_path,
                full_page=True,
                animations="disabled",
                timeout=60000,
            )

            return True

        except Exception as exc:

            print(
                f"[screenshot] Erreur pour {url} : "
                f"{type(exc).__name__}: {exc}"
            )

            return False

        finally:
            await page.close()
            await context.close()


async def shutdown_browser():
    """
    Ferme proprement le navigateur et Playwright.

    À appeler à l'arrêt du bot.
    """

    global _browser, _playwright

    if _browser is not None:
        try:
            await _browser.close()
        except Exception:
            pass

        _browser = None

    if _playwright is not None:
        try:
            await _playwright.stop()
        except Exception:
            pass

        _playwright = None
