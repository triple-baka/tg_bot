import stripe
from config import (
    CHANNEL_ID,
    DOMAIN,
    OWNER_IDS,
    STRIPE_ONE_TIME_PRICE_ID,
    STRIPE_PRICE_RECURRING_ID,
    STRIPE_SECRET_KEY,
    STRIPE_TRIAL_PRICE_ID,
    Tariff
)
from database import (
    deactivate_subscription,
    get_subscription_id,
    get_subscription_info,
    get_user_tariff,
    has_used_trial,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

stripe.api_key = STRIPE_SECRET_KEY


#
# Функция для создания платежа с помощью Stripe
#

async def create_checkout(
    user_id,
    tariff: Tariff,
):

    common_metadata = {
        "telegram_user_id": str(user_id),
        "tariff": tariff.value,
    }

#
# Пробная подписка
#

    if tariff == Tariff.TRIAL:

        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price": STRIPE_TRIAL_PRICE_ID,
                    "quantity": 1,
                }
            ],
            metadata=common_metadata,
            payment_intent_data={
                "metadata": common_metadata
            },
            success_url=f"{DOMAIN}/success",
            cancel_url=f"{DOMAIN}/cancel",
            client_reference_id=str(user_id),
        )

#
# Повторяющийся платёж
#

    elif tariff == Tariff.RECURRING:

        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[
                {
                    "price": STRIPE_PRICE_RECURRING_ID,
                    "quantity": 1,
                }
            ],
            metadata=common_metadata,
            subscription_data={
                "metadata": common_metadata
            },
            success_url=f"{DOMAIN}/success",
            cancel_url=f"{DOMAIN}/cancel",
            client_reference_id=str(user_id),
        )

    else:
        raise ValueError(
            f"Unknown tariff: {tariff}"
        )

    print(
        "Created checkout:",
        tariff.value,
        session.id,
    )

    return session.url

#
# Функция-обработчик когда юзер стартует бота
#

async def user_start(
    update,
    context,
):

    print(
        f"User started bot: "
        f"id={update.effective_user.id}, "
        f"username={update.effective_user.username}"
    )

#
# Кнопки под сообщением
#

    keyboard = [
        [
            InlineKeyboardButton(
                "💼 Личный кабинет",
                callback_data="cabinet",
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ Купить подписку",
                callback_data="buy_subscription",
            )
        ],
        [
            InlineKeyboardButton(
                "💬 Сообщение владельцу",
                callback_data="contact_owner",
            )
        ],
    ]

#
# Сообщение при старте бота
#

    await update.message.reply_text(
        "Добро пожаловать!",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


#
# Функция что обрабатывает нажатия на кнопки
#
async def user_button(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    data = query.data


#
# Отображение личного кабинета при нажатии на кнопку (если юзер подписан)
#
    if data == "cabinet":

        info = get_subscription_info(query.from_user.id)

        if not info:

            info = {"is_subscribed": False}

        if info["is_subscribed"]:

#
# Текст сообщения личного кабинета
#

            text = (
                "💼 <b>Личный кабинет</b>\n\n"
                "✅ Подписка активна\n\n"
                f"📦 Тариф: {info['tariff']}\n"
                f"📅 До: {info['until']}\n"
                f"⏳ Осталось: {info['days_left']} дн."
            )

#
# Кнопки в личном кабинете
#
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔄 Сменить тариф",
                            callback_data="cabinet_change_tariff",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "❌ Отписаться",
                            callback_data="cabinet_cancel",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "💬 Задать вопрос",
                            callback_data="contact_owner",
                        )
                    ],
                ]
            )

        else:

#
# Сообщение если пользователь не подписан
#
            text = "💼 <b>Личный кабинет</b>\n\n" "❌ У вас нет активной подписки."

#
# Кнопки если пользователь не подписан
#
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⭐ Купить подписку",
                            callback_data="buy_subscription",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "💬 Задать вопрос",
                            callback_data="contact_owner",
                        )
                    ],
                ]
            )

        await query.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

        return True

#
# Сообщение-заглушка для смены тарифа (пока не реализовано)
#
    if data == "cabinet_change_tariff":

        await query.message.reply_text("🚧 Возможность смены тарифа появится позже.")

        return True

#
# Обработка отмены подписки
#
    if data == "cabinet_cancel":

        user_id = query.from_user.id

        try:

            tariff = get_user_tariff(user_id)

#
# Отмена повторяющегося платежа
#
            if tariff == "RECURRING":

                subscription_id = get_subscription_id(user_id)

                if subscription_id:

                    stripe.Subscription.modify(
                        subscription_id,
                        cancel_at_period_end=True,
                    )

                await query.message.reply_text(
                    "✅ Автопродление отключено.\n\n"
                    "Доступ останется до конца оплаченного периода."
                )

                return True

#
# Обработка пробного тарифа/одноразового платежа
#
            else:

                await context.bot.ban_chat_member(
                    CHANNEL_ID,
                    user_id,
                )

                await context.bot.unban_chat_member(
                    CHANNEL_ID,
                    user_id,
                )

                deactivate_subscription(user_id)

#
# Сообщение-подтверждение отмены тарифа
#
                await query.message.reply_text(
                    "✅ Подписка отменена.\n\n" "Вы удалены из закрытого канала."
                )

                return True

        except Exception as e:

#
# Сообщение на случай ошибки отмены (в основном для тестировки)
#
            await query.message.reply_text(f"Ошибка отмены: {e}")

        return True

#
# Обработка нажатия на кнопку "Сообщение владельцу"
#
    if data == "contact_owner":

        context.user_data["chat_mode"] = True

#
# Сообщение после которого пользователь может написать владельцу 
#
        await query.message.reply_text("Отправьте ваше сообщение.")

        return True

#
# Обработка нажатия на кнопку "Купить подписку"
#
    if data == "buy_subscription":

#
# Кнопки для покупки подписки
#
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🎁 Пробная подписка на 15 дней",
                        callback_data="buy_trial",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔄 Ежемесячная подписка",
                        callback_data="buy_recurring",
                    )
                ],
            ]
        )

#
# Текст сообщения меню покупки подписки
#
        await query.message.reply_text(
            "Выберите вариант подписки:",
            reply_markup=keyboard,
        )

        return True

#
# Обработка покупки пробного доступа
#
    if data == "buy_trial":

        if has_used_trial(query.from_user.id):

            await query.message.reply_text("❌ Вы уже использовали пробный период.")

            return True

        url = await create_checkout(
            query.from_user.id,
            Tariff.TRIAL,
        )

#
# Подтверждение получения пробного доступа (сообщение)
#
        await query.message.reply_text(
            "Trial доступ:",

#
# Кнопка для оплаты пробной подписки
#
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🎁 Получить пробную подписку",
                            url=url,
                        )
                    ]
                ]
            ),
        )

        return True
#
# Обработка покупки повторяющимся платежом
#
    if data == "buy_recurring":

        url = await create_checkout(
            query.from_user.id,
            Tariff.RECURRING,
        )

#
# Сообщение покупки повторяющимся платежом
#
        await query.message.reply_text(
            "Регулярная подписка:",
#
# Кнопка покупки повторяющимся платежом
#
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔄 Оформить подписку",
                            url=url,
                        )
                    ]
                ]
            ),
        )

        return True

    return False

#
# Функция что обрабатывает сообщения отправленые юзером владельцу
#
async def user_message(
    update,
    context,
):
    if not context.user_data.get("chat_mode"):
        return

    user = update.effective_user
    text = update.message.text

    sent = False

    for OWNER_ID in OWNER_IDS:

        try:

#
# Сообщение от пользователя владельцу
#
            await context.bot.send_message(
                OWNER_ID,
                f"Новое сообщение\n\n"
                f"Пользователь: {user.first_name}\n"
                f"ID: {user.id}\n\n"
                f"{text}",
            )

            sent = True

        except Exception as e:

#
# Сообщение пользователю в случае ошибки
#
            print(f"Ошибка отправки владельцу {OWNER_ID}:", e)

    if sent:
#
# Сообщение пользователю в случае успешной отправки
#
        await update.message.reply_text("Сообщение отправлено.")

    else:
#
# Сообщение пользователю в случае ошибки
#
        await update.message.reply_text("❌ Не удалось отправить сообщение владельцу.")

    context.user_data["chat_mode"] = False
