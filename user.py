from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

import stripe

from config import (
    OWNER_IDS,
    CHANNEL_ID,
    STRIPE_SECRET_KEY,
    STRIPE_ONE_TIME_PRICE_ID,
    STRIPE_PRICE_RECURRING_ID,
    STRIPE_TRIAL_PRICE_ID,
    DOMAIN,
)

from database import (
    get_subscription_info,
    deactivate_subscription,
    has_used_trial,
    get_subscription_id,
    get_user_tariff,
)

stripe.api_key = STRIPE_SECRET_KEY



async def create_checkout(
    user_id,
    payment_type,
):

    common_metadata = {
        "telegram_user_id": str(user_id),
    }


    if payment_type == "trial":

        common_metadata["tariff"] = "TRIAL"

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


    elif payment_type == "one_time":

        common_metadata["tariff"] = "ONE_TIME"

        session = stripe.checkout.Session.create(

            mode="payment",

            line_items=[
                {
                    "price": STRIPE_ONE_TIME_PRICE_ID,
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


    elif payment_type == "recurring":

        common_metadata["tariff"] = "RECURRING"


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
            "Unknown payment type"
        )


    print(
        "Created checkout:",
        payment_type,
        session.id
    )


    return session.url

async def user_start(
    update,
    context,
):

    print(
        f"User started bot: "
        f"id={update.effective_user.id}, "
        f"username={update.effective_user.username}"
    )


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


    await update.message.reply_text(
        "Добро пожаловать!",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )



async def user_button(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    data = query.data



    if data == "cabinet":

        info = get_subscription_info(
            query.from_user.id
        )


        if not info:

            info = {
                "is_subscribed": False
            }



        if info["is_subscribed"]:


            text = (
                "💼 <b>Личный кабинет</b>\n\n"
                "✅ Подписка активна\n\n"
                f"📦 Тариф: {info['tariff']}\n"
                f"📅 До: {info['until']}\n"
                f"⏳ Осталось: {info['days_left']} дн."
            )


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


            text = (
                "💼 <b>Личный кабинет</b>\n\n"
                "❌ У вас нет активной подписки."
            )


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




    if data == "cabinet_change_tariff":

        await query.message.reply_text(
            "🚧 Возможность смены тарифа появится позже."
        )

        return True





    if data == "cabinet_cancel":

        user_id = query.from_user.id


        try:

            tariff = get_user_tariff(
                user_id
            )


            #
            # РЕГУЛЯРНАЯ ПОДПИСКА
            #
            if tariff == "RECURRING":


                subscription_id = get_subscription_id(
                    user_id
                )


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
            # TRIAL / ONE_TIME
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


                deactivate_subscription(
                    user_id
                )


                await query.message.reply_text(
                    "✅ Подписка отменена.\n\n"
                    "Вы удалены из закрытого канала."
                )


                return True



        except Exception as e:


            await query.message.reply_text(
                f"Ошибка отмены: {e}"
            )


        return True






    if data == "contact_owner":


        context.user_data[
            "chat_mode"
        ] = True


        await query.message.reply_text(
            "Отправьте ваше сообщение."
        )


        return True






    if data == "buy_subscription":


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
                        "💳 Разовая оплата",
                        callback_data="buy_one_time",
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


        await query.message.reply_text(
            "Выберите вариант подписки:",
            reply_markup=keyboard,
        )


        return True






    if data == "buy_trial":


        if has_used_trial(
            query.from_user.id
        ):


            await query.message.reply_text(
                "❌ Вы уже использовали пробный период."
            )


            return True



        url = await create_checkout(
            query.from_user.id,
            "trial",
        )


        await query.message.reply_text(

            "Trial доступ:",

            reply_markup=InlineKeyboardMarkup(

                [
                    [
                        InlineKeyboardButton(
                            "🎁 Получить пробную подписку",
                            url=url,
                        )
                    ]
                ]
            )

        )


        return True







    if data == "buy_one_time":


        url = await create_checkout(

            query.from_user.id,

            "one_time",

        )


        await query.message.reply_text(

            "Разовая покупка:",

            reply_markup=InlineKeyboardMarkup(

                [

                    [

                        InlineKeyboardButton(

                            "💳 Оплатить",

                            url=url,

                        )

                    ]

                ]

            )

        )


        return True







    if data == "buy_recurring":


        url = await create_checkout(

            query.from_user.id,

            "recurring",

        )


        await query.message.reply_text(

            "Регулярная подписка:",

            reply_markup=InlineKeyboardMarkup(

                [

                    [

                        InlineKeyboardButton(

                            "🔄 Оформить подписку",

                            url=url,

                        )

                    ]

                ]

            )

        )


        return True



    return False







async def user_message(
    update,
    context,
):


    if not context.user_data.get(
        "chat_mode"
    ):

        return



    user = update.effective_user


    text = update.message.text



    for OWNER_ID in OWNER_IDS:


        try:


            await context.bot.send_message(

                OWNER_ID,

                f"Новое сообщение\n\n"
                f"Пользователь: {user.first_name}\n"
                f"ID: {user.id}\n\n"
                f"{text}",

            )


            await update.message.reply_text(

                "Сообщение отправлено."

            )



        except Exception as e:


            await update.message.reply_text(

                f"Error: {e}"

            )