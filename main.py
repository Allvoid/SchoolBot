import os
import datetime
import random
import difflib
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные и состояния разговора
russian_dictionary = None
MENU, RUSSIAN, ENGLISH_SET_TIME = range(3)

def get_file_path(filename):
    """
    Возвращает абсолютный путь к файлу, расположенного в той же директории, что и скрипт.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, filename)
    logger.info(f"Поиск файла: {file_path}")
    return file_path

def load_russian_dictionary():
    """
    Загружает словарь из файла 'Ожегов.txt' и возвращает его как словарь,
    где ключ – слово, а значение – определение.
    """
    dictionary = {}
    try:
        file_path = get_file_path("Ожегов.txt")
        with open(file_path, encoding="utf-8") as f:
            content = f.read().strip()
        # Разбиваем на записи по двум переносам строки
        entries = content.split("\n\n")
        for entry in entries:
            lines = entry.strip().splitlines()
            if lines:
                key = lines[0].split(",")[0].strip().lower()
                definition = " ".join(lines).strip()
                dictionary[key] = definition
        logger.info(f"Словарь успешно загружен из файла: {file_path}")
    except Exception as e:
        logger.error(f"Ошибка загрузки словаря: {e}")
    return dictionary

def main_menu_keyboard():
    """
    Создает и возвращает клавиатуру главного меню с вариантами выбора предметов.
    """
    keyboard = [
        [InlineKeyboardButton("Русский", callback_data="russian")],
        [InlineKeyboardButton("Английский", callback_data="english")],
        [InlineKeyboardButton("Математика", callback_data="math")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает команду /start, приветствуя пользователя и предлагая выбрать предмет.
    """
    welcome_text = (
        "Добро пожаловать в образовательного чат-бота!\n\n"
        "Выберите предмет, с которым хотите поработать:"
    )
    await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard())
    return MENU

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает нажатия кнопок в главном меню и перенаправляет к соответствующим обработчикам.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "russian":
        await query.edit_message_text(
            text="Введите русское слово, которое хотите найти в словаре Ожегова:"
        )
        return RUSSIAN
    elif data == "english":
        await english_handler(update, context)
        return ENGLISH_SET_TIME
    elif data == "math":
        await math_handler(update, context)
    elif data == "algebra":
        await algebra_handler(update, context)
    elif data == "geometry":
        await geometry_handler(update, context)
    elif data.startswith(("algebra_", "geometry_")):
        await send_math_file(update, context)
    elif data == "menu":
        await query.edit_message_text(
            text="Возврат в главное меню.", reply_markup=main_menu_keyboard()
        )
        return MENU
    else:
        await query.edit_message_text(text="Неверный выбор. Попробуйте снова.")
    return MENU

async def process_russian_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает введенное пользователем слово для поиска в словаре.
    """
    global russian_dictionary
    user_word = update.message.text.strip().lower()

    if russian_dictionary is None:
        russian_dictionary = load_russian_dictionary()

    if not russian_dictionary:
        await update.message.reply_text(
            "К сожалению, не удалось загрузить словарь. Попробуйте позже."
        )
        return MENU

    # Поиск ближайших совпадений с заданным порогом похожести
    matches = difflib.get_close_matches(user_word, list(russian_dictionary.keys()), n=1, cutoff=0.7)

    if matches:
        response = f"Определение для слова '{user_word}':\n\n{russian_dictionary[matches[0]]}"
        await update.message.reply_text(response)
    else:
        await update.message.reply_text(
            f"Слово '{user_word}' не найдено в словаре. Проверьте правильность ввода."
        )

    await update.message.reply_text(
        "Выберите следующий предмет для работы:", reply_markup=main_menu_keyboard()
    )
    return MENU

async def english_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор английского языка и запрашивает время для отправки слов.
    """
    query = update.callback_query
    prompt = (
        "Введите время, когда хотите получить английские слова.\n"
        "Используйте формат ЧЧ:ММ (например, 14:30):"
    )
    await query.edit_message_text(text=prompt)
    return ENGLISH_SET_TIME

async def set_english_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает введенное пользователем время и планирует отправку английских слов.
    """
    user_time = update.message.text.strip()

    try:
        target_time = datetime.datetime.strptime(user_time, "%H:%M").time()
        now = datetime.datetime.now()
        target_datetime = datetime.datetime.combine(now.date(), target_time)

        # Если указанное время уже прошло сегодня, планируем на следующий день
        if target_datetime < now:
            target_datetime += datetime.timedelta(days=1)

        delay = (target_datetime - now).total_seconds()

        await update.message.reply_text(
            f"Хорошо! Английские слова будут отправлены в {user_time}. Будьте готовы!"
        )

        # Планирование задачи с использованием встроенной очереди заданий
        context.application.job_queue.run_once(
            send_english_words, delay, chat_id=update.effective_chat.id
        )

    except ValueError:
        await update.message.reply_text(
            "Неверный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ, например, 09:45."
        )
        return ENGLISH_SET_TIME

    await update.message.reply_text(
        "Возвращаемся в главное меню.", reply_markup=main_menu_keyboard()
    )
    return MENU

async def send_english_words(context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляет пользователю случайный набор английских слов из файла words.txt.
    """
    job = context.job
    chat_id = job.chat_id

    file_path = get_file_path("words.txt")
    if not os.path.exists(file_path):
        await context.bot.send_message(
            chat_id, text="Файл words.txt не найден. Свяжитесь с администратором."
        )
        logger.warning(f"Файл не найден: {file_path}")
        return

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            await context.bot.send_message(
                chat_id, text="Файл words.txt пуст. Добавьте слова для отправки."
            )
            logger.warning("Файл words.txt пуст.")
            return

        words = random.sample(lines, min(5, len(lines)))
        text = "Вот несколько английских слов для практики:\n\n" + "".join(words)
        await context.bot.send_message(chat_id, text=text)
        logger.info(f"Слова успешно отправлены из файла: {file_path}")
    except Exception as e:
        error_text = f"Ошибка при чтении файла words.txt: {e}"
        await context.bot.send_message(chat_id, text=error_text)
        logger.error(error_text)

async def math_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор раздела математики и предлагает выбрать между алгеброй и геометрией.
    """
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Алгебра", callback_data="algebra")],
        [InlineKeyboardButton("Геометрия", callback_data="geometry")],
        [InlineKeyboardButton("Назад в главное меню", callback_data="menu")]
    ]
    await query.edit_message_text(
        text="Выберите раздел математики:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def algebra_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Предоставляет выбор класса для получения материалов по алгебре.
    """
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton(f"{i} класс", callback_data=f"algebra_{i}")]
        for i in range(5, 10)
    ]
    keyboard.append(
        [InlineKeyboardButton("Назад к разделу математики", callback_data="math")]
    )
    await query.edit_message_text(
        text="Выберите класс для получения материалов по алгебре:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def geometry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Предоставляет выбор класса для получения материалов по геометрии.
    """
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton(f"{i} класс", callback_data=f"geometry_{i}")]
        for i in range(7, 10)
    ]
    keyboard.append(
        [InlineKeyboardButton("Назад к разделу математики", callback_data="math")]
    )
    await query.edit_message_text(
        text="Выберите класс для получения материалов по геометрии:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_math_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляет пользователю учебные материалы по выбранной теме и классу.
    """
    query = update.callback_query
    subject, grade = query.data.split('_')
    grade = int(grade)

    if subject == "algebra":
        # Если класс меньше или равен 6 – материалы по общей математике, иначе материалы по алгебре
        filename = f"математика{grade}.txt" if grade <= 6 else f"алгебра{grade}.txt"
    elif subject == "geometry":
        filename = f"геометрия{grade}.txt"
    else:
        await query.message.reply_text("Ошибка: неизвестный предмет.")
        return

    file_path = get_file_path(filename)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                text = file.read()
            logger.info(f"Файл успешно прочитан: {file_path}")
        except Exception as e:
            text = f"Ошибка при чтении файла {filename}: {e}"
            logger.error(text)
    else:
        text = "Учебные материалы для выбранного класса не найдены. Обратитесь к администратору."
        logger.warning(f"Файл не найден: {file_path}")

    await query.message.reply_text(text)
    await query.message.reply_text(
        "Возвращаемся в главное меню.", reply_markup=main_menu_keyboard()
    )

def main():
    """
    Основная функция для запуска бота.
    """
    TOKEN = "Your token"  # Замените на реальный токен
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [CallbackQueryHandler(button_handler)],
            RUSSIAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_russian_word)],
            ENGLISH_SET_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_english_time)]
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()