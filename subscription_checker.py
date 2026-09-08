import asyncio

from database import (
    get_subscription_status,
    deactivate_subscription,
)

from config import CHANNEL_ID, Tariff

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

#
# Частота проверки истекших пользователей в секундах (для тестов 1 минута)
#
CHECK_TIME = 60

async def check_expired_subscriptions(bot):

    while True:

        print("Checking expired subs")
        expired_users, reminder_users = get_subscription_status()

        print("Expired ", expired_users)
        print("Reminder ", reminder_users)
        for user in reminder_users:
            tariff = user["tariff"]
            user_id = user["user_id"]

            if tariff == Tariff.RECURRING:
#
# Сообщение напоминалки о автопродлении подписки
#
                await bot.send_message(
                    user_id,
                    "⏳ Подписка на канал будет автоматически продена через 2 дня.\n\n"
                )
            else:

                keyboard = InlineKeyboardMarkup(
#
# Кнопка напоминалки пользователю продлить подписку
#
                    [[
                        InlineKeyboardButton(
                            "⭐ Продлить подписку",
                            callback_data="buy_subscription",
                        )
                    ]]
                )
#
# Сообщение напоминалки пользователю продлить подписку
#
                await bot.send_message(
                    user_id,
                    "⏳ Подписка на канал истечет через 2 дня.\n\n",
                    reply_markup=keyboard,
                )

        for user in expired_users:

            user_id = user['user_id']

            try:

                await bot.ban_chat_member(
                    CHANNEL_ID,
                    user_id,
                )


                await bot.unban_chat_member(
                    CHANNEL_ID,
                    user_id,
                )

#
# Кнопка напоминалки пользователю купить подписку после истечения
#
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

#
# Сообщения напоминалка пользователю о истечении подписки
#
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
            CHECK_TIME
        )
