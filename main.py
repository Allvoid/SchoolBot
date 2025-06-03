import os
import datetime
import random
import logging
import math

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

# Определение состояний:
# MENU (0), RUSSIAN (1), ENGLISH_SET_TIME (2), PRACTICE_MENU (3),
# DISCRIMINANT (4), ARITHMETIC (5), GEOMETRIC (6), PYTHAGORAS (7), HERON (8)
MENU, RUSSIAN, ENGLISH_SET_TIME, PRACTICE_MENU, DISCRIMINANT, ARITHMETIC, GEOMETRIC, PYTHAGORAS, HERON = range(9)
russian_dictionary = None

def get_file_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def load_russian_dictionary():
    dictionary = {}
    try:
        with open(get_file_path("Ожегов.txt"), encoding="utf-8") as f:
            content = f.read().strip().split("\n\n")
        for entry in content:
            lines = entry.strip().splitlines()
            if lines:
                key = lines[0].split(",")[0].strip().lower()
                dictionary[key] = " ".join(lines).strip()
    except Exception as e:
        logger.error(f"Ошибка загрузки словаря: {e}")
    return dictionary

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Русский", callback_data="russian")],
        [InlineKeyboardButton("Английский", callback_data="english")],
        [InlineKeyboardButton("Математика", callback_data="math")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в образовательного чат-бота!\n\nВыберите предмет:",
        reply_markup=main_menu_keyboard()
    )
    return MENU

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "russian":
        # Показываем кнопку «Назад» в разделе Русский
        await query.edit_message_text(
            "Введите слово:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="menu")]
            ])
        )
        return RUSSIAN

    elif data == "english":
        await query.edit_message_text("Введите время (ЧЧ:ММ):")
        return ENGLISH_SET_TIME

    elif data == "math":
        keyboard = [
            [InlineKeyboardButton("Теория", callback_data="math_theory")],
            [InlineKeyboardButton("Практика", callback_data="math_practice")],
            [InlineKeyboardButton("Назад", callback_data="menu")]
        ]
        await query.edit_message_text("Раздел математики:", reply_markup=InlineKeyboardMarkup(keyboard))
        return MENU

    elif data == "math_theory":
        keyboard = [
            [InlineKeyboardButton("Алгебра", callback_data="algebra")],
            [InlineKeyboardButton("Геометрия", callback_data="geometry")],
            [InlineKeyboardButton("Назад", callback_data="math")]
        ]
        await query.edit_message_text("Выберите тему:", reply_markup=InlineKeyboardMarkup(keyboard))
        return MENU

    elif data == "math_practice":
        keyboard = [
            [InlineKeyboardButton("Вычисление дискриминанта", callback_data="disc")],
            [InlineKeyboardButton("Арифметическая прогрессия", callback_data="arith")],
            [InlineKeyboardButton("Геометрическая прогрессия", callback_data="geom")],
            [InlineKeyboardButton("Теорема Пифагора", callback_data="pythagoras")],
            [InlineKeyboardButton("Теорема Герона", callback_data="heron")],
            [InlineKeyboardButton("Назад", callback_data="math")]
        ]
        await query.edit_message_text("Практика по математике:", reply_markup=InlineKeyboardMarkup(keyboard))
        return PRACTICE_MENU

    elif data == "disc":
        await query.edit_message_text(
            "Введите коэффициенты a, b, c через пробел (например: 1 5 6):\nФормула: D = b² - 4ac"
        )
        return DISCRIMINANT

    elif data == "arith":
        await query.edit_message_text(
            "Введите через пробел: первый член (a₁), разность (d) и количество членов (n).\nНапример: 2 3 5"
        )
        return ARITHMETIC

    elif data == "geom":
        await query.edit_message_text(
            "Введите через пробел: первый член (a₁), знаменатель (r) и количество членов (n).\nНапример: 2 3 5"
        )
        return GEOMETRIC

    elif data == "pythagoras":
        keyboard = [
            [InlineKeyboardButton("Найти гипотенузу", callback_data="find_hypotenuse")],
            [InlineKeyboardButton("Найти катет", callback_data="find_leg")],
            [InlineKeyboardButton("Назад", callback_data="math_practice")]
        ]
        await query.edit_message_text(
            "Что найти по теореме Пифагора?", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return PYTHAGORAS

    elif data == "find_hypotenuse":
        context.user_data["pythagoras_mode"] = "hypotenuse"
        await query.edit_message_text("Введите два катета через пробел (например: 3 4):")
        return PYTHAGORAS

    elif data == "find_leg":
        context.user_data["pythagoras_mode"] = "leg"
        await query.edit_message_text("Введите гипотенузу и известный катет через пробел (например: 5 3):")
        return PYTHAGORAS

    elif data == "heron":
        await query.edit_message_text(
            "Введите через пробел длины трёх сторон треугольника (например: 3 4 5):"
        )
        return HERON

    elif data.startswith(("algebra_", "geometry_")):
        await send_math_file(update, context)
        return MENU

    elif data == "menu":
        await query.edit_message_text("Возврат в главное меню.", reply_markup=main_menu_keyboard())
        return MENU

    else:
        await query.edit_message_text("Неверный выбор. Попробуйте снова.")
        return MENU

async def process_russian_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global russian_dictionary
    word = update.message.text.strip().lower()
    if russian_dictionary is None:
        russian_dictionary = load_russian_dictionary()
    definition = russian_dictionary.get(word)
    if definition:
        await update.message.reply_text(definition)
    else:
        await update.message.reply_text("Слово не найдено.")
    # После обработки возвращаемся в главное меню
    await update.message.reply_text("Выберите предмет:", reply_markup=main_menu_keyboard())
    return MENU

async def set_english_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_text = update.message.text.strip()
    try:
        target = datetime.datetime.strptime(time_text, "%H:%M").time()
        now = datetime.datetime.now()
        target_dt = datetime.datetime.combine(now.date(), target)
        if target_dt < now:
            target_dt += datetime.timedelta(days=1)
        delay = (target_dt - now).total_seconds()
        context.application.job_queue.run_once(send_english_words, delay, chat_id=update.effective_chat.id)
        await update.message.reply_text("Английские слова будут отправлены позже.")
    except Exception:
        await update.message.reply_text("Неверный формат времени. Используйте ЧЧ:ММ.")
        return ENGLISH_SET_TIME
    return MENU

async def send_english_words(context: ContextTypes.DEFAULT_TYPE):
    path = get_file_path("words.txt")
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        words = random.sample(lines, min(5, len(lines)))
        await context.bot.send_message(context.job.chat_id, text="Английские слова:\n" + "".join(words))
    except Exception:
        await context.bot.send_message(context.job.chat_id, text="Ошибка загрузки файла words.txt.")

async def send_math_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    subject, grade = query.data.split("_")
    filename = f"{subject}{grade}.txt"
    path = get_file_path(filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        await query.message.reply_text(text)
    else:
        await query.message.reply_text("Файл не найден.")
    await query.message.reply_text("Возвращаемся в главное меню.", reply_markup=main_menu_keyboard())

async def calculate_discriminant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        a, b, c = map(float, update.message.text.strip().split())
        D = b**2 - 4 * a * c
        response = f"Вычисляем дискриминант:\nD = {b}² - 4 * {a} * {c} = {D}"
        if D > 0:
            response += "\nДискриминант положительный: два различных корня."
        elif D == 0:
            response += "\nДискриминант равен нулю: один корень."
        else:
            response += "\nДискриминант отрицательный: вещественных корней нет."
        await update.message.reply_text(response)
    except Exception:
        await update.message.reply_text("Ошибка: введите 3 числа через пробел.")
        return DISCRIMINANT
    return await back_to_menu(update)

async def calculate_arithmetic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        a1, d, n = update.message.text.strip().split()
        a1, d = float(a1), float(d)
        n = int(n)
        terms = [a1 + i * d for i in range(n)]
        S = n / 2 * (2 * a1 + (n - 1) * d)
        response = (
            f"Арифметическая прогрессия:\n"
            f"Последовательность: {', '.join(map(str, terms))}\n"
            f"Сумма: {S}"
        )
        await update.message.reply_text(response)
    except Exception:
        await update.message.reply_text("Ошибка: введите 3 числа (a₁, d, n) через пробел.")
        return ARITHMETIC
    return await back_to_menu(update)

async def calculate_geometric(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        a1, r, n = update.message.text.strip().split()
        a1, r = float(a1), float(r)
        n = int(n)
        terms = [a1 * (r ** i) for i in range(n)]
        if r != 1:
            S = a1 * ((r ** n) - 1) / (r - 1)
        else:
            S = a1 * n
        response = (
            f"Геометрическая прогрессия:\n"
            f"Последовательность: {', '.join(map(str, terms))}\n"
            f"Сумма: {S}"
        )
        await update.message.reply_text(response)
    except Exception:
        await update.message.reply_text("Ошибка: введите 3 числа (a₁, r, n) через пробел.")
        return GEOMETRIC
    return await back_to_menu(update)

async def calculate_pythagoras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.strip().split()
        mode = context.user_data.get("pythagoras_mode")
        if mode == "hypotenuse":
            a, b = map(float, parts)
            c = math.sqrt(a ** 2 + b ** 2)
            explanation = (
                f"Вычисляем гипотенузу по теореме Пифагора:\n"
                f"c = √(a² + b²)\n"
                f"  = √({a}² + {b}²)\n"
                f"  = √({a**2} + {b**2}) = {c}"
            )
        elif mode == "leg":
            c, a = map(float, parts)
            if c <= a:
                raise ValueError("Гипотенуза должна быть больше катета.")
            b = math.sqrt(c ** 2 - a ** 2)
            explanation = (
                f"Вычисляем катет по теореме Пифагора:\n"
                f"b = √(c² - a²)\n"
                f"  = √({c}² - {a}²)\n"
                f"  = √({c**2} - {a**2}) = {b}"
            )
        else:
            raise ValueError("Режим вычисления не выбран.")
        await update.message.reply_text(explanation)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}. Введите корректные числа.")
        return PYTHAGORAS
    return await back_to_menu(update)

async def calculate_heron(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        a, b, c = map(float, update.message.text.strip().split())
        # Проверка на существование треугольника
        if a + b <= c or a + c <= b or b + c <= a:
            await update.message.reply_text("Ошибка: эти числа не могут быть сторонами одного треугольника.")
            return HERON
        s = (a + b + c) / 2
        area = math.sqrt(s * (s - a) * (s - b) * (s - c))
        explanation = (
            f"Вычисляем полупериметр:\n"
            f"s = (a + b + c) / 2 = ({a} + {b} + {c}) / 2 = {s}\n"
            f"Площадь по формуле Герона:\n"
            f"S = √(s * (s - a) * (s - b) * (s - c))\n"
            f"  = √({s} * ({s} - {a}) * ({s} - {b}) * ({s} - {c}))\n"
            f"  = {area}"
        )
        await update.message.reply_text(explanation)
    except Exception:
        await update.message.reply_text("Ошибка: введите 3 числа через пробел.")
        return HERON
    return await back_to_menu(update)

async def back_to_menu(update: Update):
    await update.message.reply_text("Возвращаемся в главное меню.", reply_markup=main_menu_keyboard())
    return MENU

def main():
    app = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [CallbackQueryHandler(button_handler)],
            RUSSIAN: [
                # 1) Пользователь вводит слово
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_russian_word),
                # 2) Пользователь может нажать «Назад» (callback_data="menu")
                CallbackQueryHandler(button_handler)
            ],
            ENGLISH_SET_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_english_time)],
            PRACTICE_MENU: [CallbackQueryHandler(button_handler)],
            DISCRIMINANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_discriminant)],
            ARITHMETIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_arithmetic)],
            GEOMETRIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_geometric)],
            PYTHAGORAS: [
                CallbackQueryHandler(button_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_pythagoras)
            ],
            HERON: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_heron)],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()