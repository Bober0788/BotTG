import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
import random
import threading
import time
import sqlite3
from flask import Flask



# Токен бота
API_TOKEN = '7716814998:AAHMsrFHr_-feESP5k3V_LOfk3PyGWCXQIs'

bot = telebot.TeleBot(API_TOKEN)

# Змінна для збереження статусу тривоги в областях
air_alerts = {
    'Київ': False, 'Львів': False, 'Одеса': False, 'Харків': False,
    'Дніпро': False, 'Запоріжжя': False, 'Івано-Франківськ': False,
    'Житомир': False, 'Черкаси': False, 'Чернігів': False,
    'Суми': False, 'Донецьк': False
}

# Структура даних для користувача
user_data = {}
used_names = set()  # Для зберігання вже вибраних імен користувачів
used_countries = set()  # Для зберігання вже вибраних країн
available_countries = ["Київ", "Львів", "Харків", "Суми", "Одеса", "Херсон", "Запоріжжя", "Івано-Франківськ",
                       "Чернігів", "Дніпро", "Житомир", "Донецьк", ]  # 12 областей
# Структура для зберігання ID користувачів по областях
region_users = {
    "Київ": [],
    "Львів": [],
    "Харків": [],
    "Суми": [],
    "Одеса": [],
    "Херсон": [],
    "Запоріжжя": [],
    "Івано-Франківськ": [],
    "Чернігів": [],
    "Дніпро": [],
    "Житомир": [],
    "Донецьк": []
}


# Структура будівель
buildings_data = {
    "АЕС": {"production": 33, "consumption": 5, "price": 45, "build_time": 3},  # Вартість, час будівництва (години)
    "ГЕС": {"production": 26, "consumption": 7, "price": 32, "build_time": 2.67},  # Час у годинах
    "ТЕС": {"production": 17, "consumption": 4, "price": 23, "build_time": 1.83},
    "ВЕС": {"production": 9, "consumption": 2, "price": 7, "build_time": 0.75},
    "АТБ": {"production": 27, "consumption": 12, "price": 17, "build_time": 2},
    "Квартира": {"production": 13, "consumption": 27, "price": 30, "build_time": 2.5},  # Квартира не виробляє енергію
    "АЗС": {"production": 19, "consumption": 7, "price": 10, "build_time": 1.5}
}

# Функція для обчислення споживання
def calculate_consumption(population):
    consumption_percentage = (population / 10) * 18
    return round(consumption_percentage)

# Створення кнопок
def create_back_button():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Назад"))
    return markup

import json

def save_user_data(user_id, username, password, country=None):
    try:
        with open('user_data.json', 'r+') as file:
            users = json.load(file)
            users[str(user_id)] = {'username': username, 'password': password, 'country': country}
            file.seek(0)
            json.dump(users, file, indent=4)
    except FileNotFoundError:
        with open('user_data.json', 'w') as file:
            users = {str(user_id): {'username': username, 'password': password, 'country': country}}
            json.dump(users, file, indent=4)

def load_user_data(user_id):
    try:
        with open('user_data.json', 'r') as file:
            users = json.load(file)
            return users.get(str(user_id))  # Повертає дані користувача або None
    except FileNotFoundError:
        return None


import hashlib

# Словник для зберігання паролів користувачів
user_passwords = {}

# Функція для хешування пароля
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Стартова функція для кожного нового користувача
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id

    # Створюємо кнопку та клавіатуру
    air_alert_button = types.KeyboardButton(get_air_alert_status())
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(air_alert_button)

    if user_id not in user_data:
        bot.send_message(message.chat.id, "Вітаю! Це симулятор України в ТГ. Напишіть ім'я персонажа.")
        bot.register_next_step_handler(message, set_username)
    else:
        if user_data[user_id]['name'] in used_names:
            bot.send_message(message.chat.id, "Це ім'я вже зареєстроване")
        else:
            bot.send_message(message.chat.id, "Введіть пароль для входу.")
            bot.register_next_step_handler(message, check_password)


# Функція для отримання статусу тривоги для кнопки
def get_air_alert_status():
    # Тут можна встановити логіку для конкретного регіону
    region = "Київ"  # Наприклад, регіон за замовчуванням
    return "Повітряна Тривога" if air_alerts[region] else "Немає тривоги"

# Оновлення кнопки після зміни статусу тривоги
def update_air_alert_button(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    air_alert_button = types.KeyboardButton(get_air_alert_status())
    markup.add(air_alert_button)
    bot.send_message(chat_id, "Оновлення статусу:", reply_markup=markup)

# Функція для встановлення пароля
def set_username(message):
    user_id = message.chat.id
    username = message.text.strip()

    if username in used_names:
        bot.send_message(message.chat.id, "Це ім'я вже зайняте. Спробуйте інше.")
        bot.register_next_step_handler(message, set_username)
        return

    used_names.add(username)
    bot.send_message(message.chat.id, "Введіть пароль для вашого аккаунта.")
    bot.register_next_step_handler(message, set_password)

# Функція для встановлення пароля
def set_password(message):
    user_id = message.chat.id
    password = message.text.strip()

    # Перевірка на наявність даних користувача в user_data
    if user_id not in user_data:
        user_data[user_id] = {}  # Ініціалізуємо порожній словник, якщо дані користувача відсутні

    # Зберігаємо хеш пароля
    user_passwords[user_id] = hash_password(password)

    # Ініціалізуємо інші параметри користувача
    user_data[user_id] = {
        'name': user_data[user_id].get('name', ''),  # Якщо ім'я не задано, то залишаємо порожнім
        'country': None,
        'balance': random.randint(150, 350),
        'energy_production': 0,
        'food_production': 0,
        'energy_consumption': 0,
        'food_consumption': 0,
        'population': random.randint(20, 80),
        'account_link': message.from_user.username,
        'buildings_in_progress': [],
    }

    bot.send_message(message.chat.id, "Пароль успішно встановлено! Тепер виберіть область.")
    show_country_selection(message)


# Перевірка пароля
# Функція для перевірки пароля
def check_password(message):
    user_id = message.from_user.id
    user_data = load_user_data(user_id)

    if user_data:
        correct_password = user_data['password']
        entered_password = message.text.strip()  # Забираємо зайві пробіли

        if entered_password == correct_password:
            bot.send_message(message.chat.id, "Вхід успішний!")
            show_main_menu(message)  # Показуємо головне меню після успішного входу
        else:
            bot.send_message(message.chat.id, "Невірний пароль. Спробуйте ще раз.")
            bot.register_next_step_handler(message, check_password)  # Повторно запитуємо пароль
    else:
        bot.send_message(message.chat.id, "Користувача не знайдено. Зареєструйтесь спочатку.")
        bot.register_next_step_handler(message, register_new_user)  # Запитуємо пароль для реєстрації


# Реєстрація нового користувача
def register_new_user(message):
    user_id = message.from_user.id
    new_password = message.text  # новий пароль для реєстрації

    user_data = {'username': message.from_user.username, 'password': new_password}
    save_user_data(user_id, message.from_user.username, new_password)

    bot.send_message(message.chat.id, "Реєстрація завершена! Тепер ви можете почати гру.")

# Функція для збереження даних користувача
def save_user_data(user_id, username, password):
    try:
        with open('user_data.json', 'r+') as file:
            users = json.load(file)
            users[str(user_id)] = {'username': username, 'password': password}
            file.seek(0)
            json.dump(users, file, indent=4)
    except FileNotFoundError:
        with open('user_data.json', 'w') as file:
            users = {str(user_id): {'username': username, 'password': password}}
            json.dump(users, file, indent=4)

def load_user_data(user_id):
    try:
        with open('user_data.json', 'r') as file:
            users = json.load(file)
            return users.get(str(user_id))  # Повертає дані користувача або None
    except FileNotFoundError:
        return None


@bot.message_handler(commands=['login'])
def login(message):
    user_id = message.from_user.id
    # Перевірка, чи є користувач у базі даних
    user_data = load_user_data(user_id)

    if user_data:  # Якщо користувач є в базі
        bot.send_message(message.chat.id, "Введіть ваш пароль для входу:")
        bot.register_next_step_handler(message, check_password, user_data)
    else:
        bot.send_message(message.chat.id, "Ви ще не зареєстровані. Будь ласка, введіть пароль для реєстрації:")
        bot.register_next_step_handler(message, register_new_user)


def check_password(message, user_data):
    entered_password = message.text  # Пароль, введений користувачем
    stored_password = user_data.get('password')  # Збережений пароль

    if entered_password == stored_password:  # Порівняння паролів
        bot.send_message(message.chat.id, "Вхід успішний!")

        # Перевірка наявності країни у користувача
        if 'country' in user_data and user_data['country'] is not None:
            # Якщо країна вже вибрана, відправити користувачу відповідне повідомлення і головне меню
            bot.send_message(message.chat.id, f"Вітаємо, ви повертаєтеся до гри {user_data['country']}.")
            show_main_menu(message)
        else:
            # Якщо країна не вибрана, запитуємо вибір
            show_country_selection(message)
    else:
        bot.send_message(message.chat.id, "Невірний пароль. Спробуйте ще раз.")
        bot.register_next_step_handler(message, check_password, user_data)  # Дати ще одну спробу


def register_new_user(message):
    user_id = message.from_user.id
    new_password = message.text

    # Створення нового запису користувача
    user_data = {'password': new_password}

    # Збереження в базі
    save_user_data(user_id, user_data)
    bot.send_message(message.chat.id, "Реєстрація успішна! Ви можете увійти за допомогою команди /login.")



# Функція для збереження даних користувача
def save_user_data(user_id, user_data):
    try:
        with open('user_data.json', 'r') as file:
            users = json.load(file)
    except FileNotFoundError:
        users = {}

    users[str(user_id)] = user_data

    with open('user_data.json', 'w') as file:
        json.dump(users, file, indent=4)



def load_user_data(user_id):
    try:
        with open('user_data.json', 'r') as file:
            users = json.load(file)
            print(f"Завантажено дані: {users}")  # Додати для відладки
            return users.get(str(user_id))  # Повертає дані користувача
    except FileNotFoundError:
        print("Файл user_data.json не знайдено.")
        return None

def show_country_selection(message):
    user_id = message.chat.id
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [KeyboardButton(country) for country in available_countries]
    markup.add(*buttons)
    bot.send_message(message.chat.id, "Оберіть Область для вашого персонажа:", reply_markup=markup)


# Функція для обробки вибору країни
@bot.message_handler(func=lambda message: message.text in available_countries)
def select_country(message):
    user_id = message.chat.id
    selected_country = message.text

    if selected_country in used_countries:
        bot.send_message(message.chat.id, "Ця Область вже зайнята, виберіть іншу.")
        show_country_selection(message)
        return

    if user_id not in user_data:
        user_data[user_id] = {}  # Якщо немає, ініціалізуємо словник для користувача

    # Збереження країни для користувача
    user_data[user_id]['country'] = selected_country
    used_countries.add(selected_country)
    bot.send_message(message.chat.id, f"Вітаємо, ви обрали область {selected_country}. Початок вашої кар'єри!")
    show_main_menu(message)


# Головне меню
def show_main_menu(message):
    user_id = message.chat.id
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Моя область"), KeyboardButton("Інші області"))
    markup.add(KeyboardButton("Будівництво"), KeyboardButton("Повітряна Тривога"))
    bot.send_message(message.chat.id, "Що ви хочете робити?", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in available_countries)
def choose_region(message):
    # Отримуємо область, яку вибрав користувач
    selected_region = message.text

    # Отримуємо ID користувача
    user_id = message.from_user.id

    # Додаємо ID користувача в список цієї області
    if user_id not in region_users[selected_region]:
        region_users[selected_region].append(user_id)

    # Зберігаємо обрану область для користувача в user_data
    if user_id not in user_data:
        user_data[user_id] = {'country': selected_region}
    else:
        user_data[user_id]['country'] = selected_region


# Функція для відображення інформації про країну
@bot.message_handler(func=lambda message: message.text == "Моя область")
def my_country(message):
    user_id = message.chat.id
    if user_id not in user_data or user_data[user_id]['country'] is None:
        bot.send_message(message.chat.id, "Ви ще не вибрали область!")
        return

    population = user_data[user_id]['population']
    energy_consumption = calculate_consumption(population)
    food_consumption = calculate_consumption(population)

    # Оцінка настрою населення
    energy_diff = user_data[user_id]['energy_production'] - energy_consumption
    if energy_diff > 10:
        mood = "Добрий"
    elif energy_diff < -10:
        mood = "Поганий"
    else:
        mood = "Стабільний"

    # Виведення статистики по країні з смайликами
    country_info = (
        f"🏙️<b>Ваша Область:</b> {user_data[user_id]['country']}\n"
        "\n"
        f"👤<b>Ім'я персонажа:</b> {user_data[user_id]['name']}👤\n"
        "\n"
        f"💶<b>Баланс:</b> {user_data[user_id]['balance']} млн $\n"
        "\n"
        f"⚡<b>Виробництво електроенергії:</b> {user_data[user_id]['energy_production']}%\n"
        "\n"
        f"🍽️<b>Виробництво їжі:</b> {user_data[user_id]['food_production']}%\n"
        "\n"
        f"🔋<b>Споживання електроенергії:</b> {energy_consumption}%\n"
        "\n"
        f"🍞<b>Споживання їжі:</b> {food_consumption}%\n"
        "\n"
        f"👥<b>Населення:</b> {user_data[user_id]['population']} млн\n"
        "\n"
        f"😊<b>Настрій населення:</b> {mood}\n"
    )

    # Надсилаємо повідомлення з інформацією по країні
    bot.send_message(message.chat.id, country_info, parse_mode="HTML")


@bot.message_handler(func=lambda message: message.text == "Інші області")
def other_countries(message):
    country_info = []
    for country in available_countries:
        if country not in used_countries:
            continue
        for user_id, data in user_data.items():
            if data['country'] == country:
                country_info.append(f"{country} - @{data['account_link']} - Настрій населення - {data['mood'] if 'mood' in data else 'Невідомо'}")


    if not country_info:
        country_info.append("Немає доступних областей для перегляду.")
    bot.send_message(message.chat.id, "\n".join(country_info))

# Функція для обробки кнопки "Назад"
@bot.message_handler(func=lambda message: message.text == "Назад")
def back_to_main_menu(message):
    show_main_menu(message)


# Зберігаємо статус тривог у глобальній змінній
air_alert = {
    'Київ': False, 'Львів': False, 'Одеса': False, 'Харків': False,
    'Дніпро': False, 'Запоріжжя': False, 'Івано-Франківськ': False,
    'Житомир': False, 'Черкаси': False, 'Чернігів': False,
    'Суми': False, 'Донецьк': False
}

# Обробник для команди /air_alert
@bot.message_handler(commands=['air_alert'])
def handle_air_alert_command(message):
    try:
        # Розбиваємо команду на частини
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "Формат: /air_alert <область> <почати/зняти>")
            return

        region, action = parts[1], parts[2]
        if region not in air_alert:
            bot.send_message(message.chat.id, f"Область '{region}' не знайдена!")
            return

            # Оновлюємо статус тривоги
        if action == "почати":
                air_alert[region] = True
                bot.send_message(message.chat.id, f"<b>У області {region} почалась тривога!</b>",parse_mode="HTML")
        elif action == "зняти":
                air_alert[region] = False
                bot.send_message(message.chat.id, f"<b>У області {region} відбій тривоги!</b>",parse_mode="HTML")
        else:
                bot.send_message(message.chat.id, "Доступні дії: почати, зняти.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Помилка: {e}")

# Обробник для кнопки "Повітряна Тривога"
@bot.message_handler(func=lambda message: message.text == "Повітряна Тривога")
def handle_air_alert_button(message):
    # Формуємо статус тривог
    alert_status = "\n".join(
        [ f"<b>{region}:</b> {'<b>📣 Тривога' if status else '🟢 Спокійно'}</b>" for region, status in air_alert.items()]
    )
    # Відправляємо повідомлення
    bot.send_message(message.chat.id, f"<b>Статус повітряної тривоги по областях:\n\n{alert_status}</b>")


import threading
import time

# Словник для збереження даних про гравців
user_data = {
    # Приклад структури даних користувача
    # user_id: {
    #     "country": "Київ",
    #     "name": "Олександр",
    #     "balance": 1000,
    #     "energy_production": 120,  # У відсотках
    #     "food_production": 80,  # У відсотках
    #     "population": 2,  # У мільйонах
    # }
}

# Перемикач для графіка відключень
area_schedule = {}


# Функція для зниження споживання електроенергії та відключень
def reduce_energy_schedule(user_id, area, hours):
    global area_schedule

    # Якщо користувач вже створив графік для цієї області
    if area in area_schedule and area_schedule[area]["in_progress"]:
        bot.send_message(user_id, f"Графік відключень для {area} вже в процесі. Спробуйте знову через 4 години.")
        return

    # Встановлюємо статус для цієї області
    area_schedule[area] = {"in_progress": True}

    # Повідомлення для всіх користувачів, що створюється графік
    bot.send_message(user_id, f"Графік погодинних відключень для {area} на {hours} години стартував!")
    bot.broadcast_message(f"Графік погодинних відключень для {area} стартував на {hours} години!")

    # Зменшуємо споживання для цієї області
    reduction_percentage = hours * 10  # Зменшення на 10% за кожну годину (1-5 годин дають зменшення від 10% до 50%)
    for hour in range(hours):
        time.sleep(3600)  # Зачекати 1 годину
        bot.send_message(user_id, f"Графік відключень: {hour + 1} з {hours} годин завершений для {area}.")

    # Після завершення відключень
    bot.send_message(user_id, f"Графік погодинних відключень для {area} завершено.")
    bot.broadcast_message(f"Графік погодинних відключень для {area} завершено.")

    # Встановлюємо, що графік більше не в процесі і можна буде знову використовувати через 4 години
    area_schedule[area]["in_progress"] = False


# Команда /electric для гравців
@bot.message_handler(commands=['electric'])
def electric(message):
    user_id = message.from_user.id
    parts = message.text.split()

    # Перевірка аргументів
    if len(parts) < 3:
        bot.send_message(message.chat.id, "Будь ласка, введіть правильний формат: /electric <область> <години>")
        return

    # Отримуємо область та кількість годин
    area = parts[1]  # Область для зниження споживання електроенергії
    try:
        hours = int(parts[2])  # Кількість годин
    except ValueError:
        bot.send_message(message.chat.id, "Будь ласка, введіть число для кількості годин.")
        return

    # Перевірка, чи кількість годин правильна (від 1 до 5)
    if hours not in [1, 2, 3, 4, 5]:
        bot.send_message(message.chat.id, "Будь ласка, виберіть кількість годин від 1 до 5.")
        return

    # Перевірка, чи користувач має право використовувати команду
    if area != user_data[user_id]['country']:  # Перевірка, чи користувач вказав свою область
        bot.send_message(message.chat.id, "Ви можете змінювати споживання лише у своїй області!")
        return

    # Запускаємо функцію для зниження споживання електроенергії в окремому потоці
    threading.Thread(target=reduce_energy_schedule, args=(user_id, area, hours)).start()

    # Повідомляємо про запуск графіку відключень
    bot.send_message(message.chat.id, f"Створюється графік погодинних відключень для {area} на {hours} години...")


# Функція для обробки будівництва
@bot.message_handler(func=lambda message: message.text == "Будівництво")
def building(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [KeyboardButton(building) for building in buildings_data]
    markup.add(*buttons)
    bot.send_message(message.chat.id, "Оберіть будівлю для побудови:", reply_markup=markup)

# Функція для вибору будівлі та початку будівництва автоматично
from datetime import datetime, timedelta


@bot.message_handler(func=lambda message: message.text in buildings_data)
def start_building(message):
    user_id = message.chat.id
    building_name = message.text
    building_info = buildings_data[building_name]

    # Перевірка, чи є користувач в даних
    if user_id not in user_data:
        bot.send_message(message.chat.id, "Ваш акаунт не знайдено. Будь ласка, зареєструйтеся або увійдіть.")
        return

    # Перевірка балансу користувача
    if user_data[user_id]['balance'] < building_info['price']:
        bot.send_message(message.chat.id, "У вас недостатньо коштів для цього будівництва.")
        return

    # Початок будівництва
    user_data[user_id]['balance'] -= building_info['price']

    # Розраховуємо час завершення будівництва
    finish_time = datetime.now() + timedelta(hours=building_info['build_time'])

    # Додаємо будівництво в процес
    user_data[user_id]['buildings_in_progress'].append({
        'name': building_name,
        'finish_time': finish_time,  # Час завершення
    })

    # Повідомлення про початок будівництва
    bot.send_message(message.chat.id,
                     f"Будівництво {building_name} розпочато! Це займе до {finish_time.strftime('%Y-%m-%d %H:%M:%S')}.")

    # Виведення інформації про будівлю
    building_info_message = (
        f"Будівництво {building_name} розпочато!\n"
        f"Час будівництва: {building_info['build_time']} години\n"
        f"Вартість: {building_info['price']} млн $\n"
        f"Виробництво енергії: {building_info['production']}%\n"
        f"Споживання енергії: {building_info['consumption']}%\n"
    )
    bot.send_message(message.chat.id, building_info_message)

    # Показуємо головне меню
    show_main_menu(message)


# Функція для перевірки закінчення будівництва
def check_building_status():
    current_time = datetime.now()  # Отримуємо поточний час
    for user_id, data in user_data.items():
        for building in data['buildings_in_progress']:
            finish_time = building['finish_time']  # Час завершення будівництва

            if current_time >= finish_time:
                # Завершення будівництва
                user_data[user_id]['buildings_in_progress'].remove(building)
                bot.send_message(user_id, f"Будівництво {building['name']} завершено!")

                # Оновлення статистики
                if building['name'] in buildings_data:
                    user_data[user_id]['energy_production'] += buildings_data[building['name']]['production']
                    user_data[user_id]['food_production'] += buildings_data[building['name']]['food_production']
                    user_data[user_id]['energy_consumption'] += buildings_data[building['name']]['consumption']
                    user_data[user_id]['food_consumption'] += buildings_data[building['name']]['consumption']
def initialize_user(user_id):
    user_data[user_id] = {
        'balance': 1000,  # Початковий баланс
        'buildings_in_progress': [],  # Список будівель, що будуються
        'energy_production': 0,  # Початкове виробництво енергії
        'food_production': 0,  # Початкове виробництво їжі
        'energy_consumption': 0,  # Початкове споживання енергії
        'food_consumption': 0  # Початкове споживання їжі
    }
    save_user_data(user_id, user_data)


# Перевірка стану будівництва що 60 секунд
import threading
def check_buildings():
    while True:
        check_building_status()
        time.sleep(60)

# Запуск фону для перевірки будівництва
threading.Thread(target=check_buildings, daemon=True).start()

# Функція для додавання винагороди до балансу користувача
def add_reward():
    current_time = datetime.now()
    if current_time.hour == 12 and current_time.minute == 0:  # Перевірка на 12:00
        for user_id in user_data:
            user_data[user_id]['balance'] += 35  # Додаємо 35 млн до балансу
            bot.send_message(user_id, "Прийшла винагорода: +35 млн$")
    elif current_time.hour == 22 and current_time.minute == 0:  # Перевірка на 22:00
        for user_id in user_data:
            user_data[user_id]['balance'] += 35  # Додаємо 35 млн до балансу
            bot.send_message(user_id, "Прийшла винагорода: +35 млн$")

# Функція для періодичної перевірки і додавання винагороди кожні 60 секунд
def check_rewards_periodically():
    while True:
        add_reward()
        time.sleep(60)  # Перевіряємо кожні 60 секунд

# Запуск функції перевірки в окремому потоці
def start_reward_thread():
    reward_thread = threading.Thread(target=check_rewards_periodically)
    reward_thread.daemon = True
    reward_thread.start()

# Виклик функції для запуску потоку
start_reward_thread()

# Функція для надсилання повідомлення всім користувачам
def send_message_to_all(bot, user_data, message_text):
    for user_id in user_data:
        bot.send_message(user_id, message_text)

# Функція для надсилання повідомлення конкретному користувачу
def send_message_to_user(bot, user_id, message_text):
    bot.send_message(user_id, message_text)

# Команда для адміністратора для надсилання повідомлення всім користувачам
@bot.message_handler(commands=['send_to_all'])
def send_message_from_admin(message):
    admin_user_id = 5707773847  # Ваш ID адміністратора
    if message.chat.id == admin_user_id:
        message_text = message.text[len('/send_to_all '):]  # Отримуємо текст після команди
        send_message_to_all(bot, user_data, message_text)
        bot.send_message(message.chat.id, "Повідомлення надіслано всім гравцям.")
    else:
        bot.send_message(message.chat.id, "Тільки адміністратор може використовувати цю команду.")

# Команда для адміністратора для надсилання повідомлення конкретному користувачу
@bot.message_handler(commands=['send_to_user'])
def send_message_to_user_command(message):
    admin_user_id = 5707773847  # Ваш ID адміністратора
    if message.chat.id == admin_user_id:
        # Формат команди: /send_to_user <user_id> <повідомлення>
        try:
            parts = message.text.split(' ', 2)
            target_user_id = int(parts[1])  # Ідентифікатор користувача
            message_text = parts[2]  # Текст повідомлення
            send_message_to_user(bot, target_user_id, message_text)
            bot.send_message(message.chat.id, f"Повідомлення надіслано користувачу {target_user_id}.")
        except Exception as e:
            bot.send_message(message.chat.id, "Невірний формат команди. Спробуйте ще раз.")
            print(f"Error: {e}")
    else:
        bot.send_message(message.chat.id, "Тільки адміністратор може використовувати цю команду.")


from telegram import InlineKeyboardButton, InlineKeyboardMarkup


#ножина для збереження використаних нікнеймів
used_names = set()

# Функція для очищення одного нікнейму
def clear_username(username):
    global used_names  # Використовуємо глобальну змінну used_names
    if username in used_names:
        used_names.remove(username)  # Видаляємо конкретний нікнейм
        print(f"Нікнейм {username} був очищений.")  # Виводимо повідомлення для відлагодження
        return f"Нікнейм {username} був успішно очищений."
    else:
        return f"Нікнейм {username} не знайдений."

# Множина для збереження використаних нікнеймів
used_names = set()

# Функція для очищення всіх нікнеймів
def clear_all_usernames():
    global used_names  # Використовуємо глобальну змінну used_names
    used_names.clear()  # Очищаємо множину
    print("Всі нікнейми були очищені.")  # Можна додати повідомлення для відлагодження
    return "Ваші нікнейми були успішно очищені. Користувачі можуть реєструватися знову."

# Перевірка команди /clear_usernames
@bot.message_handler(commands=['clear_usernames'])
def clear_usernames(message):
    # Перевірка, чи є у користувача права адміністратора
    if message.from_user.id == 5707773847:  # Замість YOUR_ADMIN_USER_ID введіть свій ID
        result_message = clear_all_usernames()
        bot.send_message(message.chat.id, result_message)
    else:
        bot.send_message(message.chat.id, "У вас немає прав для цієї команди.")


# Адмін команда для зміни балансу або населення в області
@bot.message_handler(commands=['set_balance'])
def set_balance(message):
    if not is_admin(message):  # Перевірка, чи є користувач адміністратором
        bot.send_message(message.chat.id, "Тільки адмін може змінювати баланс.")
        return

    parts = message.text.split()

    # Перевіряємо, чи є достатньо аргументів
    if len(parts) < 3:
        bot.send_message(message.chat.id,
                         "Будь ласка, введіть правильний формат: /set_balance <user_id> <новий баланс>")
        return

    user_id = int(parts[1])  # Припустимо, що user_id передається як другий аргумент
    try:
        new_balance = int(parts[2])  # Перетворення на ціле число
    except ValueError:
        bot.send_message(message.chat.id, "Будь ласка, введіть коректну суму для балансу.")
        return

    if user_id not in user_data:
        bot.send_message(message.chat.id, "Цей користувач не зареєстрований.")
        return

    # Оновлення балансу в user_data
    user_data[user_id]['balance'] = new_balance
    bot.send_message(message.chat.id, f"Баланс користувача {user_id} було оновлено на {new_balance} млн.")


@bot.message_handler(commands=['set_population'])
def set_population(message):
    if not is_admin(message):  # Перевірка, чи є користувач адміністратором
        bot.send_message(message.chat.id, "Тільки адмін може змінювати населення.")
        return

    parts = message.text.split()

    # Перевіряємо, чи є достатньо аргументів
    if len(parts) < 3:
        bot.send_message(message.chat.id,
                         "Будь ласка, введіть правильний формат: /set_population <user_id> <нове населення>")
        return

    user_id = int(parts[1])  # Припустимо, що user_id передається як другий аргумент
    try:
        new_population = int(parts[2])  # Перетворення на ціле число
    except ValueError:
        bot.send_message(message.chat.id, "Будь ласка, введіть коректну кількість населення.")
        return

    if user_id not in user_data:
        bot.send_message(message.chat.id, "Цей користувач не зареєстрований.")
        return

    # Оновлення населення в user_data
    user_data[user_id]['population'] = new_population
    bot.send_message(message.chat.id, f"Населення користувача {user_id} було оновлено на {new_population}.")


# Адмін команда для ракетної атаки
@bot.message_handler(commands=['rocket'])
def rocket_attack(message):
    if not is_admin(message):  # Перевірка, чи є користувач адміністратором
        bot.send_message(message.chat.id, "Тільки адмін може запускати ракетну атаку.")
        return

    parts = message.text.split()
    region = parts[1]

    if region not in available_countries:
        bot.send_message(message.chat.id, "Ця область не існує.")
        return

    # Рандомний шанс попадання
    hit_chance = random.randint(1, 2)  # 1 - попадання, 2 - не попадання
    if hit_chance == 1:
        bot.send_message(message.chat.id, f"Влучання в {region}! Деталі поки не відомі.")
        bot.send_message(message.chat.id, f"Увага! Враховуйте можливі наслідки.")
    else:
        bot.send_message(message.chat.id, f"ППО {region} успішно збила ракету.")
# Перевірка на адміністратора
def is_admin(message):
    admin_id = 5707773847  # ID адміністратора
    return message.from_user.id == admin_id

import json
import os
from telegram import Update
from telegram.ext import CallbackContext

# Файл для збереження ID користувачів
USERS_FILE = "users.json"

# Завантаження ID користувачів
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return []

# Збереження ID користувачів
def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as file:
        json.dump(users, file, ensure_ascii=False, indent=4)

# Реєстрація користувача
def register_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)  # Додаємо нового користувача
        save_users(users)  # Зберігаємо список користувачів


# Функція для перевірки, чи є користувач адміністратором
def is_admin(message):
    admin_id = 5707773847  # ID адміністратора
    return message.from_user.id == admin_id

# Функція для запуску ракетної атаки
@bot.message_handler(commands=['airraid'])
def airraid(message):
    if not is_admin(message):  # Перевірка, чи є користувач адміністратором
        bot.send_message(message.chat.id, "Тільки адмін може запускати повітряну атаку.")
        return

    parts = message.text.split()

    # Перевіряємо, чи є достатньо аргументів
    if len(parts) < 3:
        bot.send_message(message.chat.id, "Будь ласка, введіть правильний формат: /airraid <область> <тип атаки>")
        return

    region = parts[1]  # Область
    attack_type = parts[2]  # Тип атаки (Шахеди, ТУ-95, МБР, Крилата ракета)

    if region not in available_countries:
        bot.send_message(message.chat.id, "Ця область не існує.")
        return

    # Перевірка на тип атаки
    attack_info = {
        "Шахеди": {"time": 120, "hit_chance": 50, "damage_chance": 50},
        "ТУ-95": {"time": 300, "hit_chance": 65, "damage_chance": 45},
        "МБР": {"time": 30, "hit_chance": 75, "damage_chance": 25},
        "Крилата ракета": {"time": 90, "hit_chance": 80, "damage_chance": 20}
    }

    if attack_type not in attack_info:
        bot.send_message(message.chat.id, "Невідомий тип атаки. Доступні: Шахеди, ТУ-95, МБР, Крилата ракета.")
        return

    # Одержуємо інформацію про атаку
    attack = attack_info[attack_type]
    time_to_impact = attack["time"]
    hit_chance = random.randint(1, 100)
    damage_chance = random.randint(1, 100)

    # Оголошуємо час до атаки
    bot.send_message(message.chat.id, f"Запуск атаки {attack_type} на {region} через {time_to_impact} секунд...")

    time.sleep(time_to_impact)  # чекаємо час до удару

    # Перевіряємо, чи було влучання
    if hit_chance <= attack["hit_chance"]:
        # Влучання
        if damage_chance <= attack["damage_chance"]:
            bot.send_message(message.chat.id, f"Влучання в {region}! Зупинено будівництво 1 будівлі.")
        else:
            bot.send_message(message.chat.id, f"Влучання в {region}! Деталі поки невідомі.")
    else:
        # Не влучило
        bot.send_message(message.chat.id, f"ППО {region} успішно збила ракету.")


import telebot
import random

import random
import time

# Тільки Росія може бути атакована
attackable_region = "Росія"
# ID Києва (гравець, який грає за Київ)
kyiv_player_id = 5707773847  # Замініть на реальний ID Києва

# Дані про ракети
missiles = {
    "Нептун": {"flight_time": 60, "hit_chance": 50, "ppo_chance": 50},
    "Шторм": {"flight_time": 120, "hit_chance": 60, "ppo_chance": 50},
    "Атакмс": {"flight_time": 180, "hit_chance": 70, "ppo_chance": 50},
    "Крилата ракета": {"flight_time": 240, "hit_chance": 80, "ppo_chance": 50},
}

# Словник для тимчасового збереження запитів на атаку
pending_attacks = {}


# Функція для запуску атаки
@bot.message_handler(commands=['attack'])
def attack(message):
    user_id = message.from_user.id
    parts = message.text.split()

    # Перевірка аргументів
    if len(parts) < 3:
        bot.send_message(user_id, "Будь ласка, введіть правильний формат: /attack <область> <тип ракети>")
        return

    region = parts[1]  # Область для атаки
    missile_type = parts[2]  # Тип ракети

    if region != attackable_region:
        bot.send_message(user_id, "Атака можлива лише на Росію!")
        return

    if missile_type not in missiles:
        bot.send_message(user_id, f"Тип ракети '{missile_type}' не існує. Доступні: {', '.join(missiles.keys())}.")
        return

    # Зберігаємо запит на атаку та повідомляємо Київ
    pending_attacks[user_id] = {"region": region, "missile_type": missile_type, "user_name": message.from_user.first_name}
    bot.send_message(
        kyiv_player_id,
        f"{message.from_user.first_name} хоче запустити ракету '{missile_type}' по {region}.\n"
        "Дайте відповідь: /accept або /decline."
    )
    bot.send_message(user_id, "Ваш запит на атаку відправлено до Києва. Очікуйте відповіді.")


# Команда для схвалення атаки (Київ)
@bot.message_handler(commands=['accept'])
def accept_attack(message):
    if message.from_user.id != kyiv_player_id:
        bot.send_message(message.chat.id, "Тільки Київ може схвалити атаку.")
        return

    if not pending_attacks:
        bot.send_message(message.chat.id, "Немає активних запитів на атаку.")
        return

    # Обробка першого запиту з черги
    user_id, attack_data = pending_attacks.popitem()
    missile_type = attack_data["missile_type"]
    region = attack_data["region"]

    bot.send_message(message.chat.id, f"Київ схвалює запуск ракети '{missile_type}' по {region}!")
    bot.send_message(user_id, f"Ваш запит на запуск ракети '{missile_type}' по {region} схвалено! Ракета запускається...")

    # Запуск ракети
    missile_data = missiles[missile_type]
    flight_time = missile_data["flight_time"]
    hit_chance = missile_data["hit_chance"]
    ppo_chance = missile_data["ppo_chance"]

    bot.send_message(user_id, f"Ракета '{missile_type}' в дорозі. Час підльоту: {flight_time // 60} хвилин "
                              f"{flight_time % 60} секунд.")
    time.sleep(flight_time)

    # Розрахунок результатів
    if random.randint(1, 100) <= ppo_chance:
        bot.send_message(user_id, "Нажаль, ППО збила вашу ракету.")
    else:
        if random.randint(1, 100) <= hit_chance:
            bot.send_message(user_id, f"Успішне попадання ракети '{missile_type}'! Деталі поки невідомі.")
        else:
            bot.send_message(user_id, "Ракета не влучила в ціль.")


# Команда для відхилення атаки (Київ)
@bot.message_handler(commands=['decline'])
def decline_attack(message):
    if message.from_user.id != kyiv_player_id:
        bot.send_message(message.chat.id, "Тільки Київ може відхилити атаку.")
        return

    if not pending_attacks:
        bot.send_message(message.chat.id, "Немає активних запитів на атаку.")
        return

    # Обробка першого запиту з черги
    user_id, attack_data = pending_attacks.popitem()
    bot.send_message(message.chat.id, f"Київ відхилив запит на запуск ракети '{attack_data['missile_type']}' по {attack_data['region']}.")
    bot.send_message(user_id, "Ваш запит на атаку відхилено Києвом.")


import random
import time
import threading
from datetime import datetime, timedelta

# Клас для ППО
class PVO:
    def __init__(self, region):
        self.region = region
        self.pvo_level = 1  # Початковий рівень ППО
        self.coins = 0  # Поточний баланс користувача

        # Параметри для кожного рівня ППО
        self.upgrade_cost = {
            1: 7_000_000,
            2: 15_000_000,
            3: 25_000_000,
            4: 37_000_000,
            5: 49_000_000
        }

        self.hit_chance = {
            1: 10,  # шанс збиття 10%
            2: 20,  # шанс збиття 20%
            3: 30,  # шанс збиття 30%
            4: 40,  # шанс збиття 40%
            5: 50   # шанс збиття 50%
        }

        self.recharge_time = {
            1: 120,  # 2 хвилини
            2: 100,  # 1 хв 40 секунд
            3: 80,   # 1 хв 20 секунд
            4: 40,   # 40 секунд
            5: 30    # 30 секунд
        }

    def upgrade_pvo(self):
        """Покращення ППО."""
        if self.pvo_level < 5:
            next_level = self.pvo_level + 1
            cost = self.upgrade_cost[next_level]
            if self.coins >= cost:
                self.coins -= cost
                self.pvo_level = next_level
                return f"ППО в {self.region} покращено до рівня {self.pvo_level}."
            else:
                return "Недостатньо коштів для покращення ППО."
        else:
            return "ППО вже на максимальному рівні!"

    def defend_attack(self, attack_type):
        """Перевірка, чи зможе ППО збити ракету."""
        success_chance = self.hit_chance[self.pvo_level]
        defense_success = random.randint(1, 100)
        if defense_success <= success_chance:
            return f"Успішна робота ППО! {self.region} збила ракету типу {attack_type}."
        else:
            return f"ППО в {self.region} не змогло збити ракету типу {attack_type}."

    def get_recharge_time(self):
        """Отримуємо час на перезарядку."""
        return self.recharge_time[self.pvo_level]

    def set_coins(self, amount):
        """Встановлюємо баланс користувача."""
        self.coins = amount

    def get_pvo_info(self):
        """Отримати інформацію про поточний рівень ППО."""
        level_info = f"Рівень ППО: {self.pvo_level}\n"
        level_info += f"Шанс збиття ракет: {self.hit_chance[self.pvo_level]}%\n"
        level_info += f"Час перезарядки: {self.recharge_time[self.pvo_level]} секунд"
        return level_info


# Клас для користувача, де зберігаються всі дані користувача, включаючи ППО
class User:
    def __init__(self, user_id):
        self.user_id = user_id
        self.pvo = PVO('Київ')  # Припустимо, що всі користувачі мають ППО в Києві на старті
        self.coins = 0  # Поточний баланс користувача

    def get_user_pvo_info(self):
        return self.pvo.get_pvo_info()

# Створюємо користувача
user_data = {}

def get_user(user_id):
    """Функція для отримання користувача за ID"""
    if user_id not in user_data:
        user_data[user_id] = User(user_id)
    return user_data[user_id]

# Подія для зміни погоди та катастроф

def random_event():
    """Функція для випадкової зміни погоди або катастрофи."""
    events = ["Шторм у Києві", "Землетрус в Харкові", "Пожежа в Одесі", "Техногенна катастрофа у Львові", "Засуха на сході"]
    return random.choice(events)

# Таймер для запуску події раз на 2 години

def event_timer():
    """Функція для запуску події кожні 2 години."""
    while True:
        time.sleep(7200)  # 7200 секунд = 2 години
        event = random_event()
        print(f"Подія: {event} сталася! ({datetime.now()})")

# Запуск подій в окремому потоці

thread = threading.Thread(target=event_timer)
thread.daemon = True
thread.start()

# Команди для ППО

@bot.message_handler(commands=['upgrade_pvo'])
def upgrade_pvo_command(message):
    user = get_user(message.chat.id)
    response = user.pvo.upgrade_pvo()
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['defend_attack'])
def defend_attack_command(message):
    parts = message.text.split()
    attack_type = parts[1] if len(parts) > 1 else 'Шахед'
    user = get_user(message.chat.id)
    defense_result = user.pvo.defend_attack(attack_type)
    bot.send_message(message.chat.id, defense_result)

@bot.message_handler(commands=['set_coins'])
def set_coins_command(message):
    """Команда для встановлення коштів користувача"""
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Будь ласка, введіть правильний формат: /set_coins <сума>")
        return
    try:
        amount = int(parts[1])
        user = get_user(message.chat.id)
        user.pvo.set_coins(amount)
        bot.send_message(message.chat.id, f"Баланс коштів встановлено на {amount} грн.")
    except ValueError:
        bot.send_message(message.chat.id, "Будь ласка, введіть коректну суму.")

@bot.message_handler(commands=['pvo_info'])
def pvo_info_command(message):
    """Команда для отримання інформації про ППО"""
    user = get_user(message.chat.id)
    pvo_info = user.get_user_pvo_info()
    bot.send_message(message.chat.id, pvo_info)

# Запускаємо бота (потрібен токен для запуску)
# bot.polling(none_stop=True)


import random
import time
import threading

# Можливі погодні умови
weather_conditions = ['Сонячно', 'Дощ', 'Сніг', 'Туман', 'Вітер']

# Можливі екологічні катастрофи
disasters = ['Землетрус', 'Повінь', 'Лісова пожежа', 'Виверження вулкана']

# Змінні для збереження поточної погоди та катастрофи
current_weather = None
current_disaster = None

# Функція для генерації випадкової погоди
def get_weather():
    return random.choice(weather_conditions)

# Функція, що перевіряє погодні умови та їхній ефект
def weather_effect():
    current_weather = get_weather()
    if current_weather == 'Дощ':
        return "Дощ уповільнює будівництво на 10%."
    elif current_weather == 'Сніг':
        return "Сніг зменшує виробництво енергії на 20%."
    elif current_weather == 'Туман':
        return "Туман знижує точність ракетних атак на 30%."
    elif current_weather == 'Вітер':
        return "Вітер може спричинити проблеми в роботі ППО."
    else:
        return "Сонячна погода покращує всі процеси."

# Функція для випадкової екологічної катастрофи
def trigger_disaster():
    disaster = random.choice(disasters)
    if disaster == 'Землетрус':
        return "Землетрус знищив деякі будівлі та ресурси."
    elif disaster == 'Повінь':
        return "Повінь затопила частину вашого регіону, знизивши виробництво."
    elif disaster == 'Лісова пожежа':
        return "Лісова пожежа знищила частину лісів, знизивши ресурсні надходження."
    elif disaster == 'Виверження вулкана':
        return "Виверження вулкана спричинило загрозу для міст та їхніх мешканців."

# Таймер для випадкових погодних умов кожні 2 години
def weather_update():
    global current_weather
    while True:
        time.sleep(7200)  # 7200 секунд = 2 години
        current_weather = weather_effect()  # Оновлюємо погоду
        print(f"Погода оновлена: {current_weather}")
        # Тут можна додати код, щоб надіслати повідомлення гравцям

# Таймер для випадкових катастроф кожен день
def disaster_update():
    global current_disaster
    while True:
        time.sleep(86400)  # 86400 секунд = 1 день
        current_disaster = trigger_disaster()  # Оновлюємо катастрофу
        print(f"Катастрофа: {current_disaster}")
        # Тут можна додати код, щоб надіслати повідомлення гравцям

# Стартуємо потоки для оновлення погоди та катастроф
weather_thread = threading.Thread(target=weather_update)
weather_thread.daemon = True
weather_thread.start()

disaster_thread = threading.Thread(target=disaster_update)
disaster_thread.daemon = True
disaster_thread.start()

# Команда для перевірки поточної погоди (доступно лише адміну)
@bot.message_handler(commands=['weather'])
def show_weather(message):
    if not is_admin(message):  # Перевірка, чи є користувач адміністратором
        bot.send_message(message.chat.id, "Тільки адміністратор може переглядати та оголошувати погоду.")
        return

    if current_weather:
        bot.send_message(message.chat.id, f"Поточна погода: {current_weather}")
        # Розсилка всім користувачам
        for user_id in user_data.keys():
            bot.send_message(user_id, f"📡 Оновлення погоди: {current_weather}")
    else:
        bot.send_message(message.chat.id, "Погода ще не була оновлена.")

# Команда для перевірки останньої катастрофи (доступно лише адміну)
@bot.message_handler(commands=['disaster'])
def show_disaster(message):
    if not is_admin(message):  # Перевірка, чи є користувач адміністратором
        bot.send_message(message.chat.id, "Тільки адміністратор може переглядати та оголошувати катастрофи.")
        return

    if current_disaster:
        bot.send_message(message.chat.id, f"Остання екологічна катастрофа: {current_disaster}")
        # Розсилка всім користувачам
        for user_id in user_data.keys():
            bot.send_message(user_id, f"⚠️ Увага! Остання катастрофа: {current_disaster}")
    else:
        bot.send_message(message.chat.id, "Катастрофа ще не була оновлена.")

user_data = {}  # Словник для зберігання даних гравців

# Функція для реєстрації нового гравця
def register_player(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"name": f"Гравець {user_id}"}
        print(f"Новий гравець зареєстрований: {user_id}")



# Функція для перевірки стану потоку та автоматичного перезапуску бота
def run_bot():
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()

    while True:
        time.sleep(10)
        if not bot_thread.is_alive():
            print("Бот зупинився, перезапуск...")
            bot_thread = threading.Thread(target=start_bot)
            bot_thread.daemon = True
            bot_thread.start()

import json
import os

# Ім'я файлу для збереження даних
DATA_FILE = "players_data.json"

# Завантаження даних із файлу
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}

# Збереження даних у файл
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Оновлення інформації про користувача
def update_player(user_id, field, value):
    data = load_data()  # Завантаження актуальних даних
    if str(user_id) not in data:
        data[str(user_id)] = {}  # Додавання нового користувача, якщо його немає
    data[str(user_id)][field] = value  # Оновлення поля
    save_data(data)  # Збереження оновлених даних

# Отримання інформації про користувача
def get_player_data(user_id, field=None):
    data = load_data()  # Завантаження актуальних даних
    user_data = data.get(str(user_id))  # Отримання даних користувача
    if user_data:
        if field:
            return user_data.get(field)  # Повернення конкретного поля
        return user_data  # Повернення всіх даних користувача
    return None  # Якщо даних немає




from flask import Flask
import threading

app = Flask(__name__)

# Ваші маршрути Flask тут
@app.route('/')
def home():
    return "Hello, World!"

# Функція для запуску Flask сервера в окремому потоці
def run_flask():
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)

# В кінці основного коду
if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)


# Функція для запуску бота в окремому потоці
def start_bot():
    bot.polling(none_stop=True, interval=0)

if __name__ == '__main__':
    run_bot()

bot.polling(none_stop=True)
