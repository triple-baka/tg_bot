import traceback

from config import CHANNEL_ID
from database import (
    add_user_tag,
    deactivate_subscription,
    remove_user_tag,
    selected_conversations,
    get_all_tags,
    get_user_tags,
    get_users_by_tag,
    get_delete_on_expiration,
    toggle_delete_on_expiration,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

#
# Функция обработчик старта бота владельцем
#
async def owner_start(update, context):

#
# Кнопки панели управления
#
    keyboard = [
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
#
# Сообщение панели управления
#
    await update.message.reply_text(
        "Панель управления",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

#
# Функция-обработчик нажатия на кнопки стартового меню
#
async def owner_button(
    update,
    context,
    get_all_users,
):

    query = update.callback_query

    data = query.data

#
# Обработка нажатия на кнопку "Активные разговоры"
#
    if data == "owner_conversations":

        users = get_all_users()

        buttons = []

        for (
            user_id,
            username,
        ) in users:

#
# Меню разговоров с кнопкой для каждого пользователя
#
            buttons.append(
                [
                    InlineKeyboardButton(
#
# Кнопка каждого пользователя (username и user_id это переменные 
# в которых лежат ник польователя и айди, их лучше не трогать) 
# при необходимости лучше редактировать там где "Написать пользователю"
#
                        "Написать пользователю \n"+
                        f"{username} ({user_id})",
                        callback_data=f"open_{user_id}",
                    )
                ]
            )

#
# Кнопка если разговоров с пользователями нету
#
        if not buttons:

            buttons.append(
                [
                    InlineKeyboardButton(
                        "Нет пользователей",
                        callback_data="noop",
                    )
                ]
            )

#
# Сообщение меню разговоров с пользователями 
#
        await query.message.reply_text(
            "Активные разговоры:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        return True

    if data == "owner_add_user":

        context.user_data["manual_add_user"] = True

#
# Сообщение добавления пользователя вручную
#
        await query.message.reply_text(
            "Пришлите ID пользователя которого нужно добавить:"
        )

        return True

    if data == "owner_remove_user":

        context.user_data["manual_remove_user"] = True

#
# Сообщение удаления пользователя вручную
#
        await query.message.reply_text(
            "Пришлите ID пользователя которого нужно удалить:"
        )

        return True

    if data == "owner_broadcast":

        context.user_data["broadcast_mode"] = True

#
# Сообщение рассылки
#
        await query.message.reply_text("Напишите сообщение всем пользователям:")

        return True

    if data == "owner_tag_broadcast":

        tags = get_all_tags()

#
# Сообщение рассылки по тегу если тегов нет
#
        if not tags:
            await query.message.reply_text("❌ Тегов пока нет.")

            return True

        keyboard = []

#
# Если теги есть то для каждого тега появляется кнопка
#
        for tag in tags:
            keyboard.append(
                [
                    InlineKeyboardButton(
#
# Кнопка тега где tag - название тега
#
                        ''+
                        f"🏷 {tag}",
                        callback_data=f"broadcast_tag_{tag}",
                    )
                ]
            )

#
# Сообщение меню выбора тега
#
        await query.message.reply_text(
            "Выберите тег для рассылки:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return True

    if data.startswith("open_"):

        user_id = int(data.replace("open_", ""))

        selected_conversations[query.from_user.id] = user_id

        delete_on_expiration = get_delete_on_expiration(user_id)

#
# Текст кнопки переключения автоудаления
#
        if delete_on_expiration:
            delete_button_text = "🗑 Удалять при окончании: ВКЛ"
        else:
            delete_button_text = "🗑 Удалять при окончании: ВЫКЛ"

#
# Кнопки меню управления пользователем
#
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
                    delete_button_text,
                    callback_data=f"toggle_delete_{user_id}",
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

#
# Обновление текста кнопок после переключения автоудаления
#
    if data.startswith("toggle_delete_"):

        user_id = int(
            data.replace("toggle_delete_", "")
        )

        new_value = toggle_delete_on_expiration(user_id)

        if new_value is None:
            await query.answer(
                "Пользователь не найден.",
                show_alert=True,
            )
            return True

        delete_button_text = (
            "🗑 Удалять при окончании: ВКЛ"
            if new_value
            else
            "🗑 Удалять при окончании: ВЫКЛ"
        )

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
                    delete_button_text,
                    callback_data=f"toggle_delete_{user_id}",
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

        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await query.answer()

        return True

    if data.startswith("tag_add_"):

        user_id = int(data.replace("tag_add_", ""))

        tags = get_all_tags()

        keyboard = []
#
# Добавление тега пользователю с кнопками под каждый тег
#
        for tag in tags:
            keyboard.append(
                [
                    InlineKeyboardButton(
#
# Кнопка с названием существующего тега
#
                        f"🏷 {tag}",
                        callback_data=f"add_existing_tag|{user_id}|{tag}",
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
#
# Кнопка добавления нового тега
#
                    "➕ Создать новый тег",
                    callback_data=f"new_tag|{user_id}",
                )
            ]
        )

        await query.message.reply_text(
#
# Сообщение добавления тега
#
            "Выберите тег:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return True

    if data.startswith("tag_list_"):

        user_id = int(data.replace("tag_list_", ""))

        tags = get_user_tags(user_id)

        await query.message.reply_text(
#
# Сообщение со списком тегов у пользователя если они есть
#
            "Теги:\n" + "\n".join(tags) if tags 
#
# Сообщение если у пользователя нету тегов
#
            else "Нет тегов"
        )

        return True

#
# Меню удаления тегов пользователя
#
    if data.startswith("tag_remove_"):

        user_id = int(data.replace("tag_remove_", ""))

        tags = get_user_tags(user_id)

        if not tags:
#
# Сообщение если у пользователя нету тегов
#
            await query.message.reply_text("У пользователя нет тегов.")

            return True

        keyboard = []

        for tag in tags:
            keyboard.append(
                [
                    InlineKeyboardButton(
#
# Кнопка с названием тега для удаления под каждый тег
#
                        f"❌ {tag}",
                        callback_data=f"delete_tag|{user_id}|{tag}",
                    )
                ]
            )
#
# Сообщение меню удаления тегов
#
        await query.message.reply_text(
            "Выберите тег для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return True

    if data.startswith("add_existing_tag|"):
        parts = data.split("|")

        user_id = int(parts[1])

        tag = parts[2]

        add_user_tag(
            user_id,
            tag,
        )

#
# Сообщение-подтверждение добавления существующего тега пользователю
#
        await query.message.reply_text(f"✅ Тег{tag} добавлен.")

        return True

    if data.startswith("new_tag|"):
        user_id = int(
            data.split("|")[1]
        )

        context.user_data["create_tag_user"] = user_id

#
# Сообщение создания нового тега
#
        await query.message.reply_text(
            "Введите название нового тега:"
        )

        return True

    if data.startswith("broadcast_tag_"):

        tag = data.replace("broadcast_tag_", "")

        context.user_data["broadcast_tag"] = tag

        context.user_data["tag_broadcast_message"] = True

#
# Сообщение рассылки по тегу
#
        await query.message.reply_text(
            f"Введите сообщение для пользователей с тегом {tag}:"
        )

        return True

    if data.startswith("delete_tag|"):
        parts = data.split("|")

        user_id = int(parts[1])
        tag = parts[2]

        remove_user_tag(user_id, tag)

#
# Сообщение-подтверждение удаления тега у пользователя
#
        await query.message.reply_text(
            f"✅ Тег {tag} удалён."
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
#
# Сообщение пользователю при добавлении его вручную
#
                "Ссылка для входа:\n\n" f"{invite.invite_link}",
            )
#
# Сообщение админу при добавлении пользователя вручную
#
            await query.message.reply_text("✅ Ссылка отправлена.")

        except Exception as e:

            traceback.print_exc()
#
# Сообщение админу на случай ошибки при добавлении пользователя вручную
#
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
#
# Сообщение админу при удалении пользователя вручную
#
            await query.message.reply_text("✅ Пользователь удалён из канала.")

        except Exception as e:
#
# Сообщение админу на случай ошибки при удалении пользователя вручную
#
            await query.message.reply_text(f"Ошибка:\n{e}")

        return True

    if data == "noop":
        return True

    return False


async def owner_message(
    update,
    context,
    get_all_users,
):

    text = update.message.text

    if context.user_data.get("create_tag_user"):
        user_id = context.user_data.pop("create_tag_user")

        tag = text.lower().strip()

        add_user_tag(
            user_id,
            tag,
        )
#
# Сообщение-подтверждение добавления созданного тега пользователю
#
        await update.message.reply_text(f"✅ Новый тег #{tag} создан и добавлен.")

        return

    if context.user_data.get("manual_add_user"):

        context.user_data["manual_add_user"] = False

        try:

            user_id = int(text)

            invite = await context.bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1,
            )
#
# Сообщение пользователю со ссылкой на канал при добавлении его вручную (по айди)
#
            await context.bot.send_message(
                user_id,
                "Ссылка:\n\n" f"{invite.invite_link}",
            )

#
# Сообщение подтверждение отправки пользователю ссылки при добавлении его вручную (по айди)
#
            await update.message.reply_text("✅ Ссылка отправлена.")

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
#
# Сообщение-подтверждение удаления пользователя из канала вручную (по айди)
#
            await update.message.reply_text("✅ Пользователь удалён.")

        except Exception as e:

            await update.message.reply_text(str(e))

        return

    if context.user_data.get("tag_broadcast_message"):

        context.user_data["tag_broadcast_message"] = False

        tag = context.user_data.pop("broadcast_tag")

        users = get_users_by_tag(tag)

        count = 0

        for (user_id,) in users:

            try:

                await context.bot.send_message(
                    user_id,
#
# Сообщение пользователю от владельца (при рассылке по тегу)
#
                    f"📢 Сообщение владельца:\n\n{text}",
                )

                count += 1

            except Exception:
                pass

        await update.message.reply_text(
#
# Сообщение-подтверждение успешной рассылки по тегу
#
            f"✅ Рассылка по тегу #{tag} завершена.\nОтправлено: {count} пользователям"
        )

        return

    if context.user_data.get("broadcast_mode"):

        context.user_data["broadcast_mode"] = False

        users = get_all_users()

        count = 0

        for (user_id, _) in users:

            try:

                await context.bot.send_message(
                    user_id,
#
# Сообщение пользователю от владельца (при рассылке всем)
#
                    f"📢 Сообщение владельца:\n\n{text}",
                )

                count += 1

            except Exception:

                pass
#
# Сообщение-подтверждение успешной рассылки всем
#
        await update.message.reply_text(f"Отправлено: {count} пользователям")

        return

    selected_user = selected_conversations.get(update.effective_user.id)

    if not selected_user:
#
# Сообщение админу если он пишет сообщение боту не выбрав пользователя сначала
#
        await update.message.reply_text("Сначала выберите пользователя.")

        return

    try:

        await context.bot.send_message(
            selected_user,
#
# Сообщение пользователю от владельца (если админ пишет лично ему)
#
            f"📢 Сообщение владельца:\n\n{text}",
        )

#
# Сообщение-подтверждение отправки пользователю от владельца 
#
        await update.message.reply_text("Сообщение отправлено.")

    except Exception as e:

        await update.message.reply_text(str(e))
