from telebot import types
from database import Database, Analysis
from datetime import datetime
import re
import os

bot = os.bot
db = Database()
db.create_tables_users()
db.create_table_track()  # Создаем таблицу для трасс
a = Analysis()
user_data = {}
track_data = {}


# Основные клавиатуры
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    keyboard.add(
        types.KeyboardButton('Вход'),
        types.KeyboardButton('Регистрация'),
        types.KeyboardButton('О проекте')
    )
    return keyboard


def get_track_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("5", callback_data='grade_5'),
        types.InlineKeyboardButton("6", callback_data='grade_6'),
        types.InlineKeyboardButton("7", callback_data='grade_7'),
        types.InlineKeyboardButton("8", callback_data='grade_8'),
        types.InlineKeyboardButton("Назад", callback_data='back_to_start')
    )
    return keyboard


def get_subgrade_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("A", callback_data='subgrade_A'),
        types.InlineKeyboardButton("B", callback_data='subgrade_B'),
        types.InlineKeyboardButton("C", callback_data='subgrade_C'),
        types.InlineKeyboardButton("Назад", callback_data='back_to_start')
    )
    return keyboard


# Обработчики команд
@bot.message_handler(commands=['start'])
def handle_start(user_id_or_message):
    if isinstance(user_id_or_message, int):
        user_id = user_id_or_message
    else:
        user_id = user_id_or_message.from_user.id

    bot.send_message(user_id, 'Войдите или зарегистрируйтесь',
                     reply_markup=get_main_keyboard())
    process_main_menu(user_id_or_message)


@bot.message_handler(func=lambda message: True)
def process_main_menu(message):
    if message.text == 'Вход':
        start_handler(message)
    elif message.text == 'Регистрация':
        register_handler(message)
    elif message.text == 'О проекте':
        bot.send_message(message.from_user.id,
                         'Этот бот сохраняет информацию о ваших пролазах и анализирует её\n'
                         'Чтобы получить оценку своего уровня лазания\n'
                         'и статистику за день, месяц или год, нажмите /info')
    else:
        bot.reply_to(message, 'Пожалуйста, используйте кнопки меню')


def start_handler(message):
    try:
        if db.user_exists(message.from_user.id): # Проверяем наличие пользователя
            username = db.get_username(message.from_user.id) or "пользователь"
            bot.send_message(
                message.from_user.id,
                f"Добро пожаловать, {username}!"
            )
            welcome(message)
        else:
            bot.send_message(
                message.from_user.id,
                "Вы не зарегистрированы\nДля регистрации введите /register"
            )

    except Exception as e:
        print(f"Ошибка в start_handler: {e}")
        bot.send_message(message.from_user.id, "Произошла ошибка. Попробуйте позже.")


# Регистрация пользователя
@bot.message_handler(commands=['register'])
def register_handler(message):
    user_data[message.from_user.id] = {'name': '', 'surname': '', 'phone': '', 'city': ''}
    ask_name(message)


def ask_name(user_id_or_message):
    if isinstance(user_id_or_message, int):
        user_id = user_id_or_message
    else:
        user_id = user_id_or_message.from_user.id

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Назад", callback_data='back_to_start'))
    msg = bot.send_message(user_id, "Как вас зовут?", reply_markup=keyboard)
    bot.register_next_step_handler(msg, process_name)


def process_name(message):
    try:
        if message.text.lower() == 'назад':
            return handle_start(message)

        user_data[message.from_user.id]['name'] = message.text.strip()
        ask_surname(message)

    except Exception as e:
        bot.reply_to(message, f"Ошибка при вводе имени: {e}")
        ask_name(message)



def ask_surname(user_id_or_message):
    if isinstance(user_id_or_message, int):
        user_id = user_id_or_message
    else:
        user_id = user_id_or_message.from_user.id
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Назад", callback_data='back'))
    message = bot.send_message(user_id, "Какая у вас фамилия?", reply_markup=keyboard)
    bot.register_next_step_handler(message, process_surname)


def process_surname(message):
    try:
        if message.text.lower() == 'назад':
            return ask_name(message)

        user_data[message.from_user.id]['surname'] = message.text.strip()
        ask_phone(message)

    except Exception as e:
        bot.reply_to(message, f"Ошибка при вводе имени: {e}")
        ask_name(message)


def ask_phone(user_id_or_message):
    if isinstance(user_id_or_message, int):
        user_id = user_id_or_message
    else:
        user_id = user_id_or_message.from_user.id
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Назад", callback_data='back_to_surname'))
    msg = bot.send_message(
        user_id,
        'Введите ваш номер телефона в формате:\n+7XXX... или 8XXX... (10 цифр после кода страны)\nПример: +79123456789',
        reply_markup=keyboard
    )
    bot.register_next_step_handler(msg, process_phone)


def process_phone(message):
    try:
        if message.text.lower() == 'назад':
            return ask_surname(message)

        # Очищаем и нормализуем номер
        cleaned = re.sub(r'[^\d+]', '', message.text)
        if cleaned.startswith('8'):
            cleaned = '+7' + cleaned[1:]
        elif cleaned.startswith('7'):
            cleaned = '+' + cleaned

        if not re.fullmatch(r'^\+7\d{10}$', cleaned):
            raise ValueError("Неверный формат номера")

        user_data[message.from_user.id]['phone'] = cleaned
        ask_city(message)

    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")
        ask_phone(message)


def ask_city(user_id_or_message):
    if isinstance(user_id_or_message, int):
        user_id = user_id_or_message
    else:
        user_id = user_id_or_message.from_user.id
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Назад", callback_data='back_to_phone'))
    msg = bot.send_message(user_id, 'Из какого вы города?', reply_markup=keyboard)
    bot.register_next_step_handler(msg, process_city)


def process_city(message):
    try:
        if message.text.lower() == 'назад':
            return ask_phone(message)

        user_data[message.from_user.id]['city'] = message.text.strip()
        confirm_data(message)

    except Exception as e:
        bot.reply_to(message, f"Ошибка при вводе города: {e}")
        ask_city(message)


def confirm_data(user_id_or_message):
    if isinstance(user_id_or_message, int):
        user_id = user_id_or_message
    else:
        user_id = user_id_or_message.from_user.id

    data = user_data[user_id]
    text = (
        f"Проверьте ваши данные:\n\n"
        f"Имя: {data['name']}\n"
        f"Фамилия: {data['surname']}\n"
        f"Телефон: {data['phone']}\n"
        f"Город: {data['city']}\n\n"
        f"Всё верно?"
    )

    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("Да", callback_data='confirm_yes'),
        types.InlineKeyboardButton("Нет", callback_data='confirm_no')
    )

    bot.send_message(user_id, text, reply_markup=keyboard)


#Сохранение данных пользователя
def save_user_data(user_id_or_message):
    if isinstance(user_id_or_message, int):
        user_id = user_id_or_message
    else:
        user_id = user_id_or_message.chat.id

    try:
        data = user_data[user_id]
        db.user_update(
            user_id,
            data['name'],
            data['surname'],
            data['city'],
            data['phone']
        )
        bot.send_message(user_id, "Регистрация прошла успешно!")
        welcome(user_id)
    except Exception as e:
        print(e)
        bot.send_message(user_id, f"Ошибка при сохранении данных: {e}")

def welcome(user_id_or_message):
    if isinstance(user_id_or_message, int):
        user_id = user_id_or_message
    else:
        user_id = user_id_or_message.from_user.id

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Записать трассу", callback_data='save_track'),
                 types.InlineKeyboardButton("Анализ лазания", callback_data='analysis_track'))
    username = db.get_username(user_id) or "пользователь"
    bot.send_message(user_id,f"{username}, желаете зафиксировать результат?", reply_markup=keyboard)

# Работа с трассами
@bot.callback_query_handler(func=lambda call: call.data == 'save_track')
def start_track_recording(call):
    try:
        # Инициализируем данные пользователя
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        track_data[user_id] = {
            'date': datetime.now().date(),
            'category_1': None,
            'category_2': None,
        }

        ask_grade(user_id)

    except Exception as e:
        error_msg = f"Ошибка в start_track_recording: {str(e)}"
        print(error_msg)
        bot.send_message(call.from_user.id, "Ошибка при начале записи трассы")

def ask_grade(user_id):
    bot.send_message(user_id, "Хотите зафиксировать результат пролаза?\nВыберите категорию трассы",
                     reply_markup=get_track_keyboard())


@bot.callback_query_handler(func=lambda call: call.data == 'analysis_track')
def analysis(call):
    try:
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        data = list(a.track(user_id))
        bot.send_message(user_id, f'Самая популярная категория за последниe 30 дней: {data[0]}\nЗа последние 90 дней: {data[2]}\n'
                                  f'Самая популярная категория за последний месяц: {data[1]}\nЗа последние 90 дней: {data[3]}')
        welcome(call.from_user.id)
    except Exception as e:
        bot.send_message(call.from_user.id, f"Ошибка в  analysis: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('grade_'))
def process_grade(call):
    try:
        # Обязательно отвечаем на callback
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        # Проверяем, инициализированы ли данные пользователя
        if call.from_user.id not in track_data:
            bot.send_message(
                user_id,
                "Ошибка: данные сессии не найдены. Начните запись трассы заново."
            )
            return handle_start(call.message)

        # Проверяем формат callback_data
        if '_' not in call.data:
            raise ValueError("Некорректный формат callback_data")

        # Извлекаем категорию
        grade = call.data.split('_')[1]

        # Проверяем, что категория - цифра
        if not grade.isdigit():
            raise ValueError("Категория должна быть числом")

        # Сохраняем категорию
        track_data[call.from_user.id]['category_1'] = int(grade)

        # Запрашиваем подкатегорию
        ask_subgrade(call.from_user.id)

    except ValueError as e:
        error_msg = f"Ошибка значения: {str(e)}"
        print(error_msg)
        bot.send_message(
            call.from_user.id,
            "Ошибка при обработке категории. Пожалуйста, выберите снова.",
            reply_markup=get_track_keyboard()
        )
    except Exception as e:
        error_msg = f"Неожиданная ошибка в process_grade: {str(e)}"
        print(error_msg)
        bot.send_message(
            call.from_user.id,
            "Произошла непредвиденная ошибка. Попробуйте снова."
        )
        return handle_start(call.message)


def ask_subgrade(user_id):
    bot.send_message(user_id, "Выберите подкатегорию:",
                     reply_markup=get_subgrade_keyboard())


@bot.callback_query_handler(func=lambda call: call.data.startswith('subgrade_'))
#startswith проверкаБ что callback начинается с 'subgrade'
def process_subgrade(call):
    try:
        bot.answer_callback_query(call.id)
        subgrade = call.data.split('_')[1]
        track_data[call.from_user.id]['category_2'] = subgrade
        confirm_track_data(call.from_user.id)
    except Exception as e:
        bot.reply_to(call.from_user.id, f"Произошла ошибка в process_subgrade: {e}")


def confirm_track_data(user_id):
    try:
        data = track_data[user_id]
        print(user_id)
        text = (
            f"Проверьте данные о трассе:\n\n"
            f"Дата: {data['date']}\n"
            f"Категория: {data['category_1']}{data['category_2']}\n\n"
            f"Всё верно?"
        )

        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton("Да", callback_data='confirm_track_yes'),
            types.InlineKeyboardButton("Нет", callback_data='confirm_track_no')
        )
        bot.send_message(user_id, text, reply_markup=keyboard)
    except Exception as e:
        bot.send_message(user_id, f"Ошибка в confirm_track_data: {e}")


@bot.callback_query_handler(func=lambda call: call.data == 'confirm_track_yes')
def save_track_data(call):
    try:
        data = track_data[call.from_user.id]
        db.save_track(call.from_user.id, data['date'], data['category_1'], data['category_2'])
        #db.conn.commit()
        bot.send_message(call.from_user.id, "Трасса успешно сохранена!")
        welcome(call.from_user.id) #
    except Exception as e:
        bot.send_message(call.from_user.id, f"Ошибка при сохранении: {e}")


@bot.callback_query_handler(func=lambda call: call.data == 'confirm_track_no')
def restart_track_recording(call):
    bot.answer_callback_query(call.id)
    start_track_recording(call)

#обработчики callback запросов
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        bot.clear_step_handler_by_chat_id(user_id)

        if call.data == 'back_to_start':
            welcome(user_id)

        elif call.data == 'back_to_name':
            ask_name(user_id)

        elif call.data == 'back_to_surname':
            ask_surname(user_id)

        elif call.data == 'back_to_phone':
            ask_phone(user_id)

        elif call.data == 'save_track':
            start_track_recording(call)  # Эта функция уже обрабатывает сохранение

        elif call.data == 'confirm_yes':
            if call.message:
                save_user_data(call.message)
            else:
                bot.send_message(user_id, "Не удалось подтвердить данные. Попробуйте снова.")

        elif call.data == 'confirm_no':
            register_handler(user_id)

        else:
            bot.send_message(user_id, "Неизвестная команда. Пожалуйста, попробуйте снова.")
            handle_start(user_id)

    except Exception as e:
        error_msg = f"Произошла ошибка: {str(e)}"
        print(error_msg)
        bot.send_message(call.from_user.id, "⚠️ Произошла ошибка при обработке запроса. Попробуйте позже.")

#Отбойник для текстовых сообщений
@bot.message_handler(func=lambda message: True)
def text_handler(message):
#Обработчик текстовых сообщений
    try:
        if message:
            handle_start(message)
    except Exception as e:
        print(f"Ошибка в text_handler: {e}")
    print(f"DEBUG: Получено сообщение от {message.from_user.id}, {message.text}, {user_data}")  # Логируем
if __name__ == '__main__':
    print("Бот запускается...")
    bot.polling(none_stop=True)