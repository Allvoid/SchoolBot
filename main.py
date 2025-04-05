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

# Определение состояний разговора:
# MENU - главное меню,
# RUSSIAN - работа с русским языком,
# ENGLISH_SET_TIME - установка времени для английских слов,
# PRACTICE_MENU - меню практических задач по математике,
# DISCRIMINANT - состояние ожидания ввода для дискриминанта,
# ARITHMETIC - состояние ожидания ввода для арифметической прогрессии,
# GEOMETRIC - состояние ожидания ввода для геометрической прогрессии,
# THEORY_MENU - меню теоретической части математики.
MENU, RUSSIAN, ENGLISH_SET_TIME, PRACTICE_MENU, DISCRIMINANT, ARITHMETIC, GEOMETRIC, THEORY_MENU = range(8)

russian_dictionary = None

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
        return MENU
    elif data == "math_theory":
        await theory_menu_handler(update, context)
        return THEORY_MENU
    elif data == "math_practice":
        await practice_menu_handler(update, context)
        return PRACTICE_MENU
    elif data == "back_math":
        await math_handler(update, context)
        return MENU
    elif data == "disc":
        await discriminant_prompt(update, context)
        return DISCRIMINANT
    elif data == "arith":
        await arithmetic_progression_prompt(update, context)
        return ARITHMETIC
    elif data == "geom":
        await geometric_progression_prompt(update, context)
        return GEOMETRIC
    elif data == "algebra":
        await algebra_handler(update, context)
    elif data == "geometry":
        await geometry_handler(update, context)
    elif data.startswith(("algebra_", "geometry_")):
        await send_math_file(update, context)
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
    Предлагает выбрать между теорией и практикой в разделе математики.
    """
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Теория", callback_data="math_theory")],
        [InlineKeyboardButton("Практика", callback_data="math_practice")],
        [InlineKeyboardButton("Назад в главное меню", callback_data="menu")]
    ]
    await query.edit_message_text(
        text="Выберите раздел математики:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def theory_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает меню теоретической части математики с выбором разделов.
    """
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Алгебра", callback_data="algebra")],
        [InlineKeyboardButton("Геометрия", callback_data="geometry")],
        [InlineKeyboardButton("Назад к разделу математики", callback_data="math")]
    ]
    await query.edit_message_text(
        text="Выберите раздел теории математики:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def practice_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает меню практических задач по математике.
    """
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Вычисление дискриминанта", callback_data="disc")],
        [InlineKeyboardButton("Арифметическая прогрессия", callback_data="arith")],
        [InlineKeyboardButton("Геометрическая прогрессия", callback_data="geom")],
        [InlineKeyboardButton("Назад к разделу математики", callback_data="math")]
    ]
    await query.edit_message_text(
        text="Выберите практическую задачу по математике:", reply_markup=InlineKeyboardMarkup(keyboard)
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
        [InlineKeyboardButton("Назад к разделу теории", callback_data="math")]
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
        [InlineKeyboardButton("Назад к разделу теории", callback_data="math")]
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

# Функции для практических задач

async def discriminant_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запрашивает у пользователя коэффициенты a, b, c для вычисления дискриминанта.
    """
    query = update.callback_query
    await query.edit_message_text(
        "Введите коэффициенты a, b, c через пробел (например: 1 5 6):\n"
        "Формула: D = b² - 4ac"
    )
    return DISCRIMINANT

async def calculate_discriminant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Вычисляет дискриминант и подробно объясняет шаги вычисления.
    """
    text = update.message.text.strip()
    try:
        parts = text.split()
        if len(parts) != 3:
            await update.message.reply_text("Пожалуйста, введите ровно три числа, разделенные пробелами.")
            return DISCRIMINANT
        a, b, c = map(float, parts)
        D = b**2 - 4 * a * c
        explanation = (
            f"Для вычисления дискриминанта по формуле D = b² - 4ac:\n"
            f"Подставляем значения: a = {a}, b = {b}, c = {c}\n"
            f"Вычисляем b²: {b}² = {b**2}\n"
            f"Вычисляем 4ac: 4 * {a} * {c} = {4 * a * c}\n"
            f"Таким образом, D = {b**2} - {4 * a * c} = {D}\n"
        )
        if D > 0:
            explanation += "Дискриминант положительный. Уравнение имеет два различных вещественных корня."
        elif D == 0:
            explanation += "Дискриминант равен нулю. Уравнение имеет один корень (два совпадающих)."
        else:
            explanation += "Дискриминант отрицательный. Уравнение не имеет вещественных корней."
        await update.message.reply_text(explanation)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}. Проверьте правильность ввода.")
        return DISCRIMINANT

    await update.message.reply_text("Возвращаемся в главное меню.", reply_markup=main_menu_keyboard())
    return MENU

async def arithmetic_progression_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запрашивает у пользователя данные для вычисления арифметической прогрессии.
    """
    query = update.callback_query
    await query.edit_message_text(
        "Введите через пробел три числа:\n"
        "1. Первый член прогрессии (a₁)\n"
        "2. Разность прогрессии (d)\n"
        "3. Количество членов (n)\n"
        "Например: 2 3 5"
    )
    return ARITHMETIC

async def calculate_arithmetic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Вычисляет арифметическую прогрессию, выводит последовательность и сумму, с подробным объяснением.
    """
    text = update.message.text.strip()
    try:
        parts = text.split()
        if len(parts) != 3:
            await update.message.reply_text("Пожалуйста, введите ровно три числа, разделенные пробелами.")
            return ARITHMETIC
        a1, d, n = parts
        a1 = float(a1)
        d = float(d)
        n = int(n)
        terms = [a1 + i * d for i in range(n)]
        progression_str = ", ".join(str(term) for term in terms)
        sum_progression = n / 2 * (2 * a1 + (n - 1) * d)
        explanation = (
            f"Для арифметической прогрессии с первым членом {a1}, разностью {d} и количеством членов {n}:\n"
            f"Последовательность: {progression_str}\n"
            f"Сумма членов (по формуле S = n/2 * (2a₁ + (n-1)d)) = {sum_progression}"
        )
        await update.message.reply_text(explanation)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}. Проверьте правильность ввода.")
        return ARITHMETIC

    await update.message.reply_text("Возвращаемся в главное меню.", reply_markup=main_menu_keyboard())
    return MENU

async def geometric_progression_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запрашивает у пользователя данные для вычисления геометрической прогрессии.
    """
    query = update.callback_query
    await query.edit_message_text(
        "Введите через пробел три числа:\n"
        "1. Первый член прогрессии (a₁)\n"
        "2. Знаменатель прогрессии (r)\n"
        "3. Количество членов (n)\n"
        "Например: 2 3 5"
    )
    return GEOMETRIC

async def calculate_geometric(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Вычисляет геометрическую прогрессию, выводит последовательность и сумму (если знаменатель не равен 1),
    с подробным объяснением.
    """
    text = update.message.text.strip()
    try:
        parts = text.split()
        if len(parts) != 3:
            await update.message.reply_text("Пожалуйста, введите ровно три числа, разделенные пробелами.")
            return GEOMETRIC
        a1, r, n = parts
        a1 = float(a1)
        r = float(r)
        n = int(n)
        terms = [a1 * (r ** i) for i in range(n)]
        progression_str = ", ".join(str(term) for term in terms)
        explanation = (
            f"Для геометрической прогрессии с первым членом {a1}, знаменателем {r} и количеством членов {n}:\n"
            f"Последовательность: {progression_str}\n"
        )
        if r != 1:
            sum_progression = a1 * (r ** n - 1) / (r - 1)
            explanation += f"Сумма членов (по формуле S = a₁*(rⁿ - 1)/(r - 1)) = {sum_progression}"
        else:
            explanation += f"Так как знаменатель равен 1, сумма равна {a1 * n} (просто сумма повторяющихся членов)."
        await update.message.reply_text(explanation)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}. Проверьте правильность ввода.")
        return GEOMETRIC

    await update.message.reply_text("Возвращаемся в главное меню.", reply_markup=main_menu_keyboard())
    return MENU

def main():
    """
    Основная функция для запуска бота.
    """
    TOKEN = "Your Token"  # Замените на реальный токен
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [CallbackQueryHandler(button_handler)],
            RUSSIAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_russian_word)],
            ENGLISH_SET_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_english_time)],
            PRACTICE_MENU: [CallbackQueryHandler(button_handler)],
            THEORY_MENU: [CallbackQueryHandler(button_handler)],
            DISCRIMINANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_discriminant)],
            ARITHMETIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_arithmetic)],
            GEOMETRIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_geometric)],
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()