"""
Bot de vote automatique - Mistral Pixtral MTCaptcha Bypass
==========================================================
Logiciel de vote autonome utilisant l'IA Vision Mistral (Pixtral)
pour résoudre les captchas de Serveur-Prive.net.
"""

import asyncio
from playwright.async_api import async_playwright
import time
import logging
import sys
import requests
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

USERNAME = "alexcaill"
VOTE_INTERVAL = 5430  # 1h30 en secondes
MISTRAL_API_KEY = "P5bTDPAhdn9g8Q2QdEvCXH5VWeGViQh2"

def solve_mtcaptcha_with_mistral(b64_image):
    """Appelle directement l'API Vision de Mistral pour lire le captcha."""
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    
    # Préfixe requis pour Pixtral
    if not b64_image.startswith('data:image'):
        b64_image = f"data:image/png;base64,{b64_image}"
        
    prompt = "This is a captcha image. Read the characters (letters/numbers). Reply ONLY with the characters found. NO punctuation, NO spaces."
    
    data = {
        "model": "pixtral-12b-2409",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": b64_image}
                ]
            }
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        if 'choices' in result:
            content = result['choices'][0]['message']['content'].strip()
            # Nettoyage au cas où l'IA bavarde
            content = ''.join(e for e in content if e.isalnum())
            return content
    except Exception as e:
        logging.error(f"Erreur API Mistral : {e}")
    return None

async def vote_site_2():
    url = "https://serveur-prive.net/minecraft/serenity-craft/vote"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            logging.info(f"Navigation vers {url}")
            await page.goto(url, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # --- 1. Remplissage du Pseudo ---
            pseudo_input = await page.query_selector("input#pseudo")
            if pseudo_input:
                await pseudo_input.type(USERNAME, delay=100)
                logging.info(f"Pseudo '{USERNAME}' saisi.")
                    
            # --- 2. Interaction avec l'Iframe MTCaptcha ---
            logging.info("Recherche de l'iframe MTCaptcha...")
            iframe_element = await page.wait_for_selector('iframe[src*="service.mtcaptcha.com"]', timeout=10000)
            frame = await iframe_element.content_frame()
            
            # Attendre que l'image du captcha soit chargée
            await frame.wait_for_selector(".mtcap-image-mini", timeout=10000)
            
            # --- 3. Extraction de l'image (Base64) ---
            style = await frame.evaluate("document.querySelector('.mtcap-image-mini').style.backgroundImage")
            
            if 'url("data:image' in style or "url('data:image" in style:
                b64 = style.split("data:image/")[1].split('")')[0].split("')")[0]
                if "base64," in b64:
                    b64 = b64.split("base64,")[1]
                
                logging.info("Image Captcha extraite. Envoi à l'IA Mistral...")
                captcha_text = solve_mtcaptcha_with_mistral(b64)
                
                if captcha_text:
                    logging.info(f"L'IA a déchiffré : {captcha_text}")
                    
                    # Saisie dans le champ de l'iframe
                    input_field = await frame.query_selector("input[type='text']")
                    if input_field:
                        await input_field.type(captcha_text, delay=150)
                        logging.info("Texte saisi dans le captcha.")
                        await page.wait_for_timeout(1000)
                        
                        # --- 4. Validation finale du Vote ---
                        logging.info("Recherche du bouton de vote...")
                        # On essaie plusieurs sélecteurs courants pour être sûr
                        vote_selectors = ["button#btn-vote", "button.btn-vote", "input[type='submit']", "button:has-text('vote')"]
                        
                        btn_clicked = False
                        for selector in vote_selectors:
                            vote_btn = await page.query_selector(selector)
                            if vote_btn and await vote_btn.is_visible():
                                logging.info(f"Clic sur le bouton trouvé via '{selector}'")
                                await vote_btn.click()
                                btn_clicked = True
                                break
                        
                        if not btn_clicked:
                            logging.warning("Bouton de vote non trouvé avec les sélecteurs standards.")
                        
                        # Attendre de voir si on a un message de succès
                        await page.wait_for_timeout(5000)
                        
                        content = (await page.content()).lower()
                        if "merci" in content or "confirmé" in content or "succès" in content:
                            logging.info("✅ Vote validé avec succès !")
                        else:
                            logging.info("Cycle terminé. Le bouton a été cliqué mais la confirmation n'est pas évidente.")
                else:
                    logging.error("L'IA n'a pas renvoyé de réponse valide.")
            else:
                logging.error("Impossible de trouver l'image Base64 dans le widget.")

        except Exception as e:
            logging.error(f"Erreur durant l'exécution du vote : {e}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    cycle = 1
    while True:
        logging.info(f"=== Début du cycle de vote #{cycle} (Vision AI Bypass) ===")
        asyncio.run(vote_site_2())
        logging.info(f"=== Fin du cycle de vote #{cycle} ===")
        logging.info(f"⏳ Prochain vote dans 1h30 (5400s)...")
        try:
            time.sleep(VOTE_INTERVAL)
        except KeyboardInterrupt:
            logging.info("Arrêt du bot.")
            sys.exit(0)
        cycle += 1
