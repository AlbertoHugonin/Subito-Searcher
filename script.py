import os
import requests
import asyncio
from bs4 import BeautifulSoup
from telegram import Bot
import json
import logging

# File to store sent URLs
SENT_URLS_FILE = "sent_urls.json"

logging.basicConfig(level=logging.WARNING)

# Load configuration (TOKEN, CHAT_ID, URLs, and CHECK_INTERVAL) from environment variables
def load_config_and_urls():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    urls = os.getenv("MONITOR_URLS")
    check_interval = int(os.getenv("CHECK_INTERVAL", "60"))  # Default to 60 seconds if not set
    
    if not token or not chat_id or not urls:
        logging.error("Environment variables TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, and MONITOR_URLS must be set.")
        return None, None, [], check_interval

    # Split URLs by comma if multiple URLs are provided
    urls = urls.split(",")
    return token, chat_id, urls, check_interval

# Load sent URLs from file
def load_sent_urls():
    if os.path.exists(SENT_URLS_FILE):
        try:
            with open(SENT_URLS_FILE, "r") as file:
                data = json.load(file)
                return set(data)
        except (json.JSONDecodeError, ValueError):
            logging.warning("The sent URLs file is empty or corrupted. Starting with an empty set.")
            return set()
    return set()

# Save sent URLs to file
def save_sent_urls(sent_urls):
    with open(SENT_URLS_FILE, "w") as file:
        json.dump(list(sent_urls), file)

# Function to send messages on Telegram
async def send_telegram_message(bot, chat_id, message):
    await asyncio.sleep(6)
    await bot.send_message(chat_id=chat_id, text=message)

# Function to get new listings
def get_new_listings(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    listings = []
    for item in soup.find_all("div", class_="SmallCard-module_card__3hfzu"):
        title_tag = item.find("h2", class_="ItemTitle-module_item-title__VuKDo")
        title = title_tag.text.strip() if title_tag else "Titolo non disponibile"

        link_tag = item.find("a", class_="SmallCard-module_link__hOkzY")
        link = link_tag["href"] if link_tag else "Link non disponibile"

        price_tag = item.find("p", class_="index-module_price__N7M2x")
        price = price_tag.text.strip() if price_tag else "Prezzo non disponibile"

        listings.append({"title": title, "link": link, "price": price})

    return listings

# Loop to monitor listings
async def monitor_listings(bot, chat_id, check_interval):
    sent_urls = load_sent_urls()
    _, _, urls_to_monitor, _ = load_config_and_urls()
    
    while urls_to_monitor:
        for url in urls_to_monitor:
            new_listings = get_new_listings(url)
            for listing in new_listings:
                if listing["link"] not in sent_urls:
                    message = f"Nuova inserzione trovata:\n{listing['title']}\nPrezzo: {listing['price']}\nLink: {listing['link']}"
                    await send_telegram_message(bot, chat_id, message)
                    sent_urls.add(listing["link"])
                    save_sent_urls(sent_urls)  # Save after each new listing
        await asyncio.sleep(check_interval)  # Wait for the specified interval

# Entry point
if __name__ == "__main__":
    TOKEN, CHAT_ID, urls, CHECK_INTERVAL = load_config_and_urls()
    if TOKEN and CHAT_ID and urls:
        request = HTTPXRequest(connect_timeout=10.0, read_timeout=10.0)
        bot = Bot(token=TOKEN, request=request)
        asyncio.run(monitor_listings(bot, CHAT_ID, CHECK_INTERVAL))  # Run the main async function