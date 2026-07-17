from telegram import Update

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import (
    OWNER_IDS,
    BOT_TOKEN,
    CHANNEL_ID
)

from database import (
    init_db,
    add_user,
    get_all_users,
)

from owner import (
    owner_start,
    owner_button,
    owner_message,
)

from user import (
    user_start,
    user_button,
    user_message,
)


def is_owner(user):
    return user.id in OWNER_IDS


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    add_user(user)

    if is_owner(user):

        await owner_start(
            update,
            context,
        )

    else:

        await user_start(
            update,
            context,
        )


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    user = query.from_user

    if is_owner(user):

        await owner_button(
            update,
            context,
            get_all_users,
        )

    else:

        await user_button(
            update,
            context,
        )


async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    add_user(user)

    if is_owner(user):

        await owner_message(
            update,
            context,
            get_all_users,
        )

    else:

        await user_message(
            update,
            context,
        )


from telegram.ext import Application


def create_bot():

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler,
        )
    )

    return app
