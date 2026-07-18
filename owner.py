import traceback

from config import CHANNEL_ID
from database import (
    add_user_tag,
    add_tag,
    remove_user_tag,
    get_user_tags,
    get_users_by_tag,
    get_tag,
    get_all_tags,
    delete_tag,
    deactivate_subscription,
    selected_conversations,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def owner_start(update, context):

    keyboard = [
        [
            InlineKeyboardButton(
                "🏷 Управление тегами",
                callback_data="owner_tags",
            )
        ],
        [
            InlineKeyboardButton(
                "📨 Активные разговоры",
                callback_data="owner_conversations",
            )
        ],
        [
            InlineKeyboardButton(
                "📢 Сообщение всем пользователям",
                callback_data="owner_broadcast",
            )
        ],
        [
            InlineKeyboardButton(
                "📢 Рассылка по тегу",
                callback_data="owner_tag_broadcast",
            )
        ],
        [
            InlineKeyboardButton(
                "➕ Добавить пользователя в группу",
                callback_data="owner_add_user",
            )
        ],
        [
            InlineKeyboardButton(
                "➖ Убрать пользователя из группы",
                callback_data="owner_remove_user",
            )
        ],
    ]

    await update.message.reply_text(
        "Панель управления",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def owner_button(
    update,
    context,
    get_all_users,
):

    query = update.callback_query

    data = query.data

    if data == "owner_conversations":

        users = get_all_users()

        buttons = []

        for (
            user_id,
            username,
        ) in users:

            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{username} ({user_id})",
                        callback_data=f"open_{user_id}",
                    )
                ]
            )

        if not buttons:

            buttons.append(
                [
                    InlineKeyboardButton(
                        "Нет пользователей",
                        callback_data="noop",
                    )
                ]
            )

        await query.message.reply_text(
            "Активные разговоры:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        return True

    if data == "owner_add_user":

        context.user_data["manual_add_user"] = True

        await query.message.reply_text(
            "Пришлите ID пользователя которого нужно добавить:"
        )

        return True

    if data == "owner_remove_user":

        context.user_data["manual_remove_user"] = True

        await query.message.reply_text(
            "Пришлите ID пользователя которого нужно удалить:"
        )

        return True

    if data == "owner_broadcast":

        context.user_data["broadcast_mode"] = True

        await query.message.reply_text("Напишите сообщение всем пользователям:")

        return True

    if data == "owner_tag_broadcast":

        tags = get_all_tags()

        if not tags:
            await query.message.reply_text("❌ Тегов пока нет.")

            return True

        keyboard = []

        for tag_id, name in tags:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🏷 {name}",
                        callback_data=f"broadcast_tag_{tag_id}",
                    )
                ]
            )

        await query.message.reply_text(
            "Выберите тег для рассылки:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return True

    if data.startswith("open_"):

        user_id = int(data.replace("open_", ""))

        selected_conversations[query.from_user.id] = user_id

        keyboard = [
            [
                InlineKeyboardButton(
                    "📋 Теги",
                    callback_data=f"tag_list_{user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "🏷 Добавить тег",
                    callback_data=f"tag_add_{user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Удалить тег",
                    callback_data=f"tag_remove_{user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "➕ Добавить в группу",
                    callback_data=f"add_{user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "➖ Удалить из группы",
                    callback_data=f"remove_{user_id}",
                )
            ],
        ]

        await query.message.reply_text(
            f"Пользователь: {user_id}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return True

    if data.startswith("add_"):

        user_id = int(data.replace("add_", ""))

        try:

            invite = await context.bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1,
            )

            await context.bot.send_message(
                user_id,
                "Ссылка для входа:\n\n" f"{invite.invite_link}",
            )

            await query.message.reply_text("✅ Ссылка отправлена.")

        except Exception as e:

            traceback.print_exc()

            await query.message.reply_text(f"Ошибка:\n{e}")

        return True

    if data.startswith("remove_"):

        user_id = int(data.replace("remove_", ""))

        try:

            await context.bot.ban_chat_member(
                CHANNEL_ID,
                user_id,
            )

            await context.bot.unban_chat_member(
                CHANNEL_ID,
                user_id,
            )

            deactivate_subscription(user_id)

            await query.message.reply_text("✅ Пользователь удалён из канала.")

        except Exception as e:

            await query.message.reply_text(f"Ошибка:\n{e}")

        return True

    if data.startswith("tag_add_"):

        user_id = int(data.replace("tag_add_", ""))

        tags = get_all_tags()

        keyboard = []

        for tag_id, name in tags:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🏷 {name}",
                        callback_data=f"add_existing_tag|{user_id}|{tag_id}",
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "➕ Создать новый тег",
                    callback_data=f"new_tag|{user_id}",
                )
            ]
        )

        await query.message.reply_text(
            "Выберите тег:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return True

    if data.startswith("tag_list_"):

        user_id = int(data.replace("tag_list_", ""))

        tags = get_user_tags(user_id)

        await query.message.reply_text(
            "Теги:\n" + "\n".join(
                name for _, name in tags
            ) if tags else "Нет тегов"
        )

        return True

    if data.startswith("tag_remove_"):

        user_id = int(data.replace("tag_remove_", ""))

        tags = get_user_tags(user_id)

        if not tags:
            await query.message.reply_text("У пользователя нет тегов.")

            return True

        keyboard = []

        for tag_id, name in tags:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"❌ {name}",
                        callback_data=f"delete_tag_{user_id}_{tag_id}",
                    )
                ]
            )

        await query.message.reply_text(
            "Выберите тег для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return True

    if data.startswith("add_existing_tag|"):
        parts = data.split("|")

        user_id = int(parts[1])

        tag_id = int(parts[2])

        add_user_tag(
            user_id,
            tag_id,
        )

        tag = get_tag(tag_id)

        await query.message.reply_text(
            f"✅ Тег #{tag['name']} добавлен."
        )

        return True

    if data.startswith("broadcast_tag_"):

        tag = data.replace("broadcast_tag_", "")

        context.user_data["broadcast_tag"] = tag

        context.user_data["tag_broadcast_message"] = True

        await query.message.reply_text(
            f"Введите сообщение для пользователей с тегом #{tag}:"
        )

        return True

    if data.startswith("manage_tag_"):

        tag_id = int(data.split("_")[-1])

        tag = get_tag(tag_id)

        keyboard = [
            [
                InlineKeyboardButton(
                    "👥 Пользователи",
                    callback_data=f"tag_users_{tag_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "➕ Добавить пользователя",
                    callback_data=f"tag_add_user_{tag_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "➖ Убрать пользователя",
                    callback_data=f"tag_remove_user_{tag_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Удалить тег",
                    callback_data=f"delete_global_tag_{tag_id}",
                )
            ],
        ]

        await query.message.reply_text(
            f"🏷 Тег: {tag['name']}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return True

    if data.startswith("delete_global_tag_"):

        tag_id = int(data.split("_")[-1])

        delete_tag(tag_id)

        await query.message.reply_text(
            "✅ Тег удалён."
        )

        return True

    if data.startswith("delete_tag_"):
        data_parts = data.replace(
            "delete_tag_",
            "",
        )

        user_id, tag_id = data_parts.split("_", 1)

        tag = get_tag(int(tag_id))

        remove_user_tag(
            int(user_id),
            int(tag_id),
        )

        await query.message.reply_text(
            f"✅ Тег <b>{tag['name']}</b> удалён.",
            parse_mode="HTML",
        )

        return True

    if data == "create_tag":
        context.user_data["create_tag"] = True

        await query.message.reply_text(
            "Введите название нового тега:"
        )

        return True

    if data == "owner_tags":

        tags = get_all_tags()

        keyboard = []

        for tag_id, name in tags:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🏷 {name}",
                        callback_data=f"manage_tag_{tag_id}",
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "➕ Добавить тег",
                    callback_data="create_tag",
                )
            ]
        )

        await query.message.reply_text(
            "🏷 Управление тегами:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return True

    return False


async def owner_message(
    update,
    context,
    get_all_users,
):

    text = update.message.text

    if context.user_data.get("create_tag"):

        context.user_data.pop("create_tag")

        add_tag(
            text.strip().lower()
        )

        await update.message.reply_text(
            "✅ Тег создан."
        )

        return


    if context.user_data.get("manual_add_user"):

        context.user_data["manual_add_user"] = False

        try:

            user_id = int(text)

            invite = await context.bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1,
            )

            await context.bot.send_message(
                user_id,
                "Ссылка:\n\n" f"{invite.invite_link}",
            )

            await update.message.reply_text("✅ Отправлено.")

        except Exception as e:

            await update.message.reply_text(str(e))

        return

    if context.user_data.get("manual_remove_user"):

        context.user_data["manual_remove_user"] = False

        try:

            user_id = int(text)

            await context.bot.ban_chat_member(
                CHANNEL_ID,
                user_id,
            )

            await context.bot.unban_chat_member(
                CHANNEL_ID,
                user_id,
            )

            deactivate_subscription(user_id)

            await update.message.reply_text("✅ Пользователь удалён.")

        except Exception as e:

            await update.message.reply_text(str(e))

        return

    if context.user_data.get("broadcast_mode"):

        context.user_data["broadcast_mode"] = False

        users = get_all_users()

        count = 0

        for (user_id, _) in users:

            try:

                await context.bot.send_message(
                    user_id,
                    f"📢 Сообщение владельца:\n\n{text}",
                )

                count += 1

            except Exception:

                pass

        await update.message.reply_text(f"Отправлено: {count}")

        return

    selected_user = selected_conversations.get(update.effective_user.id)

    if not selected_user:

        await update.message.reply_text("Сначала выберите пользователя.")

        return

    try:

        await context.bot.send_message(
            selected_user,
            f"📢 Сообщение владельца:\n\n{text}",
        )

        await update.message.reply_text("Сообщение отправлено.")

    except Exception as e:

        await update.message.reply_text(str(e))
