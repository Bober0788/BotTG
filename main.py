import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
import random
import threading
import time

# Токен бота
API_TOKEN = '7716814998:AAHMsrFHr_-feESP5k3V_LOfk3PyGWCXQIs'

bot = telebot.TeleBot(API_TOKEN)

# Структура даних для користувача
user_data = {}
used_names = set()  # Для зберігання вже вибраних імен користувачів
used_countries = set()  # Для зберігання вже вибраних країн
available_countries = ["США", "Аргентина", "Бразилія", "Канада", "Україна", "Польща", "Швеція", "Фінляндія",
                       "Німеччина", "Іран", "Італія", "Франція", "Велика Британія", "Іспанія",
                       "Південна Африка", "Єгипет"]  # 16 країн

# Структура будівель
buildings_data = {
    "АЕС": {"production": 33, "consumption": 5, "price": 45, "build_time": 3},  # Вартість, час будівництва (години)
    "ГЕС": {"production": 26, "consumption": 7, "price": 32, "build_time": 2.67},  # Час у годинах
    "ТЕС": {"production": 17, "consumption": 4, "price": 23, "build_time": 1.83},
    "ВЕС": {"production": 9, "consumption": 2, "price": 7, "build_time": 0.75},
    "АТБ": {"production": 27, "consumption": 12, "price": 17, "build_time": 2},
    "Квартира": {"production": 0, "consumption": 27, "price": 30, "build_time": 0},  # Квартира не виробляє енергію
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

# Створення кнопки для коаліції
def create_coalition_button():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Приєднатись до ООН"), KeyboardButton("Приєднатись до НАТО"))
    return markup

# Стартова функція для кожного нового користувача
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if user_id not in user_data:
        bot.send_message(message.chat.id, "Вітаю! Це симулятор президента в ТГ. Напишіть ім'я персонажа.")
        bot.register_next_step_handler(message, set_username)
    else:
        if user_data[user_id]['name'] in used_names:
            bot.send_message(message.chat.id, "Це ім'я вже зареєстроване. Введіть пароль.")
        else:
            show_main_menu(message)

# Функція для встановлення імені персонажа
def set_username(message):
    user_id = message.chat.id
    username = message.text.strip()

    if username in used_names:
        bot.send_message(message.chat.id, "Це ім'я вже зайняте. Спробуйте інше.")
        bot.register_next_step_handler(message, set_username)
        return


    used_names.add(username)
    user_data[user_id] = {
        'name': username,
        'country': None,
        'balance': random.randint(150, 350),  # Початковий баланс
        'energy_production': 0,
        'food_production': 0,
        'energy_consumption': 0,
        'food_consumption': 0,
        'population': random.randint(20, 80),  # Початкове населення
        'account_link': message.from_user.username,
        'buildings_in_progress': [],  # Список будівель в процесі будівництва
        'coalition': None  # Коаліція (ООН або НАТО)
    }

    bot.send_message(message.chat.id, f"Вітаємо, {username}! Тепер виберіть країну.")
    show_country_selection(message)

# Функція для відображення клавіатури вибору країни
def show_country_selection(message):
    user_id = message.chat.id
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [KeyboardButton(country) for country in available_countries]
    markup.add(*buttons)
    bot.send_message(message.chat.id, "Оберіть країну для вашого персонажа:", reply_markup=markup)

# Функція для обробки вибору країни
@bot.message_handler(func=lambda message: message.text in available_countries)
def select_country(message):
    user_id = message.chat.id
    selected_country = message.text

    if selected_country in used_countries:
        bot.send_message(message.chat.id, "Ця країна вже зайнята, виберіть іншу.")
        show_country_selection(message)
        return

    user_data[user_id]['country'] = selected_country
    used_countries.add(selected_country)
    bot.send_message(message.chat.id, f"Вітаємо, ви обрали країну {selected_country}. Початок вашої кар'єри президента!")
    show_main_menu(message)

# Основне меню
def show_main_menu(message):
    user_id = message.chat.id
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Моя країна"), KeyboardButton("Інші країни"))
    markup.add(KeyboardButton("Будівництво"), KeyboardButton("Коаліція"))
    bot.send_message(message.chat.id, "Що ви хочете робити?", reply_markup=markup)

# Функція для відображення інформації про країну
@bot.message_handler(func=lambda message: message.text == "Моя країна")
def my_country(message):
    user_id = message.chat.id
    if user_id not in user_data or user_data[user_id]['country'] is None:
        bot.send_message(message.chat.id, "Ви ще не вибрали країну!")
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

    # Виведення статистики по країні
    country_info = (
        f"Ваша країна: {user_data[user_id]['country']}\n"
        f"Ім'я персонажа: {user_data[user_id]['name']}\n"
        f"Баланс: {user_data[user_id]['balance']} млн $\n"
        f"Виробництво електроенергії: {user_data[user_id]['energy_production']}%\n"
        f"Виробництво їжі: {user_data[user_id]['food_production']}%\n"
        f"Споживання електроенергії: {energy_consumption}%\n"
        f"Споживання їжі: {food_consumption}%\n"
        f"Населення: {user_data[user_id]['population']} млн\n"
        f"Настрій населення: {mood}\n"
        f"Коаліція: {user_data[user_id]['coalition'] if user_data[user_id]['coalition'] else 'Не приєднано'}"
    )

    bot.send_message(message.chat.id, country_info)


# Функція для обробки вибору коаліції
@bot.message_handler(func=lambda message: message.text == "Коаліція")
def coalition(message):
    markup = create_coalition_button()
    bot.send_message(message.chat.id, "Оберіть коаліцію:", reply_markup=markup)

# Функція для приєднання до коаліції
@bot.message_handler(func=lambda message: message.text in ["Приєднатись до ООН", "Приєднатись до НАТО"])
def join_coalition(message):
    user_id = message.chat.id
    user_data[user_id]['coalition'] = message.text
    bot.send_message(message.chat.id, f"Ви приєдналися до {message.text}!")
    show_main_menu(message)

# Функція для перегляду інших країн
@bot.message_handler(func=lambda message: message.text == "Інші країни")
def other_countries(message):
    country_info = []
    for country in available_countries:
        if country not in used_countries:
            continue
        for user_id, data in user_data.items():
            if data['country'] == country:
                country_info.append(f"{country} - @{data['account_link']} - Коаліція - {data['coalition'] if data['coalition'] else 'Не приєднано'}")

    if not country_info:
        country_info.append("Немає доступних країн для перегляду.")
    bot.send_message(message.chat.id, "\n".join(country_info))

# Функція для обробки кнопки "Назад"
@bot.message_handler(func=lambda message: message.text == "Назад")
def back_to_main_menu(message):
    show_main_menu(message)

# Функція для обробки будівництва
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

    # Перевірка балансу
    if user_data[user_id]['balance'] < building_info['price']:
        bot.send_message(message.chat.id, "У вас недостатньо коштів для цього будівництва.")
        return

    # Початок будівництва
    user_data[user_id]['balance'] -= building_info['price']

    # Розрахуємо час завершення будівництва
    finish_time = datetime.now() + timedelta(hours=building_info['build_time'])

    # Додаємо будівництво в процес
    user_data[user_id]['buildings_in_progress'].append({
        'name': building_name,
        'finish_time': finish_time,  # Тепер зберігається час завершення
    })

    # Повідомлення з часом завершення
    bot.send_message(message.chat.id,
                     f"Будівництво {building_name} розпочато! Це займе до {finish_time.strftime('%Y-%m-%d %H:%M:%S')}.")
    show_main_menu(message)

    # Виведення інформації про будівлю
    building_info_message = (
        f"Будівництво {building_name} розпочато!\n"
        f"Час будівництва: {building_info['build_time']} години\n"
        f"Вартість: {building_info['price']} млн $\n"
        f"Виробництво енергії: {building_info['production']}%\n"
        f"Споживання енергії: {building_info['consumption']}%\n"
    )
    bot.send_message(message.chat.id, building_info_message)

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

# Множина для збереження використаних нікнеймів
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


# В кінці основного коду
if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)


# Функція для запуску бота в окремому потоці
def start_bot():
    bot.polling(none_stop=True, interval=0)

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

if __name__ == '__main__':
    run_bot()
