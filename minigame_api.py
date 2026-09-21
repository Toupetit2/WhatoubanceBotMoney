import os
import requests
import random
import asyncio

from playwright.async_api import async_playwright


# ============================================================
# RIOT API
# ============================================================

RIOT_API_KEY = os.getenv("RIOT_API_KEY")

SERVER_LIST = ["na1", "euw1"]


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
    ("diamond", "I"), ("diamond", "II"), ("diamond", "III"), ("diamond", "IV"),
    ("emerald", "I"), ("emerald", "II"), ("emerald", "III"), ("emerald", "IV"),
    ("platinum", "I"), ("platinum", "II"), ("platinum", "III"), ("platinum", "IV"),
    ("gold", "I"), ("gold", "II"), ("gold", "III"), ("gold", "IV"),
    ("silver", "I"), ("silver", "II"), ("silver", "III"), ("silver", "IV"),
    ("bronze", "I"), ("bronze", "II"), ("bronze", "III"), ("bronze", "IV"),
    ("iron", "I"), ("iron", "II"), ("iron", "III"), ("iron", "IV"),
]


def get_top_ladder(server, min_players=50):
    """Récupère une liste de joueurs du ladder classé, en descendant les
    tiers jusqu'à atteindre min_players. Ne renvoie jamais None."""
    players = []
    base_url = f"https://{server}.api.riotgames.com/tft/league/v1"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    for tier, division in TIERS:
        if division is None:
            url = f"{base_url}/{tier}"
        else:
            url = f"{base_url}/entries/{tier.upper()}/{division}"

        try:
            response = requests.get(
                url, headers=headers, params={"queue": "RANKED_TFT"}, timeout=10
            )
        except requests.RequestException as exc:
            print(f"Erreur réseau sur {url} : {exc}")
            continue

        if response.status_code != 200:
            print(f"Erreur Riot API ({response.status_code}) sur {url} : {response.text[:300]}")
            continue

        data = response.json()
        entries = data if isinstance(data, list) else data.get("entries", [])
        players.extend(entries)

        if len(players) >= min_players:
            break

    return players


def get_random_puuid():
    server = random.choice(SERVER_LIST)
    player_list = get_top_ladder(server)

    if not player_list:
        print(f"Aucun joueur récupéré pour le serveur {server}.")
        return None, server

    return random.choice(player_list)["puuid"], server


def get_random_gameid():
    puuid, platform = get_random_puuid()
    if puuid is None:
        print("Impossible de récupérer un puuid, abandon.")
        return None

    cluster = get_cluster(platform)
    url = f"https://{cluster}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        response = requests.get(url, headers=headers, params={"count": 5}, timeout=10)
    except requests.RequestException as exc:
        print(f"Erreur réseau Riot API : {exc}")
        return None

    if response.status_code != 200:
        print(f"Erreur Riot API ({response.status_code}) sur {url} : {response.text[:300]}")
        return None

    match_ids = response.json()
    if not match_ids:
        print("Aucun match trouvé pour ce joueur.")
        return None

    while match_ids:
        match_id = random.choice(match_ids)
        url = f"https://{cluster}.api.riotgames.com/tft/match/v1/matches/{match_id}"

        try:
            response = requests.get(url, headers=headers, timeout=10)
        except requests.RequestException as exc:
            print(f"Erreur réseau Riot API : {exc}")
            match_ids.remove(match_id)
            continue

        if response.status_code != 200:
            print(f"Erreur Riot API ({response.status_code}) sur {url} : {response.text[:300]}")
            match_ids.remove(match_id)
            continue

        match_info = response.json()["info"]
        is_ranked_solo = match_info["queue_id"] == 1100
        is_set_18 = match_info.get("tft_set_number") == 18

        if is_ranked_solo and is_set_18:
            return match_id

        match_ids.remove(match_id)

    # Plus aucun match ranked solo trouvé parmi les candidats : on retente
    # avec un autre joueur.
    return get_random_gameid()


# ============================================================
# PLAYWRIGHT / SCREENSHOTS
# ============================================================

CUSTOM_CSS = """
.bg-bg2 { background-color: #0F3058 !important; }

[class*='gap-y-5'][class*='grid'] {
    grid-template-columns: repeat(15, minmax(0, 1fr)) !important;
}

* { animation: none !important; transition: none !important; }
::-webkit-scrollbar { display: none !important; }
body { white-space: nowrap; }

iframe[src*="adsrvr.org"],
iframe[src*="btloader.com"],
iframe[src*="p7cloud.net"],
iframe[src*="doubleclick"],
iframe[src*="googlesyndication"],
iframe[src*="googleadservices"],
iframe[src*="adservice"],
img[src*="adsrvr.org"],
img[src*="doubleclick"],
img[src*="googlesyndication"],
img[src*="googleadservices"],
img[src*="adservice"] {
    display: none !important;
    visibility: hidden !important;
}
"""

# Domaines publicitaires/tracking bloqués au niveau réseau.
AD_BLOCKED_HOSTS = (
    "adsrvr.org",
    "btloader.com",
    "p7cloud.net",
    "doubleclick.net",
    "googlesyndication.com",
    "googleadservices.com",
    "google-analytics.com",
    "googletagmanager.com",
)

# Sélecteurs des éléments publicitaires masqués côté DOM (JS).
AD_ELEMENT_SELECTORS_JS = """[
    'iframe[src*="adsrvr.org"]',
    'iframe[src*="btloader.com"]',
    'iframe[src*="p7cloud.net"]',
    'iframe[src*="doubleclick"]',
    'iframe[src*="googlesyndication"]',
    'iframe[src*="googleadservices"]',
    'iframe[src*="adservice"]',
    'img[src*="adsrvr.org"]',
    'img[src*="doubleclick"]',
    'img[src*="googlesyndication"]',
    'img[src*="googleadservices"]',
    'img[src*="adservice"]'
]"""

COOKIE_SELECTORS = [
    "button:has-text('Accepter')",
    "[role='button']:has-text('Accepter')",
    "text=Accepter",
    "button:has-text('Accept')",
    "[role='button']:has-text('Accept')",
    "text=Accept",
]

GRID_SELECTOR = "[class*='gap-y-5'][class*='grid']"
MAX_ITEMS_PER_ROW = 15

screenshot_semaphore = asyncio.Semaphore(1)
_playwright = None
_browser = None


def is_blocked_ad_url(url: str) -> bool:
    url_lower = url.lower()
    return any(host in url_lower for host in AD_BLOCKED_HOSTS)


async def get_browser():
    """Réutilise une seule instance de navigateur au lieu d'en relancer une
    à chaque capture."""
    global _playwright, _browser

    if _browser is None or not _browser.is_connected():
        if _playwright is None:
            _playwright = await async_playwright().start()

        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-background-networking",
                "--disable-component-update",
            ],
        )

    return _browser


async def wait_for_grids(page, timeout_ms=15000):
    """Attend que tactics.tools ait terminé de construire les grids dans le
    DOM (le rendu est dynamique, les grids n'existent pas forcément
    immédiatement après domcontentloaded)."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_ms / 1000

    while loop.time() < deadline:
        count = await page.evaluate(
            "selector => document.querySelectorAll(selector).length",
            GRID_SELECTOR,
        )
        if count > 0:
            return count
        await asyncio.sleep(0.1)

    return 0


async def has_too_many_items(page) -> bool:
    """True si une grille contient plus de MAX_ITEMS_PER_ROW enfants."""
    max_children = await page.evaluate(
        """
        selector => {
            const grids = document.querySelectorAll(selector);
            let max = 0;
            for (const grid of grids) {
                if (grid.children.length > max) max = grid.children.length;
            }
            return max;
        }
        """,
        GRID_SELECTOR,
    )
    return max_children > MAX_ITEMS_PER_ROW


async def remove_ad_elements(page):
    """Masque les éléments publicitaires/tracking déjà présents dans le DOM.

    On masque uniquement l'élément lui-même (display: none), jamais son
    parent : le parent peut porter le fond visuel du bloc de layout
    englobant, et le supprimer laisse apparaître le fond noir de la page
    derrière."""
    try:
        await page.evaluate(
            f"""
            () => {{
                const selectors = {AD_ELEMENT_SELECTORS_JS};
                for (const selector of selectors) {{
                    for (const el of document.querySelectorAll(selector)) {{
                        el.style.setProperty('display', 'none', 'important');
                    }}
                }}
            }}
            """
        )
    except Exception as exc:
        print(f"[ads] Nettoyage DOM ignoré : {type(exc).__name__}: {exc}")


async def install_ad_cleanup(page):
    """Installe un MutationObserver pour masquer les publicités injectées
    après le chargement initial (même logique que remove_ad_elements :
    on masque, on ne supprime jamais le parent)."""
    try:
        await page.evaluate(
            f"""
            () => {{
                if (window.__tftAdCleanupInstalled) return;
                window.__tftAdCleanupInstalled = true;

                const selectors = {AD_ELEMENT_SELECTORS_JS};

                const isAdElement = (el) =>
                    el && el.matches && selectors.some(s => el.matches(s));

                const hide = (el) =>
                    el.style.setProperty('display', 'none', 'important');

                const observer = new MutationObserver(mutations => {{
                    for (const mutation of mutations) {{
                        for (const node of mutation.addedNodes) {{
                            if (node.nodeType !== Node.ELEMENT_NODE) continue;

                            if (isAdElement(node)) {{
                                hide(node);
                                continue;
                            }}

                            for (const child of node.querySelectorAll('iframe, img')) {{
                                if (isAdElement(child)) hide(child);
                            }}
                        }}
                    }}
                }});

                observer.observe(document.documentElement, {{
                    childList: true,
                    subtree: true,
                }});
            }}
            """
        )
    except Exception as exc:
        print(f"[ads] MutationObserver non installé : {type(exc).__name__}: {exc}")


async def accept_cookies(page, timeout_ms=8000) -> bool:
    """Tente d'accepter les cookies, avec polling sur plusieurs secondes
    car le bandeau peut apparaître après l'hydratation React. Cherche
    d'abord dans la page principale, puis dans les iframes (certains CMP
    affichent leur bandeau dans une iframe tierce)."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_ms / 1000

    while loop.time() < deadline:
        for selector in COOKIE_SELECTORS:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=300):
                    await locator.click(timeout=2000)
                    await page.wait_for_timeout(300)
                    return True
            except Exception:
                pass

        for frame in page.frames:
            if frame == page.main_frame:
                continue
            for selector in COOKIE_SELECTORS:
                try:
                    locator = frame.locator(selector).first
                    if await locator.is_visible(timeout=300):
                        await locator.click(timeout=2000)
                        await page.wait_for_timeout(300)
                        return True
                except Exception:
                    pass

        await asyncio.sleep(0.3)

    return False


async def screenshot_url(url: str, output_path: str = "screenshot.png") -> bool:
    """Capture une page tactics.tools.

    Retourne False si les grids n'apparaissent pas, si une grille contient
    plus de MAX_ITEMS_PER_ROW éléments, ou si une erreur survient pendant
    la capture. Retourne True si le screenshot a été créé."""
    async with screenshot_semaphore:
        browser = await get_browser()

        context = await browser.new_context(
            viewport={"width": 1280, "height": 750},
            device_scale_factor=2,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )

        async def handle_route(route):
            if is_blocked_ad_url(route.request.url):
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", handle_route)

        # Réduit les traces les plus évidentes du fingerprint headless.
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr', 'en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
            """
        )

        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            await install_ad_cleanup(page)
            await remove_ad_elements(page)

            grid_count = await wait_for_grids(page, timeout_ms=15000)
            if grid_count == 0:
                print(f"[screenshot] Aucun grid trouvé : {url}")
                return False

            await accept_cookies(page, timeout_ms=5000)
            await remove_ad_elements(page)

            await page.add_style_tag(content=CUSTOM_CSS)
            await page.wait_for_timeout(500)
            await remove_ad_elements(page)

            if await has_too_many_items(page):
                print(f"[screenshot] Trop d'éléments dans une grille : {url}")
                return False

            try:
                await page.evaluate(
                    """
                    async () => {
                        if (!document.fonts) return;
                        await Promise.race([
                            document.fonts.ready,
                            new Promise(resolve => setTimeout(resolve, 3000)),
                        ]);
                    }
                    """
                )
            except Exception:
                pass

            await remove_ad_elements(page)
            await page.evaluate("() => window.scrollTo(0, 0)")
            await page.wait_for_timeout(200)

            await page.screenshot(path=output_path, animations="disabled", timeout=60000)
            return True

        except Exception as exc:
            print(f"[screenshot] Erreur pour {url} : {type(exc).__name__}: {exc}")
            return False

        finally:
            await page.close()
            await context.close()


async def shutdown_browser():
    """Ferme proprement le navigateur et Playwright. À appeler à l'arrêt du bot."""
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