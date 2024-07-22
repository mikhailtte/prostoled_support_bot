import asyncio
from config import SESSION_LIFETIME, MESSAGE_REMINDER_TIME
from time import time
from typing import Dict, List, Union
from aiogram import Bot
from config import SUPPORT_CHAT_ID as group_chat_id
import psutil

blacklist = []
selfname = []
keywords = []
active_messages: Dict[int, Dict[str, int]] = {}
'''
active_message[message.id: int] = {
    'chat_id': int,
    'date': int, (дата сообщения пользователя)
    'callback_message_id': int (айди доп. сообщения)
    'reminds_id': [int,] (список id напоминаний)
}
'''

sessions: Dict[int, Dict[str, Union[List[int], int]]] = {}
'''
sessions[chat_id: int] = {
    'messages_id': [int,], (список сообщений пользователя)
    'date': int (дата последней активности сессии),
    'user_id' : int
}
'''

async def init_userdata(bot: Bot, db):
    '''Инициализация ключевых слов, конфигурации заказов, названия бота'''
    # получение имени
    me = await bot.get_me()
    selfname.append(me.username)

    # инит ключевых слов
    keys = await db.get_autoresponces_keywords()
    if keys:
        for key in keys:
            keywords.append(key[0])

async def performance(db, stop: asyncio.Event):
    # 10 сек задержка включения
    try:
        await asyncio.wait_for(stop.wait(), timeout=10)
    except asyncio.TimeoutError:
        pass

    while not stop.is_set():
        try:
            memory = psutil.virtual_memory()
            cpu_used = psutil.cpu_percent()       
            await db.write_performance(memory.used, memory.total, cpu_used)
        except Exception as e:
            print(e)           
        # 10 сек ждем сигнала остановки
        try:
            await asyncio.wait_for(stop.wait(), timeout=10)
        except asyncio.TimeoutError:
            pass

async def remove_old_sessions(db, stop: asyncio.Event):
    while not stop.is_set():
        if sessions:

            current_time = time()
            
            old_sessions = next(
                ((session_id, data['user_id'])
                for session_id, data in sessions.items()
                if (current_time - data['date']) >= SESSION_LIFETIME),
                None
            )

            if old_sessions:
                for session_id, user_id in old_sessions:
                    
                    # наличие активных сообщений у старой сессии
                    has_active_message = any(
                        data['chat_id'] == session_id
                        for _ , data in active_messages.items()
                    )

                    if has_active_message:
                        sessions[session_id]['date'] += 600
                        # продлеваем срок жизни сессии на 10 минут
                    else:
                        await db.close_session(user_id)
                        del sessions[session_id]

        # 60 сек ждем сигнала остановки
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass

async def messages_reminder(bot: Bot, stop: asyncio.Event):
   
    while not stop.is_set():
        if active_messages:

            current_time = time()

            # вычисляет время, прошедшее с момента создания сообщения
            # и сравнивает его с временем, необходимым для отправки уведомления,
            # учитывая количество отправленных уведомлений 
            notice_to_messages = [
                (message_id, data['date'])
                for message_id, data in active_messages.items()
                if current_time - data['date'] >= MESSAGE_REMINDER_TIME * (len(data.get('reminds_id', [])) + 1)
            ]

            if notice_to_messages:

                for message_id, message_time in notice_to_messages:

                    minutes = round((current_time - message_time) / 60)
                    remind = await bot.send_message(
                        chat_id=group_chat_id,
                        text=f'⏰ Время ожидания: {minutes} мин.',
                        reply_to_message_id=message_id,
                        parse_mode='Markdown'
                    )
                    # если нет такого ключа создаем
                    active_messages[message_id].setdefault('reminds_id', [])
                    active_messages[message_id]['reminds_id'].append(remind.message_id)

        # 60 сек ждем сигнала остановки
        try:
            await asyncio.wait_for(stop.wait(), timeout=30)
        except asyncio.TimeoutError:
            pass
