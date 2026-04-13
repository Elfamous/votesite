"""
Bot de vote automatique - Site #2 (serveur-minecraft-vote.fr)
==========================================================
Logiciel de vote autonome pour Serenity-Craft.
"""

import asyncio
from playwright.async_api import async_playwright
import time
import logging
import sys

# Configuration des logs avec de la couleur/style (via préfixes)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

USERNAME = "AlexCaill"
VOTE_INTERVAL = 5430  # 1h30 en secondes
TARGET_URL = "https://serveur-minecraft-vote.fr/serveurs/serenity-craft-java-bedrock.2583/vote"

async def perform_vote():
    async with async_playwright() as p:
        # Lancement du navigateur
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            logging.info(f"🚀 Navigation vers {TARGET_URL}...")
            await page.goto(TARGET_URL, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # --- 1. Saisie du Pseudo ---
            logging.info(f"✍️ Saisie du pseudo : {USERNAME}")
            pseudo_input = await page.wait_for_selector("input#pseudo", timeout=10000)
            if pseudo_input:
                await pseudo_input.click()
                await pseudo_input.fill("") # Clear just in case
                await pseudo_input.type(USERNAME, delay=100)
                
            # --- 2. Clic sur le bouton de vote ---
            logging.info("🖱️ Recherche du bouton de vote...")
            # Le bouton a l'ID vote-button-action
            vote_btn = await page.wait_for_selector("button#vote-button-action", timeout=10000)
            
            if vote_btn:
                # Vérifier si on peut voter (le texte change si on a déjà voté)
                btn_text = await vote_btn.inner_text()
                if "déconnecté" in btn_text.lower() or "voter" in btn_text.lower():
                    logging.info("✅ Bouton prêt. Clic en cours...")
                    await vote_btn.click()
                    
                    # Attendre la réaction du site (reCAPTCHA invisible se déclenche ici)
                    await page.wait_for_timeout(5000)
                    
                    # --- 3. Vérification du succès ---
                    content = (await page.content()).lower()
                    if "merci" in content or "succès" in content or "confirmé" in content:
                        logging.info("✨ VOTE RÉUSSI ! Le site a validé l'action.")
                    else:
                        logging.info("🏁 Cycle terminé. Vérifiez vos récompenses en jeu.")
                else:
                    logging.warning(f"⚠️ Le bouton semble indiquer que le vote n'est pas possible : {btn_text}")

        except Exception as e:
            logging.error(f"❌ Erreur durant le vote : {e}")
            
        finally:
            await browser.close()
            logging.info("🔒 Navigateur fermé.")

if __name__ == "__main__":
    cycle = 1
    while True:
        logging.info(f"🔔 === Début du cycle de vote #{cycle} (Site #2) ===")
        asyncio.run(perform_vote())
        logging.info(f"=== Fin du cycle #{cycle} ===")
        logging.info(f"⏳ Prochain check dans 1h30...")
        try:
            time.sleep(VOTE_INTERVAL)
        except KeyboardInterrupt:
            logging.info("Stop demandé par l'utilisateur.")
            sys.exit(0)
        cycle += 1
