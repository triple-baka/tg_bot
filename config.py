# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_IDS = [int(x) for x in os.getenv('OWNER_IDS').split(',')]
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PRICE_RECURRING_ID = os.getenv('STRIPE_PRICE_RECURRING_ID')
STRIPE_ONE_TIME_PRICE_ID = os.getenv('STRIPE_ONE_TIME_PRICE_ID')
STRIPE_TRIAL_PRICE_ID = os.getenv('STRIPE_TRIAL_PRICE_ID')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
DOMAIN = os.getenv('DOMAIN')
