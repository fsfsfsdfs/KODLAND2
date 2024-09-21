import telebot
from telebot import types
import sqlite3
import time
import threading
import requests
import json

bot_token = '5315502911:AAHFhNiFHW6omGgMoZkDj_NtfHhRq-Uzgjg'
bot = telebot.TeleBot(bot_token)
conn = sqlite3.connect('school.db', check_same_thread=False)
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, first_name TEXT, last_name TEXT, username TEXT, nickname TEXT, age INTEGER, gender TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS schedule
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, group_name TEXT, subject TEXT, start_time TEXT, FOREIGN KEY(user_id) REFERENCES users(user_id))''')

c.execute('''CREATE TABLE IF NOT EXISTS homework
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, description TEXT, due_time TEXT, FOREIGN KEY(user_id) REFERENCES users(user_id))''')

c.execute('''CREATE TABLE IF NOT EXISTS survey
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, question TEXT, options TEXT, due_time TEXT, FOREIGN KEY(user_id) REFERENCES users(user_id))''')

c.execute('''CREATE TABLE IF NOT EXISTS faq
             (id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answer TEXT)''')

conn.commit()

def insert_data(table, **kwargs):
    try:
        columns = ', '.join(kwargs.keys())
        placeholders = ', '.join('?' * len(kwargs))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        c.execute(query, tuple(kwargs.values()))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
        return False

def get_data(table, where_clause=None, **kwargs):
    try:
        if where_clause:
            query = f"SELECT * FROM {table} WHERE {where_clause}"
            c.execute(query, tuple(kwargs.values()))
        else:
            c.execute(f"SELECT * FROM {table}")
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"Error getting data: {e}")
        return None

def send_reminder():
    current_time = time.strftime('%H:%M')
    schedule = get_data('schedule', start_time=current_time)
    if schedule:
        for row in schedule:
            user_id = row[1]
            bot.send_message(user_id, "Напоминание: у вас скоро начнется урок!")

def create_inline_keyboard(buttons):
    keyboard = types.InlineKeyboardMarkup()
    for button_text, callback_data in buttons.items():
        button = types.InlineKeyboardButton(text=button_text, callback_data=callback_data)
        keyboard.add(button)
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user = get_data('users', user_id=user_id)

    if not user:
        bot.send_message(message.chat.id, "Привет, меня зовут SchoolBot! Я помогу тебе узнать расписание уроков и получить домашние задания. Чтобы начать, пожалуйста, зарегистрируйся.")
        bot.send_message(message.chat.id, "Напиши /register, чтобы зарегистрироваться.")
    else:
        buttons = {
            "Расписание уроков": "schedule",
            "Домашнее задание": "homework",
            "FAQ": "faq",
            "Опрос": "survey"
        }
        bot.send_message(message.chat.id, "Привет, SchoolBot! Вот что я могу сделать:", reply_markup=create_inline_keyboard(buttons))

@bot.message_handler(commands=['register'])
def register(message):
    user_id = message.from_user.id
    if get_data('users', user_id=user_id):
        bot.send_message(message.chat.id, "Вы уже зарегистрированы.")
    else:
        first_name, last_name, username, nickname, age, gender = "", "", "", "", "", ""
        bot.send_message(message.chat.id, "Пожалуйста, введите ваше имя.")
        bot.register_next_step_handler(message, lambda msg: get_next_step(msg, user_id, "first_name", first_name, last_name, username, nickname, age, gender))

def get_next_step(message, user_id, current_step, first_name, last_name, username, nickname, age, gender):
    if current_step == "first_name":
        first_name = message.text
        bot.send_message(message.chat.id, "Пожалуйста, введите вашу фамилию.")
        bot.register_next_step_handler(message, lambda msg: get_next_step(msg, user_id, "last_name", first_name, last_name, username, nickname, age, gender))
    elif current_step == "last_name":
        last_name = message.text
        bot.send_message(message.chat.id, "Пожалуйста, введите ваш username.")
        bot.register_next_step_handler(message, lambda msg: get_next_step(msg, user_id, "username", first_name, last_name, username, nickname, age, gender))
    elif current_step == "username":
        username = message.text
        bot.send_message(message.chat.id, "Пожалуйста, введите ваш nickname.")
        bot.register_next_step_handler(message, lambda msg: get_next_step(msg, user_id, "nickname", first_name, last_name, username, nickname, age, gender))
    elif current_step == "nickname":
        nickname = message.text
        bot.send_message(message.chat.id, "Пожалуйста, введите ваш возраст.")
        bot.register_next_step_handler(message, lambda msg: get_next_step(msg, user_id, "age", first_name, last_name, username, nickname, age, gender))
    elif current_step == "age":
        age = message.text
        bot.send_message(message.chat.id, "Пожалуйста, введите ваш пол.")
        bot.register_next_step_handler(message, lambda msg: get_next_step(msg, user_id, "gender", first_name, last_name, username, nickname, age, gender))
    elif current_step == "gender":
        gender = message.text
        insert_data('users', user_id=user_id, first_name=first_name, last_name=last_name, username=username, nickname=nickname, age=age, gender=gender)
        bot.send_message(message.chat.id, "Регистрация успешно завершена!")
        bot.send_message(message.chat.id, "Напишите /start, чтобы начать использовать бота.")

@bot.callback_query_handler(func=lambda call: True)
def callback_query_handler(call):
    if call.data in ["schedule", "homework", "faq", "survey"]:
        data = get_data(call.data, user_id=call.from_user.id)
        if data:
            message = '\n'.join([f"{row[2]}" for row in data])
        else:
            message = "Нет доступной информации."
        bot.send_message(call.message.chat.id, message)
    elif call.data.startswith("add_"):
        user_id = call.from_user.id
        table = call.data.split("_")[1]
        bot.send_message(user_id, f"Пожалуйста, введите информацию для {table.replace('_', ' ')}.")
        bot.register_next_step_handler(call.message, lambda msg: add_data(msg, user_id, table))

def add_data(message, user_id, table):
    if table == "schedule":
        bot.send_message(message.chat.id, "Пожалуйста, введите название группы.")
        bot.register_next_step_handler(message, lambda msg: get_next_add_step(msg, user_id, "group_name"))
    elif table == "homework":
        bot.send_message(message.chat.id, "Пожалуйста, введите описание домашнего задания.")
        bot.register_next_step_handler(message, lambda msg: get_next_add_step(msg, user_id, "description"))
    elif table == "survey":
        bot.send_message(message.chat.id, "Пожалуйста, введите вопрос опроса.")
        bot.register_next_step_handler(message, lambda msg: get_next_add_step(msg, user_id, "question"))

def get_next_add_step(message, user_id, current_step):
    if current_step == "group_name":
        group_name = message.text
        bot.send_message(message.chat.id, "Пожалуйста, введите название предмета.")
        bot.register_next_step_handler(message, lambda msg: get_next_add_step(msg, user_id, "subject"))
    elif current_step == "subject":
        subject = message.text
        bot.send_message(message.chat.id, "Пожалуйста, введите время начала урока в формате HH:MM.")
        bot.register_next_step_handler(message, lambda msg: get_next_add_step(msg, user_id, "start_time"))
    elif current_step == "start_time":
        start_time = message.text
        insert_data('schedule', user_id=user_id, group_name=group_name, subject=subject, start_time=start_time)
        bot.send_message(message.chat.id, "Информация успешно добавлена!")
    elif current_step == "description":
        description = message.text
        bot.send_message(message.chat.id, "Пожалуйста, введите время окончания домашнего задания в формате HH:MM.")
        bot.register_next_step_handler(message, lambda msg: get_next_add_step(msg, user_id, "due_time"))
    elif current_step == "due_time":
        due_time = message.text
        insert_data('homework', user_id=user_id, description=description, due_time=due_time)
        bot.send_message(message.chat.id, "Информация успешно добавлена!")
    elif current_step == "question":
        question = message.text
        bot.send_message(message.chat.id, "Пожалуйста, введите варианты ответа, разделенные запятыми.")
        bot.register_next_step_handler(message, lambda msg: get_next_add_step(msg, user_id, "options"))
    elif current_step == "options":
        options = message.text
        bot.send_message(message.chat.id, "Пожалуйста, введите время окончания опроса в формате HH:MM.")
        bot.register_next_step_handler(message, lambda msg: get_next_add_step(msg, user_id, "due_time"))
    elif current_step == "due_time":
        due_time = message.text
        insert_data('survey', user_id=user_id, question=question, options=options, due_time=due_time)
        bot.send_message(message.chat.id, "Информация успешно добавлена!")

# Schedule the reminder function to run every 5 minutes
reminder_thread = threading.Thread(target=send_reminder)
reminder_thread.start()

bot.polling(none_stop=True)