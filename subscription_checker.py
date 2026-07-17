import asyncio

from database import (
    get_subscription_status,
    deactivate_subscription,
)

from config import CHANNEL_ID

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def check_expired_subscriptions(bot):

    while True:

        print("Checking expired subs")
        expired_users, reminder_users = get_subscription_status()

        print("Expired ", expired_users)
        print("Reminder ", reminder_users)
        for user_id in reminder_users:
            keyboard = InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton(
                        "⭐ Продлить подписку",
                        callback_data="buy_subscription",
                    )
                ]]
            )

            await bot.send_message(
                user_id,
                "⏳ До окончания подписки осталось менее 2 дней.\n\n"
                "Продлите подписку заранее.",
                reply_markup=keyboard,
            )

        for user_id in expired_users:

            try:

                await bot.ban_chat_member(
                    CHANNEL_ID,
                    user_id,
                )


                await bot.unban_chat_member(
                    CHANNEL_ID,
                    user_id,
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

                await bot.send_message(
                    user_id,
                    "❌ Ваша подписка истекла.\n\n"
                    "Чтобы снова получить доступ, приобретите новую подписку.",
                    reply_markup=keyboard,
                )


                deactivate_subscription(
                    user_id
                )


                print(
                    "Удален пользователь с истекшей подпиской:",
                    user_id,
                )


            except Exception as e:

                print(
                    "Ошибка удаления:",
                    user_id,
                    e,
                )


        await asyncio.sleep(
            60
        )
