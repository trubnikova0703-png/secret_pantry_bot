#!/usr/bin/env python3
"""🕵️‍♂‍ ОПЕРАЦИЯ 'КЛАДОВАЯ УЛИК' - Секретный бот-вишлист"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, CallbackContext, ConversationHandler
)
import database
from config import TOKEN, ADMIN_ID

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для добавления улики
TITLE, DESCRIPTION, LINK, PRICE, PHOTO = range(5)

async def start(update: Update, context: CallbackContext):
    """🕵️‍♂️ Код доступа принят"""
    user = update.effective_user
    user_id = user.id
    
    # Регистрация агента
    database.add_user(
        telegram_id=user_id,
        username=user.username,
        first_name=user.first_name,
        is_admin=(user_id == ADMIN_ID)
    )
    
    # Проверка секретного токена (если друг перешел по ссылке)
    args = context.args
    if args and len(args) > 0:
        token = args[0]
        wishlist = database.get_wishlist_by_token(token)
        
        if wishlist:
            return await show_agent_wishlist(update, context, wishlist)
    
    # Разные приветствия для главного агента и оперативников
    if user_id == ADMIN_ID:
        welcome_text = f"""
🕵️‍♂️ *ДОБРО ПОЖАЛОВАТЬ НА БАЗУ, АГЕНТ {user.first_name.upper()}!*

*Кодовое имя: ХРАНИТЕЛЬ КЛАДОВОЙ*

📋 *ВАША МИССИЯ:*
• Собирать улики-желания (подарки)
• Организовать их хранение
• Выдавать коды доступа проверенным агентам

🔧 *СИСТЕМНЫЕ КОМАНДЫ:*
`/list` — инвентаризация улик
`/add` — занести новую улику
`/share` — сгенерировать код доступа
`/help` — протокол операции

⚠️ *ВНИМАНИЕ:* 
Кладовой улик могут угрожать посторонние.
Будьте бдительны.

*Готовы начать операцию?*
"""
    else:
        welcome_text = f"""
👤 *ПРИВЕТСТВИЕ, ОПЕРАТИВНИК {user.first_name}!*

Вы получили код доступа к секретной *Кладовой Улик*.

🎯 *ВАША ЗАДАЧА:*
1. Изучить список улик (подарков)
2. Выбрать одну улику для изъятия
3. Нажать "ВЗЯТЬ В РАБОТУ"
4. Обеспечить доставку к сроку

📌 *СТАТУСЫ УЛИК:*
🟢 СВОБОДНА — можно брать
🟡 В РАБОТЕ — уже взята другим агентом

*Код доступа подтвержден. Начинаем?*
"""
    
    keyboard = [
        [InlineKeyboardButton("📁 ИНВЕНТАРИЗАЦИЯ УЛИК", callback_data="view_list")],
        [InlineKeyboardButton("📖 ПРОТОКОЛ ОПЕРАЦИИ", callback_data="help")]
    ]
    if user_id == ADMIN_ID:
        keyboard.insert(0, [InlineKeyboardButton("➕ ЗАНЕСТИ НОВУЮ УЛИКУ", callback_data="add_evidence")])
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_agent_wishlist(update: Update, context: CallbackContext, wishlist):
    """Показать кладовую агенту"""
    items = database.get_items_by_wishlist_id(wishlist['wishlist_id'])
    
    if not items:
        await update.message.reply_text(
            f"📭 *КЛАДОВАЯ АГЕНТА {wishlist['owner_name'].upper()} ПУСТА!*\n\n"
            f"Улик пока не обнаружено.\n"
            f"Агент ещё не занёс материалы.",
            parse_mode='Markdown'
        )
        return
    
    welcome_text = f"""
🕵️‍♂️ *ДОСТУП К КЛАДОВОЙ АГЕНТА {wishlist['owner_name'].upper()}*

*Кодовое имя операции: 'ПОДАРОК'*

🎯 *ВАШИ ДЕЙСТВИЯ:*
1. Изучить список улик ниже
2. Выбрать одну улику для изъятия
3. Нажать "ВЗЯТЬ В РАБОТУ"
4. Обеспечить её доставку агенту {wishlist['owner_name']}

📊 *СТАТИСТИКА:*
• Всего улик: {len(items)}
• Свободных: {sum(1 for item in items if item['status'] == 'available')}

⚠️ *ПРАВИЛА БЕЗОПАСНОСТИ:*
• Каждую улику может взять только один оперативник
• После взятия улика помечается как "В РАБОТЕ"
• Агент {wishlist['owner_name']} получит уведомление

*ПРИСТУПАЕМ К ОПЕРАЦИИ...*
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    for item in items:
        if item['status'] == 'available':
            status_emoji = "🟢"
            status_text = "*СВОБОДНА*"
        else:
            status_emoji = "🟡"
            status_text = "*В РАБОТЕ*"
        
        item_text = f"""
{status_emoji} *УЛИКА: {item['title']}*
{status_text}

"""
        if item['description']:
            item_text += f"📄 _Досье: {item['description']}_\n"
        if item['price_range']:
            item_text += f"💰 _Примерная стоимость: {item['price_range']}_\n"
        
        keyboard = []
        if item['status'] == 'available':
            keyboard.append([
                InlineKeyboardButton("🕵️‍♂️ ВЗЯТЬ В РАБОТУ", callback_data=f"reserve_{item['id']}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("⛔ УЛИКА В РАБОТЕ", callback_data="already_reserved")
            ])
        
        if item['link']:
            keyboard[-1].append(
                InlineKeyboardButton("🔗 МЕСТОНАХОЖДЕНИЕ", url=item['link'])
            )
        
        if item['photo_id']:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=item['photo_id'],
                caption=item_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                item_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    await update.message.reply_text(
        f"⚠️ *ВАЖНОЕ СООБЩЕНИЕ:*\n"
        f"После взятия улики в работу обеспечьте её доставку "
        f"агенту {wishlist['owner_name']} к установленному сроку.\n\n"
        f"*Вопросы?* Свяжитесь с агентом напрямую.",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: CallbackContext):
    """Протокол операции"""
    user_id = update.effective_user.id
    
    if user_id == ADMIN_ID:
        help_text = """
🕵️‍♂‍ *ПРОТОКОЛ ОПЕРАЦИИ 'КЛАДОВАЯ УЛИК'*

*Кодовые команды:*
`/list` — инвентаризация улик
`/add` — занести новую улику в базу
`/share` — сгенерировать код доступа
`/help` — этот протокол

*Процедура добавления улики:*
1. `/add` — начало процедуры
2. Название улики (подарка)
3. Описание (досье)
4. Ссылка (местонахождение)
5. Стоимость (примерная)
6. Фото (опционально)

*Для агентов:*
Выдайте им код доступа (ссылку).
Агенты смогут:
1. Изучить список улик
2. Взять одну улику в работу
3. Вы получите уведомление

🔒 *МЕРЫ БЕЗОПАСНОСТИ:*
• Каждая улика доступна только одному агенту
• Коды доступа меняются при необходимости
• Система ведет журнал операций
"""
    else:
        help_text = """
👤 *ИНСТРУКЦИЯ ДЛЯ ОПЕРАТИВНИКА*

Вы получили доступ к секретной Кладовой Улик.

*Порядок действий:*
1. Изучите список улик (подарков)
2. Выберите одну улику для изъятия
3. Нажмите "ВЗЯТЬ В РАБОТУ"
4. Улика помечается как занятая
5. Обеспечьте доставку к сроку

*Статусы улик:*
🟢 СВОБОДНА — можно брать в работу
🟡 В РАБОТЕ — уже взята другим оперативником

*Что знает хранитель:*
Он узнает, что улика взята в работу, 
но не узнает, какая именно (сохраняется интрига).

🎯 *Цель операции:* исключить дублирование 
и обеспечить точное выполнение миссии.
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def list_command(update: Update, context: CallbackContext):
    """Инвентаризация улик"""
    user_id = update.effective_user.id
    
    items = database.get_user_items(user_id)
    
    if not items:
        if user_id == ADMIN_ID:
            await update.message.reply_text(
                "📭 *КЛАДОВАЯ УЛИК ПУСТА!*\n\n"
                "В базе нет ни одной улики.\n"
                "Начните операцию с команды `/add`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "📭 *БАЗА ДАННЫХ ПУСТА!*\n\n"
                "В этой кладовой пока нет улик.\n"
                "Хранитель ещё не занёс материалы.",
                parse_mode='Markdown'
            )
        return
    
    total = len(items)
    available = sum(1 for item in items if item['status'] == 'available')
    reserved = total - available
    
    if user_id == ADMIN_ID:
        message_text = f"""
📊 *ИНВЕНТАРИЗАЦИЯ КЛАДОВОЙ УЛИК*

*Статистика:*
• Всего улик: {total}
• 🟢 Свободно: {available}
• 🟡 В работе: {reserved}

*Список улик:*
"""
    else:
        message_text = f"""
📊 *ДОСТУПНЫЕ МАТЕРИАЛЫ*

*Для изъятия доступно: {available} из {total}*

*Список улик:*
"""
    
    await update.message.reply_text(message_text, parse_mode='Markdown')
    
    for item in items:
        if item['status'] == 'available':
            status_emoji = "🟢"
            status_text = "*СВОБОДНА*"
        else:
            status_emoji = "🟡"
            status_text = "*В РАБОТЕ*"
        
        item_text = f"""
{status_emoji} *{item['title']}*
{status_text}

"""
        if item['description']:
            item_text += f"📄 _{item['description']}_\n"
        if item['price_range']:
            item_text += f"💰 {item['price_range']}\n"
        
        keyboard = []
        if item['status'] == 'available':
            if user_id == ADMIN_ID:
                button_text = "⏳ ОЖИДАЕТ ОПЕРАТИВНИКА"
                callback_data = "cannot_reserve_own"
            else:
                button_text = "🕵️‍♂️ ВЗЯТЬ В РАБОТУ"
                callback_data = f"reserve_{item['id']}"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        else:
            keyboard.append([InlineKeyboardButton("⛔ УЛИКА В РАБОТЕ", callback_data="already_reserved")])
        
        if item['link']:
            keyboard[-1].append(InlineKeyboardButton("🔗 МЕСТОНАХОЖДЕНИЕ", url=item['link']))
        
        if item['photo_id']:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=item['photo_id'],
                caption=item_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                item_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    if user_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("➕ ЗАНЕСТИ УЛИКУ", callback_data="add_evidence")],
            [InlineKeyboardButton("🔑 ВЫДАТЬ КОД ДОСТУПА", callback_data="get_share_link")]
        ]
        await update.message.reply_text(
            "⚙️ *УПРАВЛЕНИЕ КЛАДОВОЙ:*",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def share_command(update: Update, context: CallbackContext):
    """Генерация кода доступа"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ *ТОЛЬКО ХРАНИТЕЛЬ МОЖЕТ ГЕНЕРИРОВАТЬ КОДЫ ДОСТУПА!*",
            parse_mode='Markdown'
        )
        return
    
    token = database.get_share_token(user_id)
    
    if not token:
        await update.message.reply_text("❌ Ошибка генерации кода")
        return
    
    bot_username = context.bot.username
    share_link = f"https://t.me/{bot_username}?start={token}"
    
    share_text = f"""
🔑 *КОД ДОСТУПА К КЛАДОВОЙ УЛИК*

*Секретная ссылка:*
`{share_link}`

*Процедура передачи:*
1. Скопируйте ссылку
2. Передайте проверенному агенту
3. Агент переходит по ссылке
4. Система фиксирует доступ

🛡️ *МЕРЫ БЕЗОПАСНОСТИ:*
• Ссылка одноразовая
• Не передавайте посторонним
• При утере сгенерируйте новый код

📋 *Что видит агент:*
• Полный список улик
• Возможность взять улику в работу
• Инструкцию по процедуре
"""
    
    keyboard = [[
        InlineKeyboardButton("📤 ПЕРЕДАТЬ КОД", url=f"tg://msg?text={share_link}")
    ]]
    
    await update.message.reply_text(
        share_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_command(update: Update, context: CallbackContext):
    """Занесение новой улики"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ *ТОЛЬКО ХРАНИТЕЛЬ МОЖЕТ ЗАНОСИТЬ УЛИКИ!*",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🕵️‍♂‍ *ПРОЦЕДУРА ЗАНЕСЕНИЯ НОВОЙ УЛИКИ*\n\n"
        "*ШАГ 1/5*\n"
        "📌 *НАЗВАНИЕ УЛИКИ:*\n"
        "(Краткое описание материала)",
        parse_mode='Markdown'
    )
    return TITLE

async def receive_title(update: Update, context: CallbackContext):
    context.user_data['title'] = update.message.text
    
    await update.message.reply_text(
        "📄 *ШАГ 2/5*\n"
        "*ДОСЬЕ УЛИКИ:*\n"
        "(Подробное описание, особенности)\n"
        "(Отправьте '-' чтобы пропустить):",
        parse_mode='Markdown'
    )
    return DESCRIPTION

async def receive_description(update: Update, context: CallbackContext):
    text = update.message.text
    context.user_data['description'] = text if text != '-' else ""
    
    await update.message.reply_text(
        "🔗 *ШАГ 3/5*\n"
        "*МЕСТОНАХОЖДЕНИЕ:*\n"
        "(Ссылка на материал)\n"
        "(Отправьте '-' если нет ссылки):",
        parse_mode='Markdown'
    )
    return LINK

async def receive_link(update: Update, context: CallbackContext):
    text = update.message.text
    context.user_data['link'] = text if text != '-' else ""
    
    await update.message.reply_text(
        "💰 *ШАГ 4/5*\n"
        "*СТОИМОСТЬ:*\n"
        "(Примерный диапазон, например: '1000-1500 руб'):",
        parse_mode='Markdown'
    )
    return PRICE

async def receive_price(update: Update, context: CallbackContext):
    context.user_data['price'] = update.message.text
    
    await update.message.reply_text(
        "🖼️ *ШАГ 5/5*\n"
        "*ФОТОМАТЕРИАЛ:*\n"
        "(Прикрепите фото улики)\n"
        "(Отправьте '-' чтобы продолжить без фото):",
        parse_mode='Markdown'
    )
    return PHOTO

async def receive_photo(update: Update, context: CallbackContext):
    photo_id = None
    
    if update.message.photo and update.message.text != '-':
        photo = update.message.photo[-1]
        photo_id = photo.file_id
        photo_text = "✅ Фотоматериал прикреплен!"
    elif update.message.text == '-':
        photo_text = "⏩ Пропуск фотоматериала"
    else:
        await update.message.reply_text(
            "❌ Отправьте фото или '-'",
            parse_mode='Markdown'
        )
        return PHOTO
    
    item_id = database.add_item(
        telegram_id=update.effective_user.id,
        title=context.user_data['title'],
        description=context.user_data['description'],
        link=context.user_data['link'],
        price_range=context.user_data['price'],
        photo_id=photo_id
    )
    
    if item_id:
        success_text = f"""
✅ *УЛИКА ЗАНЕСЕНА В БАЗУ!*

📁 *{context.user_data['title']}*
зарегистрирована в системе.

{photo_text}

*Следующие действия:*
• Агенты могут изучить улику
• Можно выдать код доступа
• Улика готова к изъятию

📍 *Проверить в базе:* /list
🔑 *Выдать доступ:* /share
"""
        await update.message.reply_text(
            success_text,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ *ОШИБКА ПРОЦЕДУРЫ!*\nУлика не зарегистрирована.",
            parse_mode='Markdown'
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    """Отмена процедуры"""
    await update.message.reply_text(
        "❌ *ПРОЦЕДУРА ОТМЕНЕНА.*\n"
        "Все материалы сохранены.",
        parse_mode='Markdown'
    )
    context.user_data.clear()
    return ConversationHandler.END

async def button_handler(update: Update, context: CallbackContext):
    """Обработка действий"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data.startswith('reserve_'):
        item_id = int(data.split('_')[1])
        is_owner = user_id == ADMIN_ID
        
        if is_owner:
            await query.edit_message_text(
                text="🕵️‍♂‍ *ХРАНИТЕЛЬ КЛАДОВОЙ!*\n\n"
                     "Вы не можете взять свою же улику в работу!\n"
                     "Дождитесь оперативника.",
                parse_mode='Markdown'
            )
            return
        
        result = database.reserve_item(item_id, user_id)
        
        if result == "success":
            item = database.get_item_by_id(item_id)
            
            agent_message = f"""
✅ *УЛИКА ВЗЯТА В РАБОТУ!*

📁 *{item['title']}*
теперь закреплена за вами.

🎯 *ВАШИ ДЕЙСТВИЯ:*
1. Найдите материал по координатам
2. Обеспечьте доставку к сроку
3. Сохраняйте режим секретности

⚠️ *СТАТУС:*
• Улика помечена как 'В РАБОТЕ'
• Другие агенты её не увидят
• Хранитель получил уведомление

_Операция продолжается..._ 🕵️‍♂️
"""
            await query.edit_message_text(
                text=agent_message,
                parse_mode='Markdown'
            )
            
            try:
                owner_message = f"""
📢 *УВЕДОМЛЕНИЕ ОТ СИСТЕМЫ*

🕵️‍♂‍ *АГЕНТ ВЗЯЛ УЛИКУ В РАБОТУ!*

Один из оперативников закрепил за собой улику из вашей кладовой.

📌 *ДЕТАЛИ:*
• Улика теперь недоступна другим
• Оперативник готовит доставку
• Интрига сохраняется

🎯 *ЧТО ДЕЛАТЬ:*
• Ждите исполнения операции
• Не запрашивайте детали
• Готовьтесь к получению

_Система безопасности активирована._
"""
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=owner_message,
                    parse_mode='Markdown'
                )
            except:
                pass
            
        elif result == "already_reserved":
            await query.edit_message_text(
                text="⛔ *УЛИКА УЖЕ В РАБОТЕ!*\n\n"
                     "Другой оперативник уже взял эту улику.\n"
                     "Изучите другие материалы.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                text="❌ *СИСТЕМНАЯ ОШИБКА!*\n"
                     "Процедура прервана.",
                parse_mode='Markdown'
            )
    
    elif data == "view_list":
        await list_command(update, context)
    
    elif data == "help":
        await help_command(update, context)
    
    elif data == "add_evidence":
        if user_id == ADMIN_ID:
            await add_command(update, context)
        else:
            await query.answer("Только хранитель может заносить улики!", show_alert=True)
    
    elif data == "get_share_link":
        if user_id == ADMIN_ID:
            await share_command(update, context)
        else:
            await query.answer("Только хранитель может выдавать доступ!", show_alert=True)
    
    elif data == "cannot_reserve_own":
        await query.answer("Это ваша улика! Ждите оперативника.", show_alert=True)
    
    elif data == "already_reserved":
        await query.answer("Улика уже в работе у другого агента!", show_alert=True)

def main():
    """Запуск системы"""
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('add', add_command),
            CallbackQueryHandler(add_command, pattern='^add_evidence$')
        ],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price)],
            PHOTO: [MessageHandler(filters.TEXT | filters.PHOTO, receive_photo)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("share", share_command))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("""
    🕵️‍♂‍ СИСТЕМА 'КЛАДОВАЯ УЛИК' АКТИВИРОВАНА...
    
    🔐 Безопасность: активирована
    📁 База данных: готова
    👑 Хранитель ID: {ADMIN_ID}
    
    🚀 Система запущена!
    
    Кодовые команды:
    • /start - активация агента
    • /list - инвентаризация
    • /add - занесение улики
    • /share - код доступа
    • /help - протокол
    
    ⚠️ Для деактивации: Ctrl+C
    """.format(ADMIN_ID=ADMIN_ID))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
