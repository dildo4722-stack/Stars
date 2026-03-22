import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID админов (список целых чисел)
ADMIN_IDS = [473501053]  # Замени на свои ID

# ID канала для обязательной подписки
REQUIRED_CHANNEL_ID = "@mountainsdriver"  # Замени на ID своего канала

# Курсы валют (1 звезда)
STAR_PRICE_RUB = 1.43
STAR_PRICE_USD = 0.017
STAR_PRICE_TON = 0.014

# Минимальное количество звезд для покупки
MIN_STARS_PURCHASE = 50