"""
Bot de vote automatique - Site #3 (serveur-minecraft.com)
==========================================================
Logiciel de vote autonome avec résolution reCAPTCHA v2 (Advanced Grid Solver) via Mistral.
"""

import asyncio
from playwright.async_api import async_playwright
import time
import logging
import sys
import base64
import requests
import os

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

USERNAME = "alexcaill"
VOTE_INTERVAL = 10830  # 3h + 30s
TARGET_URL = "https://serveur-minecraft.com/5104"
MISTRAL_API_KEY = "P5bTDPAhdn9g8Q2QdEvCXH5VWeGViQh2"

def solve_grid(b64_image, instruction):
    """Appel à Mistral Pixtral pour identifier les cases à cliquer."""
    url = "https://api.mistral.ai/v1/chat/completions"
    
    prompt = (
        f"Instruction: {instruction}. "
        "The image is a 3x3 grid of a reCAPTCHA challenge. "
        "Identify the numbers of the tiles where the requested object is present. "
        "Grid numbering: 1 2 3 (top), 4 5 6 (middle), 7 8 9 (bottom). "
        "Return ONLY a comma-separated list of numbers (e.g., 1,4,7). If none, return 'None'."
    )
    
    payload = {
        "model": "pixtral-12b-2409",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{b64_image}"}
                ]
            }
        ],
        "temperature": 0
    }
    
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        res_json = response.json()
        if 'choices' in res_json:
            content = res_json['choices'][0]['message']['content'].strip()
            logging.info(f"🧠 IA Response: {content}")
            if content.lower() == "none": return []
            return [int(x.strip()) for x in content.replace(" ", "").split(",") if x.strip().isdigit()]
        else:
            logging.error(f"❌ Mistral API Error: {res_json}")
            return []
    except Exception as e:
        logging.error(f"❌ Error calling Mistral: {e}")
        return []

async def perform_vote():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            logging.info(f"🌐 Navigation vers {TARGET_URL}...")
            max_retries = 3
            for i in range(max_retries):
                try:
                    await page.goto(TARGET_URL, wait_until='commit', timeout=60000)
                    break
                except Exception as e:
                    if i == max_retries - 1: raise e
                    logging.warning(f"⚠️ Tentative {i+1} échouée ({e}), nouvel essai...")
                    await page.wait_for_timeout(5000)
            
            await page.wait_for_timeout(10000) # Attendre que Cloudflare passe
            
            # 1. Pseudo
            logging.info(f"👤 Saisie du pseudo: {USERNAME}")
            await page.wait_for_selector("input#form_username")
            await page.fill("input#form_username", USERNAME)
            
            # 2. reCAPTCHA
            logging.info("🤖 Recherche du reCAPTCHA...")
            anchor_frame = None
            for frame in page.frames:
                if "anchor" in frame.url:
                    anchor_frame = frame
                    break
            
            if anchor_frame:
                logging.info("🖱️ Clic checkbox...")
                await anchor_frame.click("#recaptcha-anchor")
                await page.wait_for_timeout(4000)
                
                # Check for challenge
                bframe = None
                for frame in page.frames:
                    if "bframe" in frame.url:
                        bframe = frame
                        break
                
                has_challenge = False
                if bframe:
                    try:
                        # On attend un peu voir si les instructions apparaissent
                        await bframe.wait_for_selector(".rc-imageselect-instructions", timeout=5000)
                        has_challenge = True
                    except:
                        has_challenge = False
                
                if has_challenge:
                    logging.info("🖼️ Défi reCAPTCHA détecté !")
                    
                    # Résolution (max 3 tentatives)
                    for attempt in range(3):
                        instr_text = await bframe.inner_text(".rc-imageselect-instructions")
                        instr_text = instr_text.replace("\n", " ").strip()
                        logging.info(f"📝 Défi: {instr_text}")
                        
                        # Screenshot grid
                        grid = await bframe.wait_for_selector(".rc-imageselect-payload")
                        img_bytes = await grid.screenshot()
                        b64_img = base64.b64encode(img_bytes).decode('utf-8')
                        
                        tiles = solve_grid(b64_img, instr_text)
                        
                        if tiles:
                            # Clic sur les cases
                            all_tiles = await bframe.query_selector_all(".rc-imageselect-tile")
                            for t in tiles:
                                if 0 < t <= len(all_tiles):
                                    logging.info(f"🖱️ Clic case #{t}")
                                    await all_tiles[t-1].click()
                                    await page.wait_for_timeout(400)
                            
                            # Valider / Suivant
                            verify_btn = await bframe.wait_for_selector("#recaptcha-verify-button")
                            await verify_btn.click()
                            await page.wait_for_timeout(3000)
                            
                            # Si le défi est encore là, on recommence (image dynamique)
                            if not await bframe.is_visible(".rc-imageselect-instructions"):
                                logging.info("✅ Défi résolu !")
                                break
                        else:
                            logging.warning("⚠️ Pas de réponse de l'IA, passage au cycle suivant.")
                            break
            
            # 3. Vote Final
            logging.info("🗳️ Clique sur voter...")
            vote_btn = await page.wait_for_selector('button:has-text("Voter")')
            await vote_btn.scroll_into_view_if_needed()
            await vote_btn.click()
            
            await page.wait_for_timeout(5000)
            logging.info("✨ Cycle fini.")

        except Exception as e:
            logging.error(f"❌ Erreur: {e}")
            
        finally:
            await browser.close()
            logging.info("🔒 Navigateur fermé.")

if __name__ == "__main__":
    while True:
        logging.info("🔔 Début Vote 3")
        asyncio.run(perform_vote())
        logging.info(f"⏳ Pause 3h...")
        try:
            time.sleep(VOTE_INTERVAL)
        except KeyboardInterrupt:
            sys.exit(0)
