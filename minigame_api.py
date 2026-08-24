import os
import requests
import random
import imgkit

RIOT_API_KEY = os.getenv("RIOT_API_KEY")

#SERVER_LIST = [
#    "na1", "br1", "la1", "la2",
#    "kr", "jp1",
#    "eun1", "euw1", "tr1", "me1", "ru",
#    "oc1", "sg2", "tw2", "vn2",
#]
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

def get_random_puuid():
    server = random.choice(SERVER_LIST)

    url = f"https://{server}.api.riotgames.com/tft/league/v1/challenger"

    headers = {
        "X-Riot-Token": RIOT_API_KEY
    }

    params = {
        "queue": "RANKED_TFT"
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Erreur Riot API : {response.status_code}")
        return


    player_list = response.json()["entries"]

    return random.choice(player_list)["puuid"], server

def get_random_gameid():
    puuid, platform = get_random_puuid()
    if puuid is None:
        return
    
    cluster = get_cluster(platform)

    url = f"https://{cluster}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids"
    headers = {
        "X-Riot-Token": RIOT_API_KEY
    }

    params = {
        "count": 5 #game count
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Erreur Riot API : {response.status_code}")
        return

    match_ids = response.json()

    if not match_ids:
        print("Aucun match trouvé pour ce joueur.")
        return

    ranked_match_ids = []
    while match_ids != []:
        match_id = random.choice(match_ids)
        url = f"https://{cluster}.api.riotgames.com/tft/match/v1/matches/{match_id}"

        headers = {
        "X-Riot-Token": RIOT_API_KEY
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"Erreur Riot API : {response.status_code}")
            return

        is_ranked_solo = response.json()["info"]["queue_id"] == 1100

        if is_ranked_solo:
            return match_id

        match_ids.remove(match_id)

    return get_random_gameid()


from playwright.async_api import async_playwright
import asyncio

CUSTOM_CSS = """
.bg-bg2 { background-color: #0F3058 !important; }
[class*='gap-y-5'][class*='grid'] {
    grid-template-columns: repeat(15, minmax(0, 1fr)) !important;
}
* { animation: none !important; transition: none !important; }
html { scrollbar-width: none; }
html::-webkit-scrollbar { display: none; }
"""

screenshot_semaphore = asyncio.Semaphore(1)

_playwright = None
_browser = None


async def get_browser():
    """Réutilise une seule instance de navigateur au lieu d'en relancer une à chaque fois."""
    global _playwright, _browser
    if _browser is None or not _browser.is_connected():
        if _playwright is None:
            _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
    return _browser

import base64

async def screenshot_url(url: str, output_path: str = "screenshot.png"):
    async with screenshot_semaphore:
        browser = await get_browser()
        page = await browser.new_page(
            viewport={"width": 1280, "height": 750},
            device_scale_factor=2,
        )
        try:
            await page.goto(url, wait_until="load", timeout=30000)

            with open("/root/whatoubance-biff/fonts/roboto-regular.woff2", "rb") as f:
                font_b64 = base64.b64encode(f.read()).decode()
            await page.add_style_tag(content=f"""
            @font-face {{
                font-family: 'Roboto';
                src: url(data:font/woff2;base64,{font_b64}) format('woff2');
                font-weight: 350;
            }}
            * {{ font-family: 'Roboto', sans-serif !important; }}
        """)
            
            await page.evaluate("document.fonts.ready")

            try:
                await page.click("text=Accept", timeout=3000)
            except Exception:
                pass

            await page.add_style_tag(content=CUSTOM_CSS)
            await page.wait_for_timeout(500)

            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(200)

            await page.screenshot(path=output_path)
        finally:
            await page.close()


async def shutdown_browser():
    """Ferme proprement le navigateur et playwright. À appeler à l'arrêt du bot."""
    global _browser, _playwright
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None