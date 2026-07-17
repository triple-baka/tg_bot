import asyncio

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from bot import create_bot
from stripe_webhook import router


app = FastAPI()

app.include_router(router)

telegram_app = create_bot()


from database import init_db

import bot_instance

telegram_app = create_bot()

import asyncio

from subscription_checker import (
    check_expired_subscriptions
)

@app.on_event("startup")
async def startup():
    init_db()
    bot_instance.telegram_bot = telegram_app.bot

    await telegram_app.initialize()

    await telegram_app.start()

    await telegram_app.updater.start_polling()
    asyncio.create_task(
        check_expired_subscriptions(
            telegram_app.bot
        )
    )
    print("Telegram bot started")

@app.on_event("shutdown")
async def shutdown():

    await telegram_app.updater.stop()

    await telegram_app.stop()

    await telegram_app.shutdown()


@app.get("/")
async def home():

    return {
        "status": "running"
    }

@app.get("/success", response_class=HTMLResponse)
async def success():

    return """
    <html>
        <body>
            <h1>✅ Payment successful!</h1>
            <p>Your subscription is being activated.</p>
            <p>You can return to Telegram.</p>
        </body>
    </html>
    """
   

@app.get("/cancel", response_class=HTMLResponse)
async def cancel():

    return """
    <html>
        <body>
            <h1>❌ Payment cancelled</h1>
            <p>You can close this page and try again.</p>
        </body>
    </html>
    """
