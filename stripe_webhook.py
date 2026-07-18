from datetime import datetime, timedelta

import bot_instance
import stripe
from config import CHANNEL_ID, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from database import activate_subscription, deactivate_subscription, mark_trial_used
from fastapi import APIRouter, Request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

stripe.api_key = STRIPE_SECRET_KEY


router = APIRouter()


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):

    payload = await request.body()

    sig = request.headers.get("Stripe-Signature")

    try:

        event = stripe.Webhook.construct_event(
            payload,
            sig,
            STRIPE_WEBHOOK_SECRET,
        )

    except Exception as e:

        print("Webhook error:", e)

        return {"error": str(e)}

    event_type = event["type"]

    #
    # НОВАЯ ПОКУПКА
    #
    if event_type == "checkout.session.completed":

        session = event["data"]["object"]

        telegram_user_id = int(session["client_reference_id"])

        metadata = session["metadata"]

        tariff = metadata["tariff"] if "tariff" in metadata else None

        #
        # fallback для payment
        #
        payment_intent_id = getattr(session, "payment_intent", None)

        if not tariff and payment_intent_id:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            tariff = payment_intent.metadata.get("tariff")

        if not tariff:

            tariff = "UNKNOWN"

        subscription_id = None

        #
        # RECURRING
        #
        if session["mode"] == "subscription":

            subscription = stripe.Subscription.retrieve(session["subscription"])
            expires = datetime.fromtimestamp(
                subscription["items"]["data"][0]["current_period_end"]
            )

            subscription_id = session["subscription"]

        #
        # TRIAL / ONE_TIME
        #
        else:

            expires = (datetime.now() + timedelta(minutes=5)).replace(microsecond=0)

        activate_subscription(
            telegram_user_id,
            expires.strftime("%Y-%m-%d %H:%M:%S"),
            tariff,
            subscription_id,
        )

        if tariff == "TRIAL":

            mark_trial_used(telegram_user_id)

        invite = await bot_instance.telegram_bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
        )

        await bot_instance.telegram_bot.send_message(
            chat_id=telegram_user_id,
            text=(
                "✅ Ваша подписка активирована!\n\n"
                f"Тариф: {tariff}\n\n"
                "Ссылка на канал:\n"
                f"{invite.invite_link}"
            ),
        )

        print("Activated:", telegram_user_id, tariff)

    #
    # ПРОДЛЕНИЕ RECURRING
    #
    elif event_type == "invoice.paid":

        invoice = event["data"]["object"]

        billing_reason = invoice["billing_reason"] if "billing_reason" in invoice else None

        if billing_reason != "subscription_cycle":
            return {"received": True}

        subscription = stripe.Subscription.retrieve(invoice["subscription"])

        telegram_user_id = int(subscription.metadata["telegram_user_id"])

        expires = datetime.fromtimestamp(
            subscription["items"]["data"][0]["current_period_end"]
        )

        activate_subscription(
            telegram_user_id,
            expires.strftime("%Y-%m-%d %H:%M:%S"),
            "RECURRING",
            invoice["subscription"],
        )

        await bot_instance.telegram_bot.send_message(
            telegram_user_id, "✅ Подписка продлена!"
        )

        print("Renewed:", telegram_user_id)

    #
    # ПОЛНАЯ ОТМЕНА RECURRING
    #
    elif event_type == "customer.subscription.deleted":

        subscription = event["data"]["object"]
        print(subscription)

        telegram_user_id = int(subscription.metadata["telegram_user_id"])

        try:

            await bot_instance.telegram_bot.ban_chat_member(
                CHANNEL_ID,
                telegram_user_id,
            )

            await bot_instance.telegram_bot.unban_chat_member(
                CHANNEL_ID,
                telegram_user_id,
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⭐ Купить подписку",
                            callback_data="buy_subscription",
                        )
                    ]
                ]
            )

            await bot_instance.telegram_bot.send_message(
                telegram_user_id,
                "❌ Подписка закончилась.\n\n"
                "Чтобы снова получить доступ, оформите новую.",
                reply_markup=keyboard,
            )

            deactivate_subscription(telegram_user_id)

            print("Subscription deleted:", telegram_user_id)

        except Exception as e:

            print("Delete error:", e)

    #
    # ОТКЛЮЧЕНИЕ АВТОПРОДЛЕНИЯ
    #
    elif event_type == "customer.subscription.updated":

        subscription = event["data"]["object"]

        if subscription.cancel_at_period_end:

            telegram_user_id = int(subscription.metadata["telegram_user_id"])

            expires = datetime.fromtimestamp(
                subscription["items"]["data"][0]["current_period_end"]
            )

            await bot_instance.telegram_bot.send_message(
                telegram_user_id,
                (
                    "⚠️ Автопродление отключено.\n\n"
                    "Доступ будет до:\n"
                    f"{expires.strftime('%d.%m.%Y %H:%M')}"
                ),
            )

            print("Cancel scheduled:", telegram_user_id)

    return {"received": True}
