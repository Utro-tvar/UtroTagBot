import telebot
import time
import traceback
from telebot import types
import sqlite3
import regex
from typing import List, Tuple


#------------sql------------

with sqlite3.connect('tag_bot.db') as connection:
    cursor = connection.cursor()

    cursor.execute('PRAGMA foreign_keys = 1;')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Roles(
                role_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                chat_id INTEGER,
                role TEXT
    );''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS UserRolePairs(
                user_tag TEXT,
                role_id INTEGER,
                FOREIGN KEY (role_id) REFERENCES Roles(role_id) ON DELETE CASCADE,
                UNIQUE (user_tag, role_id)
    );
                ''')


def get_roles_list(chat_id : int) -> List[Tuple[int, str]]:
    with sqlite3.connect('tag_bot.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''SELECT role_id, role FROM Roles WHERE chat_id = ?;''', (chat_id, ))
        res = None if cursor.arraysize < 0 else cursor.fetchall()
    return  res

def get_users_with_role(role_id : int) -> List[str]:
    with sqlite3.connect('tag_bot.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''SELECT user_tag FROM UserRolePairs WHERE role_id = ?;''', (role_id, ))
        res = cursor.fetchall()
    return res

def create_role(chat_id : int, role : str):
    with sqlite3.connect('tag_bot.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''INSERT INTO Roles(chat_id, role) VALUES (?, ?);''', (chat_id, role))

def add_users_to_role(role_id : int, user_tags : List[str]):
    with sqlite3.connect('tag_bot.db') as connection:
        cursor = connection.cursor()
        for user in user_tags:
            cursor.execute('''INSERT INTO UserRolePairs VALUES (?, ?);''', (user, role_id))
            connection.commit()

def remove_users_from_role(role_id : int, user_tags : List[str]):
    with sqlite3.connect('tag_bot.db') as connection:
        cursor = connection.cursor()
        for user in user_tags:
            cursor.execute('''DELETE FROM UserRolePairs WHERE user_tag = ? AND role_id = ?;''', (user, role_id))
            connection.commit()

def remove_role(role_id : int):
    with sqlite3.connect('tag_bot.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''DELETE FROM Roles WHERE role_id = ?;''', (role_id, ))

def remove_chat(chat_id : int):
    with sqlite3.connect('tag_bot.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''DELETE FROM Roles WHERE chat_id = ?;''', (chat_id, ))

def get_role_name(role_id : int) -> str:
    with sqlite3.connect('tag_bot.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''SELECT role FROM Roles WHERE role_id = ?;''', (role_id, ))
        res = cursor.fetchone()
    return (res[0] if res != None else -1)

def get_role_id(role : str, chat_id) -> int:
    with sqlite3.connect('tag_bot.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''SELECT role_id FROM Roles WHERE role = ? AND chat_id = ?;''', (role, chat_id))
        res = cursor.fetchone()
    return (res[0] if res != None else -1)


#------------telebot------------

bot = telebot.TeleBot('6746468690:AAEbqkKHNg37x4vUBQHmLydFvPyv-_ADm2M', parse_mode='html')

#------------commands------------

@bot.message_handler(commands=['t'])
def tag_request(m : types.Message):
    key = types.InlineKeyboardMarkup()
    for role in get_roles_list(m.chat.id):
        tag_button = types.InlineKeyboardButton(text=role[1], callback_data=f'tag|{role[0]}')
        info_button = types.InlineKeyboardButton(text='📜', callback_data=f'list|{role[0]}')
        key.row(tag_button, info_button)
    close_button = types.InlineKeyboardButton(text='Закрыть ❌', callback_data='close')
    key.row(close_button)
    bot.send_message(text='<b><i>Выбери роль, которую надо упомянуть:</i></b>', reply_markup=key, chat_id=m.chat.id)
    bot.delete_message(chat_id=m.chat.id, message_id=m.id)
        

get_users = regex.compile(r'@([^@ ]+)( |$)+')
get_role = regex.compile(r'\/[^ ]+ ([^@ ]+)')

@bot.message_handler(commands=['add_role'])
def add_role(m: types.Message):
    print('add-role')
    bot.delete_message(chat_id=m.chat.id, message_id=m.id)
    if bot.get_chat_member(m.chat.id, m.from_user.id).status not in ['administrator', 'creator']: return
    users = [x[0] for x in regex.findall(get_users, m.text) if x[0] != bot.get_me().username]
    role = regex.search(get_role, m.text)
    if role == None : return
    role = role.group(1)
    role_id = get_role_id(role, m.chat.id)
    if role_id <= 0:
        create_role(m.chat.id, role)
        role_id = get_role_id(role, m.chat.id)
    add_users_to_role(role_id, users)


@bot.message_handler(commands=['delete_role'])
def delete_role(m: types.Message):
    print('delete-role')
    bot.delete_message(chat_id=m.chat.id, message_id=m.id)
    if bot.get_chat_member(m.chat.id, m.from_user.id).status not in ['administrator', 'creator']: return
    users = [x[0] for x in regex.findall(get_users, m.text) if x[0] != bot.get_me().username]
    role = regex.search(get_role, m.text)
    if role == None : return
    role = role.group(1)
    role_id = get_role_id(role, m.chat.id)
    if role_id <= 0:
        return
    if users == []:
        remove_role(role_id)
    else:
        remove_users_from_role(role_id, users)

@bot.message_handler(commands=['leave'])
def leave_request(m: types.Message):
    print('leave')
    if bot.get_chat_member(m.chat.id, m.from_user.id).status not in ['administrator', 'creator']: return
    key = types.InlineKeyboardMarkup()
    yes = types.InlineKeyboardButton(text='Да!!!', callback_data='leave')
    no = types.InlineKeyboardButton(text='Нет!!!', callback_data='close')
    key.row(yes, no)
    bot.send_message(text='Вы уверены, что хотите меня выгнать???', reply_markup=key, chat_id=m.chat.id)
    
#------------buttons functions------------

@bot.callback_query_handler(func= lambda call: call.data == 'leave')    
def leave(call : types.CallbackQuery):
    bot.edit_message_text(text='Счастливо оставаться, <s>лошки</s> 👋😘', chat_id=call.message.chat.id, message_id=call.message.id, reply_markup=None)
    bot.leave_chat(call.message.chat.id)
    remove_chat(call.message.chat.id)

@bot.callback_query_handler(func= lambda call: str.find(call.data, 'tag') != -1)
def tag(call : types.CallbackQuery):
    role_id = int(regex.search(r'\|(\d+)', call.data).group(1))
    text = f'<b>{get_role_name(role_id)}</b>\n<i>tagged by @{call.from_user.username}</i>\n\n' + ' '.join(['@' + x[0] for x in get_users_with_role(role_id)])
    bot.send_message(text= text, chat_id=call.message.chat.id, reply_markup=None)
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)

@bot.callback_query_handler(func= lambda call: str.find(call.data, 'list') != -1)
def list_users(call : types.CallbackQuery):
    role_id = int(regex.search(r'\|(\d+)', call.data).group(1))
    bot.edit_message_text(text= f'<b>{get_role_name(role_id)}:</b>\n' + '\n'.join([x[0] for x in get_users_with_role(role_id)]) + '\n\n<b><i>Выбери роль, которую надо упомянуть:</i></b>',
                          chat_id=call.message.chat.id, message_id=call.message.id, reply_markup=call.message.reply_markup)
    
@bot.callback_query_handler(func= lambda call: call.data == 'close')    
def leave(call : types.CallbackQuery):
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)

while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        with open('logger.txt', 'a') as log:
            log.write('\n' + traceback.format_exc())
        time.sleep(15)