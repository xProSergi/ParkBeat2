from playwright.sync_api import sync_playwright
from time import sleep
from requests import request
import json

bearer_token = None
cart_id = None

if not bearer_token or not cart_id:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        page.goto("https://www.parquewarner.com/horarios-y-precios/horarios")

        sleep(0.5)

        cookies = context.cookies()

        bearer_token = next((c for c in cookies if c["name"] == "portal"), None)['value']
        cart_id = next((c for c in cookies if c["name"] == "idCart"), None)['value']

bearer_header = f"Bearer {bearer_token}"
base_url = f"https://api.adminos.parquesreunidos.com/availability/calendar/{cart_id}/2025-11-01/2025-12-01"

# portal => TOKEN
# idCart => LINK

res = request('GET', base_url, headers={'Authorization': bearer_header})
parsed = json.loads(res.text)

print(parsed)