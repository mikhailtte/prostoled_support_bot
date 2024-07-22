from datetime import datetime
from io import BytesIO
from aiogram import types, Bot
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import exceptions
from time import time, strftime, localtime
from services import sessions, active_messages, selfname
from config import SUPPORT_CHAT_ID as group_chat_id
from database import db, message_cell, user_cell, prod_cell
import filters
import json

MD = 'Markdown'

async def reply(message: types.Message):
    
    # если сообщение на которое ответили в словаре активных сообщений
    if hasattr(message.reply_to_message, 'message_id'):
        
        user_chat_message_id = None
        # прверяем не ответ ли на напоминание
        reply_to = [ 
            id
            for id, data in active_messages.items()
            if message.reply_to_message.message_id in data['reminds_id']
        ]

        # если ответ на напоминание или на активный
        if reply_to or message.reply_to_message.message_id in active_messages.keys():            
            # если активный и если ответ на напоминание задаем id активного сообщения
            if not reply_to:
                reply_to = message.reply_to_message.message_id
            else:
                reply_to = reply_to[0]

            # пересылаем ответ пользователю
            try:
                sent = await message.bot.forward_message(
                    # айди чата пользователя
                    chat_id=active_messages.get(reply_to).get('chat_id'),
                    # айди канала источника  
                    from_chat_id=group_chat_id,
                    # айди сообщения в канале источнике
                    message_id=message.message_id,
                    disable_notification=False,
                    protect_content=False
                )
                # удаляем сообщение со статусом и кнопкой игнор
                try:
                    await message.bot.delete_message(
                        chat_id=group_chat_id,
                        message_id=active_messages[reply_to]['callback_message_id'],
                    )
                except Exception as e:
                    pass
                user_chat_message_id = sent.message_id
            except exceptions.BotBlocked as e:
                await message.reply("Не отправлено: бот заблокирован пользователем")
                # сообщение не было отправлено
                user_chat_message_id = None
            except Exception as e:
                await message.reply('Ошибка отправки #a1')
                # сообщение не было отправлено
                user_chat_message_id = None
                pass

            sessions[active_messages.get(reply_to).get('chat_id')]['date'] = time()
            # подмена для правильной записи в бд
            message.reply_to_message.message_id = reply_to
            await db.write_message(
                message,
                client=False,
                client_chat_id=active_messages.get(reply_to).get('chat_id'),
                client_chat_message_id=user_chat_message_id)
            # удаляем сообщение из словаря активных
            del active_messages[reply_to]
        else:
            # если сессия активна, но нет активных сообщений
            user_chat_id = None
            for _chat_id, _session_data in sessions.items():
                if message.reply_to_message.message_id in _session_data.get('messages_id'):
                    user_chat_id = _chat_id
                    break

            if user_chat_id is None:
                # сессия была завершена, или повторный ответ на напоминание.
                await message.reply('❌ Не отправлено: Сообщение клиента не было найдено.')
            else:
                # сессия активна
                # пересылаем ответ пользователю
                try:
                    sent = await message.bot.forward_message(
                        # айди чата пользователя
                        chat_id=user_chat_id,
                        # айди канала источника
                        from_chat_id=group_chat_id,
                        # айди сообщения в канале источнике
                        message_id=message.message_id,
                        disable_notification=False,
                        protect_content=False
                    )
                    user_chat_message_id = sent.message_id
                except exceptions.BotBlocked as e:
                    message.reply("Не отправлено: бот заблокирован пользователем")
                except Exception as e:
                    pass
                finally:
                    user_chat_message_id = None

                sessions[user_chat_id]['date'] = time()
                await db.write_message(
                    message=message,
                    client=False,
                    client_chat_id=user_chat_id,
                    client_chat_message_id=user_chat_message_id
                )

async def ignore_message(callback_query: types.CallbackQuery):
    # удаляем сообщение со статусом и кнопкой
    try:
        await callback_query.bot.delete_message(
            chat_id=group_chat_id,
            # в cb нам приходит айди исходного пересланного сообщения
            # в группе, по нему мы обращаемся к активному сообщению в соотв.
            # словаре откуда мы берем айди доп. сообщ. со статусом и кнопкой
            # и удаляем его 
            message_id=active_messages[int(callback_query.data.split(':')[1])]['callback_message_id']
        )
    except Exception as e:
        ...
    try:
        # удаляем сообщение из словаря активных
        del active_messages[int(callback_query.data.split(':')[1])]
    except Exception as e:
        ...

async def delete_message(message: types.Message):
    if not hasattr(message.reply_to_message, 'message_id'):
        _text = '❌ Для удаления вашего сообщения у пользователя ответьте на него ' \
            'в группе используя эту команду'
        await message.reply(_text)
    else:
        try:
            db_message = await db.get_message(message.reply_to_message.message_id)
            await message.bot.delete_message(
                chat_id=db_message[message_cell.chat_id],
                message_id=db_message[message_cell.user_chat_message_id]
            )
            await message.reply("✅ Сообщение удалено у пользователя")
        except Exception as e:
            await message.reply("❌ Не получилось удалить")

async def send_rate(message: types.Message):
    if not hasattr(message.reply_to_message, 'message_id'):
        _text = '❌ Для предложения оценки работы ответьте на любое сообщение пользователя командой /оцените'
        await message.reply(_text)
    else:
        try:
            db_message = await db.get_message(message.reply_to_message.message_id)
            await message.bot.send_message(
                chat_id=db_message[message_cell.chat_id],
                text='Спасибо за обращение!\nОцените пожалуйста нашу работу отправив оценку или комментарий:'
            )
            await message.reply("✅ Отправлено")
        except Exception as e:
            await message.reply("❌ Ошибка")

async def session_history(message: types.Message):
    if not hasattr(message.reply_to_message, 'message_id'):
        _text = 'Перешлите (reply/ответить) любое сообщение пользователя'\
            ' для получения его истории последней сессии'
        await message.reply(_text)
    else:
        try:
            # заправшиваем в бд айди чата откуда это сообщение
            db_message = await db.get_message(message.reply_to_message.message_id)
            # запрашиваем все сообщения из этого чата за посл сессию
            db_messages = await db.get_session(db_message[message_cell.chat_id])
            dt = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            # по каждму сообщению формутируем его текст исходя из его содержимого
            history = '==================================================================================================\n'\
                'Для получения медиа-содержимого скопируйте и отправьте боту динамические команды начинающиеся с \"/\"\n'\
                '==================================================================================================\n'\
            f'Сгенерировано: {dt}\n\n'
            
            for db_message in db_messages:

                history += ''.join((
                    f'\n\n[@{db_message[message_cell.username]}] ' if db_message[message_cell.username] else f'[id: {db_message[message_cell.user_id]}] ',
                    datetime.fromtimestamp(db_message[message_cell.date]).strftime('%d.%m.%Y %H:%M:%S'),
                    f'\n{db_message[message_cell.text]}\n\n' if db_message[message_cell.text] else '',
                    f'\n/photo:{db_message[message_cell.photo]}' if db_message[message_cell.photo] else '',
                    f'\n/animation:{db_message[message_cell.animation]}' if db_message[message_cell.animation] else '',
                    f'\n/audio:{db_message[message_cell.audio]}' if db_message[message_cell.audio] else '',
                    f'\n/document:{db_message[message_cell.document]}' if db_message[message_cell.document] else '',
                    f'\n/sticker:{db_message[message_cell.sticker]}' if db_message[message_cell.sticker] else '',
                    f'\n/video:{db_message[message_cell.video]}' if db_message[message_cell.video] else '',
                    f'\n/voice:{db_message[message_cell.voice]}' if db_message[message_cell.voice] else '',
                    f'\n/contact:{db_message[message_cell.message_id]}' if db_message[message_cell.contact] else '',
                    f'\n/location:{db_message[message_cell.message_id]}' if db_message[message_cell.location] else '',
                    f'\n/invoice:{db_message[message_cell.message_id]}' if db_message[message_cell.invoice] else '',
                    f'\n/successful_payment:{db_message[message_cell.message_id]}' if db_message[message_cell.successful_payment] else '',
                    f'\n(attached:{message.connected_website})' if db_message[message_cell.connected_website] else '',
                    f'\n/passport:{db_message[message_cell.message_id]}' if db_message[message_cell.passport_data] else '',
                    f'\n/markup:{db_message[message_cell.message_id]}' if db_message[message_cell.reply_markup] else '',
                    '\nКнопки: ' + \
                    str([button['text'] for row in json.loads(db_message[message_cell.reply_markup])['inline_keyboard'] for button in row])
                    if db_message[message_cell.reply_markup] else '' 
                ))

            file_data = BytesIO(history.encode())
            file = types.InputFile(file_data, filename=f'session_{db_message[message_cell.username]}.txt')
            await message.bot.send_document(chat_id=message.chat.id, document=file)

        except Exception as e:
            await message.reply('❌ Ошибка')

async def history(message: types.Message):
    if not hasattr(message.reply_to_message, 'message_id'):
        text = 'Вместе с этой командой используйте (reply/ответить) '\
            'на любое сообщение пользователя для получения его полной истории'
        await message.reply(text)
    else:
        try:
            # заправшиваем в бд айди чата откуда это сообщение
            db_message = await db.get_message(message.reply_to_message.message_id)
            # запрашиваем все сообщения из этого чата за посл сессию
            db_messages = await db.get_history(db_message[message_cell.chat_id])
            dt = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

            # по каждму сообщению формутируем его текст исходя из его содержимого
            history = '==================================================================================================\n'\
                'Для получения медиа-содержимого скопируйте и отправьте боту динамические команды начинающиеся с \"/\"\n'\
                '==================================================================================================\n'\
            f'Сгенерировано: {dt}\n\n'
            
            for db_message in db_messages:

                history += ''.join((
                    f'\n\n[@{db_message[message_cell.username]}] ' if db_message[message_cell.username] else f'[id: {db_message[message_cell.user_id]}] ',
                    datetime.fromtimestamp(db_message[message_cell.date]).strftime('%d.%m.%Y %H:%M:%S'),
                    f'\n{db_message[message_cell.text]}\n\n' if db_message[message_cell.text] else '',
                    f'\n/photo:{db_message[message_cell.photo]}' if db_message[message_cell.photo] else '',
                    f'\n/animation:{db_message[message_cell.animation]}' if db_message[message_cell.animation] else '',
                    f'\n/audio:{db_message[message_cell.audio]}' if db_message[message_cell.audio] else '',
                    f'\n/document:{db_message[message_cell.document]}' if db_message[message_cell.document] else '',
                    f'\n/sticker:{db_message[message_cell.sticker]}' if db_message[message_cell.sticker] else '',
                    f'\n/video:{db_message[message_cell.video]}' if db_message[message_cell.video] else '',
                    f'\n/voice:{db_message[message_cell.voice]}' if db_message[message_cell.voice] else '',
                    f'\n/contact:{db_message[message_cell.message_id]}' if db_message[message_cell.contact] else '',
                    f'\n/location:{db_message[message_cell.message_id]}' if db_message[message_cell.location] else '',
                    f'\n/invoice:{db_message[message_cell.message_id]}' if db_message[message_cell.invoice] else '',
                    f'\n/successful_payment:{db_message[message_cell.message_id]}' if db_message[message_cell.successful_payment] else '',
                    f'\n(attached:{message.connected_website})' if db_message[message_cell.connected_website] else '',
                    f'\n/passport:{db_message[message_cell.message_id]}' if db_message[message_cell.passport_data] else '',
                    f'\n/markup:{db_message[message_cell.message_id]}' if db_message[message_cell.reply_markup] else '', '\nКнопки: ' + \
                    str([button['text'] for row in json.loads(db_message[message_cell.reply_markup])['inline_keyboard'] for button in row])
                    if db_message[message_cell.reply_markup] else '' 
                ))

            file_data = BytesIO(history.encode())
            file = types.InputFile(file_data, filename=f'history_{db_message[message_cell.username]}.txt')
            await message.bot.send_document(chat_id=message.chat.id, document=file)

        except Exception as e:
            await message.reply('❌ Ошибка')

async def active_session(message: types.Message):
    await message.reply(f'Количество активных сессий: {len(sessions.keys())}')

async def get_performance(message: types.Message):
    # если с коммандой прислали лимит записей, запрашивает это кол-во
    limit = message.text.replace('/производительность', '').replace('/performance', '').strip()
    if limit:
        try:
            limit = int(limit)
            perf = await db.get_performance(limit)
        except Exception as e:
            pass
    else:
        # если не прислали лимит - запрашиваем по умолчанию (1000 записей)
        perf = await db.get_performance()

    if perf:
        perf_text = ''
        timestamp = 0; mem = 1; total = 2; cpu = 3
        for row in perf:
            perf_text += ''.join((
                datetime.fromtimestamp(row[timestamp]).strftime('%d.%m.%Y %H:%M:%S'),
                f'  memory usage: {round(row[mem]/1024 ** 2)} Mb',
                f'  memory total: {round((row[total]/1024 ** 2))} Mb',
                f'  CPU usage: {int(row[cpu])}%', '\n'
            ))

        file_data = BytesIO(perf_text.encode())
        file = types.InputFile(file_data, filename=f'performance.txt')
        await message.bot.send_document(chat_id=message.chat.id, document=file)
    else:
        await message.reply('Записей нет')

async def peak_performance(message: types.Message):
    peak = await db.peak_performance()
    peak_text = 'Пик производительности за последние 7 дней '\
        'по использованию оперативной памяти и ЦП:\n\n'
    timestamp = 0; mem = 1; total = 2; cpu = 3
    for row in peak:
            peak_text += ''.join((
                datetime.fromtimestamp(row[timestamp]).strftime('%d.%m.%Y %H:%M:%S'),
                f'  memory usage: {round(row[mem]/1024 ** 2)} Mb',
                f'  memory total: {round((row[total]/1024 ** 2))} Mb',
                f'  CPU usage: {int(row[cpu])}%', '\n\n'
            ))
    await message.reply(peak_text)

async def message_count_per_day(message: types.Message):
    count = await db.message_per_day()
    await message.reply(f'Количество сообщений пользователей за сутки: {count[0][0]}')

async def add_to_blacklist(message: types.Message):
    if hasattr(message, 'reply_to_message') and hasattr(message.reply_to_message, 'message_id'):
        # если сессия открыта
        user_id = [
            data['user_id']
            for _, data in sessions.items()
            if message.reply_to_message.message_id in data['messages_id']
        ]
        if user_id:
            await db.add_to_blacklist(user_id[0])
            await message.reply('Пользователь добавлен в черный список.')
        else:
            # если сессия закрыта берем айди польователя из бд
            user_message = await db.get_message(message.reply_to_message.message_id)
            await db.add_to_blacklist(user_message[message_cell.user_id])
            await message.reply('Пользователь добавлен в черный список.')
    else:
        text = 'Для добавления пользователя в черный список ответьте' \
            ' на его сообщение командой /вчс'
        await message.reply(text)

async def get_blacklist(message: types.Message):
    # запрашиваем в бд список айди чс
    bl = await db.get_blacklist()

    if not bl:
        await message.reply('Черный список пуст.')   
    else:
        reply_list = ''

        for row in bl:
            reply_list += ''.join((
                f'@{row[user_cell.username]} 'if row[user_cell.username] else '',
                f'{row[user_cell.first_name]} ' if row[user_cell.first_name] else '',
                f'{row[user_cell.fullname]}' 
                    if row[user_cell.fullname] and row[user_cell.fullname] != row[user_cell.first_name] else '',
                f'\n/del{row[user_cell.user_id]}', '\n\n'
            ))
        if len(bl) < 5:
            # пишем список в сообщениии
            await message.reply(reply_list)
        else:
            # список в файле
            file_data = BytesIO(reply_list.encode())
            file = types.InputFile(file_data, filename=f'blacklist.txt')
            await message.bot.send_document(chat_id=message.chat.id, document=file)
        text = 'Перешлите сообщение клиента из этого чата c комадой /вчс или /изчс' \
            ' для добавления или удаления из черного списка'
        await message.answer(text)

async def remove_from_blacklist(message: types.Message):
    if message.text.startswith('/del'):
        try:
            remove_id = int(message.text.replace(f'@{selfname[0]}', '').replace('/del', ''))
            ok =  await db.remove_from_blacklist(remove_id)
            await message.reply('✅ Пользователь удален из черного списка.' if ok else '❌ Ошибка')
        except ValueError as e:
            text = "Это динамическая команда, скопируйте ее *целиком* из черного списка /blacklist"
            await message.reply(text, parse_mode=MD)
    elif message.text.upper() in ('/ИЗЧС'):
        if hasattr(message, 'reply_to_message') and hasattr(message.reply_to_message,'message_id'):
            user_message = await db.get_message(message.reply_to_message.message_id)
            ok =  await db.remove_from_blacklist(user_message[message_cell.user_id])
            await message.reply('✅ Пользователь удален из черного списка' if ok else '❌ Ошибка')
        else:
            text = 'Для удаления пользователя из черного списка ответье ' \
                'на любое его сообщение командой */изчс*\nили используейте ' \
                'динамическую команду del из черного списка /blacklist'
            await message.reply(text, parse_mode=MD)

async def execute_sql_query(message: types.Message):
    if len(message.text.split(':')) > 0:
        result = await db.execute_sql_command(message.text.split(':')[1])
        await message.reply(str(result))
    else:
        message.reply('SQL: Пришлите текст запроса после \":\"\n', parse_mode=MD)
        message.reply('\'')

async def get_autoresponces(message: types.Message):
    autoresps = await db.get_autoresponces()
    text_reply = '==================================================================================================\n'\
        'Для получения медиа-содержимого скопируйте и отправьте боту динамические команды начинающиеся с \"/\"\n'\
        '==================================================================================================\n'\
        'Список настроенных автоответов:\n\n'
    key = 0; text = 1; photo = 2
    if autoresps:
        for row in autoresps:
            text_reply += ''.join((
                f'Ключевое слово: {row[key]}', '\n',
                f'Ответ: {row[text]}', '\n',
                f'Фото: /photo:{row[photo]}' if row[photo] is not None else '', '\n\n'
            ))
        
        # список в файле
        file_data = BytesIO(text_reply.encode())
        file = types.InputFile(file_data, filename=f'autoresponces.txt')
        await message.bot.send_document(chat_id=message.chat.id, document=file)
    else:
        await message.reply('Список автоответов пуст.')
    
    # text = 'Для управления используйте /add_autoresponce или '\
    #     '/добавить_автоответ\nИли /удалитьавтоответ *в личном чате с ботом*'
    # message.reply(text, parse_mode=MD)

async def add_comment(message: types.Message):
    if not hasattr(message.reply_to_message, 'message_id'):
        _text = '❌ Для добавления заметки ответье на ' \
            'сообщение покупателя командой:' \
            '\n/заметка _любой текст здесь_\n\n' \
            'Для просмотра заметки ответье ' \
            'просто командой:\n/заметка'
        await message.reply(_text, parse_mode=MD)
        
    else:
        # добавлене новой если есть текст
        if message.text.replace('/коммент', '').replace('/заметка', '').strip():
            # try:
            user_message = await db.get_message(message.reply_to_message.message_id)
            await db.add_comment(
                user_id=user_message[message_cell.user_id],
                text=message.text.replace('/коммент', '').replace('/заметка', '').strip()
            )
            await message.reply("✅ Готово")
            # except Exception as e:
            #     await message.reply("❌ Ошибка")
            # просмотр заметки если нет текста новой
        else:
            try:
                user_message = await db.get_message(message.reply_to_message.message_id)
                if not user_message:
                    raise
                comment = await db.get_comment(user_message[message_cell.user_id])
            
                if not comment[0][0]:
                    await message.reply('Заметки нет')
                else:    
                    await message.reply(''.join(('*Заметка:* ', comment[0][0])), parse_mode="Markdown")

            except Exception as e:
                await message.reply("❌ Ошибка")

async def del_comment(message: types.Message):
    if not hasattr(message.reply_to_message, 'message_id'):
        _text = '❌ Для удаления заметки у пользователя ответьте не его любое сообщение ' \
            'в группе используя эту команду'
        await message.reply(_text)
        return
    try:
        user_message = await db.get_message(message.reply_to_message.message_id)
        await db.del_comment(user_message[message_cell.user_id])
        await message.reply("✅ Готово")
    except Exception as e:
        await message.reply("❌ Ошибка")

async def howto(message: types.Message):
    with open('как пользоваться.html', 'rb') as html_file:
        await message.answer_document(
            html_file,
            caption="Нажмите что бы прочитать как работать с ботом"
        )

async def commands(message: types.Message):
    text = '/история (+свайп)\n'\
        '/сессия (+свайп)\n'\
        '\n\n'\
        '/удалить (+свайп) - свое сообщение\n'\
        '\n\n'\
        '/заметка (+свайп) - посмотреть заметку\n'\
        '/заметка _текст заметки_ (+свайп) - добавить\n'\
        '/удалить_заметку (+свайп)\n'\
        '\n\n'\
        '/вчс (+свайп) - в черный список\n'\
        '/изчс (+свайп) - из черного списка\n'\
        '/чс /bl - посмотреть черный список\n\n'\
        '\n\n'\
        '/оцените (+свайп) - отправить \"оцените нашу работу\"\n\n'\
        '/товары (/products)\n/правила (/faq)\n\n'\
        '/tech - тех. ком.'

    await message.reply(text, parse_mode=MD)

async def inline_commands(query: types.InlineQuery):
     
    results = [
        # Пример инлайн варианта - текстовое сообщение
        types.InlineQueryResultArticle(
            id='1',  # Уникальный идентификатор для каждого варианта ответа
            title='История',  # Заголовок варианта ответа
            input_message_content=types.InputTextMessageContent(
                message_text='/история'
            ),
            description='+Свайп по сообщению покупателя! Вся история переписки.',
            thumb_url='https://ibb.co/jL41TLG'
        ),
        types.InlineQueryResultArticle(
            id='2',  # Уникальный идентификатор для каждого варианта ответа
            title='Сессия',  # Заголовок варианта ответа
            input_message_content=types.InputTextMessageContent(
                message_text='/Сессия'
            ),
            description='+Свайп по сообщению покупателя! Посмотреть последние сообщения.'
        ),
        types.InlineQueryResultArticle(
            id='3',
            title='Удалить',
            input_message_content=types.InputTextMessageContent(
                message_text='/удалить'
            ),
            description='+Свайп! Удалить (Ваше) отправленное сообщение у покупателя.'
        ),
        types.InlineQueryResultArticle(
            id='4',
            title='Предложить оценить работу',
            input_message_content=types.InputTextMessageContent(
                message_text='/оцените'
            ),
            description='+Свайп! Отправить предложение оценить нашу работу.'
        ),
        types.InlineQueryResultArticle(
            id='5',
            title='Посмотреть заметку',
            input_message_content=types.InputTextMessageContent(
                message_text='/заметка'
            ),
            description='+Свайп! Посмотреть заметку по покупателю.'
        ),
        types.InlineQueryResultArticle(
            id='6',
            title='Добавить заметку',
            input_message_content=types.InputTextMessageContent(
                message_text='/заметка '
            ),
            description='+Свайп! Текст заметки через пробел после команды этим же сообщением.'
        ),
        types.InlineQueryResultArticle(
            id='7',
            title='Удалить заметку',
            input_message_content=types.InputTextMessageContent(
                message_text='/удалить_заметку'
            ),
            description='+Свайп!'    
        ),
        types.InlineQueryResultArticle(
            id='8',
            title='В черный список',
            input_message_content=types.InputTextMessageContent(
                message_text='/вчс'
            ),
            description='+Свайп!'    

        ),
        types.InlineQueryResultArticle(
            id='9',
            title='Удалить из черного списка',
            input_message_content=types.InputTextMessageContent(
                message_text='/изчс'
            ),
            description='+Свайп!'
        ),
        types.InlineQueryResultArticle(
            id='10',
            title='Посмотреть черный список',
            input_message_content=types.InputTextMessageContent(
                message_text='/чс'
            ),
            description='Посмотреть черный список. Свайп не нужен.'
        )
    ]

    await query.answer(results)

class add_autoresponce_states(StatesGroup):
    waiting_for_keyword = State()
    waiting_for_text = State()
    waiting_for_photo = State()
    waiting_for_confirmation = State()

async def add_autoresponce_start(message: types.Message):
    if message.chat.id == group_chat_id:
        text = 'Управление автоответчиком доступно только ' \
            '*через личку бота* (пользователям состоящим в данной группе).'
        await message.reply(text, parse_mode=MD)
        return False
    control_key = types.InlineKeyboardMarkup()
    control_key.add(
        types.InlineKeyboardButton(
            text="Инфо",
            callback_data=f"_add_autoresponce_info")
        )
    control_key.add(
        types.InlineKeyboardButton(
            text="Отмена",
            callback_data=f"_add_autoresponce_cancel")
        )
    await message.answer("Отправьте ключевое слово для автоответа:", reply_markup=control_key)
    await add_autoresponce_states.waiting_for_keyword.set()

async def add_autoresponce_got_keyword(message: types.Message, state: FSMContext):
    control_key = types.InlineKeyboardMarkup()
    control_key.add(
        types.InlineKeyboardButton(
            text="Отмена",
            callback_data=f"_add_autoresponce_cancel")
        )
    await message.answer("Отлично! Теперь введите текст ответа:", reply_markup=control_key)
    await add_autoresponce_states.waiting_for_text.set()
    async with state.proxy() as data:
        data['keyword'] = message.text

async def add_autoresponce_got_text(message: types.Message, state: FSMContext):
    control_key = types.InlineKeyboardMarkup()
    control_key.add(
        types.InlineKeyboardButton(
            text="Без фото",
            callback_data=f"_add_autoresponce_no_photo")
        )
    control_key.add(
        types.InlineKeyboardButton(
            text="Отмена",
            callback_data=f"_add_autoresponce_cancel")
    )
    await message.answer(
        "Теперь пришлите картинку к ответу _(необязательно)_:",
        parse_mode=MD,
        reply_markup=control_key
        )
    await add_autoresponce_states.waiting_for_photo.set()
    async with state.proxy() as data:
        data['text'] = message.text

async def add_autoresponce_got_photo(message: types.Message, state: FSMContext):  
    control_key = types.InlineKeyboardMarkup()
    control_key.add(
        types.InlineKeyboardButton(
            text="Сохранить",
            callback_data="_add_autoresponce_save")
        )
    control_key.add(
        types.InlineKeyboardButton(
            text="Сбросить",
            callback_data="_add_autoresponce_cancel")
    )

    async with state.proxy() as data:
        data['photo'] = message.photo[-1].file_id
        await message.answer(f"Проверьте автоответ на ключевое слово {data['keyword']}:")
        await message.answer_photo(
            photo=data['photo'],
            caption=data['text'],
            parse_mode=MD,
            reply_markup=control_key
        )
 
    await add_autoresponce_states.waiting_for_confirmation.set()

async def add_autoresponce_no_photo(callback_query: types.CallbackQuery, state: FSMContext):
    control_key = types.InlineKeyboardMarkup()
    control_key.add(
        types.InlineKeyboardButton(
            text="Сохранить",
            callback_data="_add_autoresponce_save")
        )
    control_key.add(
        types.InlineKeyboardButton(
            text="Сбросить",
            callback_data="_add_autoresponce_cancel")
    )
    async with state.proxy() as data:
        await callback_query.message.answer(f"Подтвердите автоответ на ключевое слово \'{data['keyword']}\':")
        await callback_query.bot.send_message(
            text=data['text'],
            chat_id=callback_query.message.chat.id,
            reply_markup=control_key
        )
        data['photo'] = None
    await add_autoresponce_states.waiting_for_confirmation.set()

async def add_autoresponce_got_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        try:
            ok = await db.add_autoresponce(data['keyword'], data['text'], data['photo'])
            await callback_query.message.answer('✅ Сохранено!' if ok else '❌ Ошибка')
        except Exception as e:
            await callback_query.message.answer('❌ Ошибка')
    await state.finish()

async def add_autoresponce_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("Добавление автоответа отменено.")
    await state.finish()

async def add_autoresponce_info(cb: types.CallbackQuery, state: FSMContext):
    # "_add_autoresponce_info"
    text = 'Автоответчик распознает слова с ошибками или опечатками.'\
        '\nОтвет будет отправлен покупателю вместо перессылки '\
        'сообщения в группу.\nКлючевое слово может быть словосочетанием.'
    await cb.message.answer(text)

async def del_autoresponce(message: types.Message):
    cmd = message.text.split(' ')[0]
    key = message.text.replace(cmd, '')
    if not key:
        _text = '❌ Для удаления автоответа напишите его ключевое слово' \
        'через пробел после команды '
        await message.reply(_text)
        return

    try:
        key = message.text.split(' ')[1]
        ok = await db.del_autoresponce(key)
        text = f'Автоответ на слово \'{key}\' удален' if ok else "❌ Ошибка"
        await message.reply(text)
    except Exception as e:
        await message.reply("❌ Ошибка")

class add_prod_states(StatesGroup):
    waiting_for_name = State()
    waiting_for_info = State()
    waiting_for_price = State()
    waiting_for_photo = State()
    waiting_for_confirmation = State()

async def add_prod_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("Добавление товара отменено.")
    await state.finish()

async def add_prod_info(cb: types.CallbackQuery):
    text = 'Непарные символы форматирования (*, _, ~, и т.д.) записывайте через \"\\\"\n'\
    'Например: \\* Размеры: Ø30 х h34 мм.'\
    '\n\nПарные символы — форматируют текст между ними (жирный, курсивный, подчеркнутый).\n\n'\
    'Новый товар с идентичным названием удалит старый.\n\n'\
    'Описание длиной не более 200 символов.\n\n'
    'Фото отправляйте со сжатием — не файлом.'
    await cb.message.answer(text)

async def add_prod_start(message: types.Message):
    if message.chat.id == group_chat_id:
        text = 'Управление товарами доступно только ' \
            '*через личку бота* (пользователям состоящим в данной группе).'
        await message.reply(text, parse_mode=MD)
        return False
    control_key = types.InlineKeyboardMarkup()
    control_key.add(
        types.InlineKeyboardButton(
            text="!!! Прочтите !!!",
            callback_data="_add_prod_info")
        )
    control_key.add(
        types.InlineKeyboardButton(
            text="Отмена",
            callback_data="_add_prod_cancel")
        )
    await message.answer("Напишите название товара:", reply_markup=control_key)
    await add_prod_states.waiting_for_name.set()

async def get_prods(message: types.Message):
    prods = await db.get_products()

    if not prods:
        await message.reply('Список товаров пуст')
        return

    # отправляем каждый товар.
    # описание запршивается по инлайн кнопке -> во всплывающем окне
    for prod in prods:

        name_formatted = f'*{prod[prod_cell.name]}*'
        text = '\n'.join((name_formatted, prod[prod_cell.price]))
        
        info_key = types.InlineKeyboardMarkup()
        info_key.add(
            types.InlineKeyboardButton(
            text="Описание",
            callback_data=f"_prod_info:{prod[prod_cell.id]}")
        )
    
        await message.answer_photo(
            photo=prod[prod_cell.photo],
            caption=text,
            parse_mode=MD,
            reply_markup=info_key,
        )

async def prod_info(cb: types.CallbackQuery):
    try:
        prod = await db.get_product(cb.data.split(':')[1])

        print(prod[0][2])
        await cb.answer(
            text=prod[0][2].replace('\\', ''),
            show_alert=True,
        )
    except Exception as e:
        print(e)

async def del_prod(message: types.Message):
    if len(message.text.split(' ')) < 2:
        text = 'Для удаления напишите название товара'\
            ' через пробел после команды'
        await message.reply(text)
        return
    try:
        cmd = message.text.split(' ')[0]
        prod = message.text.replace(cmd, '').strip()
        ok = await db.del_product(prod)
        text = f'✅ Товар \'{prod}\' удален' if ok else "❌ Ошибка"
        await message.reply(text)
    except Exception as e:
        await message.reply("❌ Ошибка")

async def add_prod_got_name(message: types.Message, state: FSMContext):
    control_key = types.InlineKeyboardMarkup()
    control_key.add(
        types.InlineKeyboardButton(
            text="Отмена",
            callback_data=f"_add_prod_cancel")
        )
    await message.answer("Отлично! Теперь напишите описание:", reply_markup=control_key)
    await add_prod_states.waiting_for_info.set()
    async with state.proxy() as data:
        data['name'] = message.text

async def add_prod_got_info(message: types.Message, state: FSMContext):
    control_key = types.InlineKeyboardMarkup()
    control_key.add(
        types.InlineKeyboardButton(
            text="Отмена",
            callback_data=f"_add_prod_cancel")
    )
    await message.answer(
        "Теперь напишите цену товара (текстом, например 38 ₽/кг):",
        parse_mode=MD,
        reply_markup=control_key
        )
    await add_prod_states.waiting_for_price.set()
    async with state.proxy() as data:
        data['info'] = message.text

async def add_prod_got_price(message: types.Message, state: FSMContext):
    control_key = types.InlineKeyboardMarkup()
    control_key.add(
        types.InlineKeyboardButton(
            text="Отмена",
            callback_data=f"_add_prod_cancel")
        )
    await message.answer("Отлично! Теперь пришлите фото товара:", reply_markup=control_key)
    await add_prod_states.waiting_for_photo.set()
    async with state.proxy() as data:
        data['price'] = message.text

async def add_prod_got_photo(message: types.Message, state: FSMContext):  
    control_key = types.InlineKeyboardMarkup()
    control_key.add(
        types.InlineKeyboardButton(
            text="Сохранить",
            callback_data="_add_prod_save")
        )
    control_key.add(
        types.InlineKeyboardButton(
            text="Сбросить",
            callback_data="_add_prod_cancel")
    )

    async with state.proxy() as data:
        data['photo'] = message.photo[-1].file_id

        name = data['name']
        info = data['info']
        price = data['price']
        text = '\n\n'.join((f'*{name}*', info, price))

        await message.answer('Подтвердите добавление товара:')
        await message.answer_photo(
            photo=data['photo'],
            caption=text,
            parse_mode=MD,
            reply_markup=control_key
        )
        # return
        #     chat_id=message.chat.id,
        #     photo=data['photo'],
        #     caption='\n\n'.join((f'*{name}*', info, price)),
        #     reply_markup=control_key,
        #     parse_mode=MD
        # )

    await add_prod_states.waiting_for_confirmation.set()

async def add_prod_got_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        try:
            ok = await db.add_product(data['name'], data['info'], data['price'], data['photo'])
            await callback_query.message.answer('✅ Сохранено!' if ok else '❌ Ошибка')
        except Exception as e:
            await callback_query.message.answer('❌ Ошибка')
    await state.finish()

# ======================================================================== #
# ======================================================================== #

async def get_photo(message: types.Message):

    if not hasattr(message, 'text'):
        await message.reply('Запрос фото: Ошибка.')
    
    if len(message.text.split(':')) > 0:
        try:
            await message.bot.send_photo(message.chat.id, photo=message.text.split(':')[1])
        except Exception as e:
            await message.reply('Запрос фото: Ошибка отправки.')
    else:
        await message.reply('Запрос фото: ❌ Ошибка')

async def get_animation(message: types.Message):
    if not hasattr(message, 'text'):
        await message.reply('Запрос анимации: Ошибка.')
    
    if len(message.text.split(':')) > 0:
        try:
            await message.bot.send_animation(message.chat.id, message.text.split(':')[1])
        except Exception as e:
            await message.reply('Запрос анимации: Ошибка отправки.')
    else:
        await message.reply('Запрос анимации: Ошибка идентификатора.')

async def get_audio(message: types.Message):
    if not hasattr(message, 'text'):
        await message.reply('Запрос аудио: Ошибка.')
    
    if len(message.text.split(':')) > 0:
        try:
            await message.bot.send_audio(message.chat.id, message.text.split(':')[1])
        except Exception as e:
            await message.reply('Запрос аудио: Ошибка отправки.')
    else:
        await message.reply('Запрос аудио: Ошибка идентификатора.')

async def get_document(message: types.Message):
    if not hasattr(message, 'text'):
        await message.reply('Запрос документа: Ошибка.')
    
    if len(message.text.split(':')) > 0:
        try:
            await message.bot.send_document(message.chat.id, message.text.split(':')[1])
        except Exception as e:
            await message.reply('Запрос документа: Ошибка отправки.')
    else:
        await message.reply('Запрос документа: Ошибка идентификатора.')

async def get_sticker(message: types.Message):
    func = 'стикера'
    if not hasattr(message, 'text'):
        await message.reply(f'Запрос {func}: Ошибка.')
    
    if len(message.text.split(':')) > 0:
        try:
            await message.bot.send_sticker(message.chat.id, message.text.split(':')[1])
        except Exception as e:
            await message.reply(f'Запрос {func}: Ошибка отправки.')
    else:
        await message.reply(f'Запрос {func}: Ошибка идентификатора.')

async def get_video(message: types.Message):
    func = 'видео'
    if not hasattr(message, 'text'):
        await message.reply(f'Запрос {func}: Ошибка.')
    
    if len(message.text.split(':')) > 0:
        try:
            await message.bot.send_video(message.chat.id, message.text.split(':')[1])
        except Exception as e:
            await message.reply(f'Запрос {func}: Ошибка отправки.')
    else:
        await message.reply(f'Запрос {func}: Ошибка идентификатора.')

async def get_voice(message: types.Message):
    func = 'голоса'
    if not hasattr(message, 'text'):
        await message.reply(f'Запрос {func}: Ошибка.')
    
    if len(message.text.split(':')) > 0:
        try:
            await message.bot.send_voice(message.chat.id, message.text.split(':')[1])
        except Exception as e:
            await message.reply(f'Запрос {func}: Ошибка отправки.')
    else:
        await message.reply(f'Запрос {func}: Ошибка идентификатора.')

async def get_contact(message: types.Message):
    func = 'контакта'
    if not hasattr(message, 'text'):
        await message.reply(f'Запрос {func}: Ошибка.')
    
    if len(message.text.split(':')) > 0:
        try:
            # сначала берем данные из БД
            data_json = await db.get_contact(message.text.split(':')[1])
            data_dict = json.loads(data_json)
            await message.bot.send_contact(message.chat.id, **data_dict['contact'])

        except Exception as e:
            await message.reply(f'Запрос {func}: Ошибка отправки.')
    else:
        await message.reply(f'Запрос {func}: Ошибка идентификатора.')

async def get_location(message: types.Message):
    func = 'локации'
    if not hasattr(message, 'text'):
        await message.reply(f'Запрос {func}: Ошибка.')
    
    if len(message.text.split(':')) > 0:
        try:
            # сначала берем данные из БД
            data_json = await db.get_location(message.text.split(':')[1])
            data_dict = json.loads(data_json)
            await message.bot.send_location(message.chat.id, **data_dict['contact'])

        except Exception as e:
            await message.reply(f'Запрос {func}: Ошибка отправки.')
    else:
        await message.reply(f'Запрос {func}: Ошибка идентификатора.')

async def get_invoice(message: types.Message):
    func = 'инвойса'
    if not hasattr(message, 'text'):
        await message.reply(f'Запрос {func}: Ошибка.')
    
    if len(message.text.split(':')) > 0:
        try:
            # сначала берем данные из БД
            data_json = await db.get_invoice(message.text.split(':')[1])
            data_dict = json.loads(data_json)
            await message.bot.send_invoice(message.chat.id, **data_dict['contact'])

        except Exception as e:
            await message.reply(f'Запрос {func}: Ошибка отправки.')
    else:
        await message.reply(f'Запрос {func}: Ошибка идентификатора.')

async def get_successful_payment(message: types.Message):
    func = 'успешного платежа'
    if not hasattr(message, 'text'):
        await message.reply(f'Запрос {func}: Ошибка.')
    
    if len(message.text.split(':')) > 0:
        try:
            # сначала берем данные из БД
            data_json = await db.get_successful_payment(message.text.split(':')[1])
            data_dict = json.loads(data_json)
            successful_payment = types.SuccessfulPayment(**data_dict)

            # Формируем многострочную строку с информацией о платеже
            message_text = f'Информация о платеже:\n' \
            f'Сумма: {successful_payment.total_amount} {successful_payment.currency}\n'\
            f'Дата: {successful_payment.invoice_payload}\n'\
            f'Идентификатор платежа: {successful_payment.invoice_payload}\n'\
            f'Идентификатор выбранного способа доставки: {successful_payment.shipping_option_id}\n'\
            f'Информация о заказе: {successful_payment.order_info}'\
            f'Идентификатор платежа в Telegram: {successful_payment.telegram_payment_charge_id}'\
            f'Идентификатор платежа провайдера: {successful_payment.provider_payment_charge_id}'
            await message.answer(message_text)

        except Exception as e:
            await message.reply(f'Запрос {func}: Ошибка отправки.')
    else:
        await message.reply(f'Запрос {func}: Ошибка идентификатора.')

async def get_passport(message: types.Message):
    func = 'паспорта'
    if not hasattr(message, 'text'):
        await message.reply(f'Запрос {func}: Ошибка.')
    
    if len(message.text.split(':')) > 0:
        try:
            # сначала берем данные из БД
            data_json = await db.get_passport(message.text.split(':')[1])
            data_dict = json.loads(data_json)
            passport_data = types.PassportData(**data_dict)

            message_text = ''
            # Обрабатываем каждый элемент PassportData
            for element in passport_data.data:
                element_type = element.type
                
                if element_type == "personal_details":
                    message_text += "Тип элемента: Персональные данные\n"
                    message_text += f"Имя: {element.data.get('first_name', '')}\n"
                    message_text += f"Фамилия: {element.data.get('last_name', '')}\n"

                elif element_type == "passport":
                    message_text += "Тип элемента: Паспорт\n"
                    message_text += f"Номер паспорта: {element.data.get('passport_number', '')}\n"
                    message_text += f"Дата рождения: {element.data.get('date_of_birth', '')}\n"

                elif element_type == "driver_license":
                    message_text += "Тип элемента: Водительское удостоверение\n"
                    message_text += f"Номер водительского удостоверения: {element.data.get('number', '')}\n"
                    message_text += f"Дата выдачи: {element.data.get('date_of_issue', '')}\n"

                elif element_type == "identity_card":
                    message_text += "Тип элемента: Удостоверение личности\n"
                    message_text += f"Номер удостоверения личности: {element.data.get('number', '')}\n"

                elif element_type == "internal_passport":
                    message_text += "Тип элемента: Внутренний паспорт\n"
                    message_text += f"Номер внутреннего паспорта: {element.data.get('number', '')}\n"

                elif element_type == "address":
                    message_text += "Тип элемента: Адрес\n"
                    message_text += f"Страна: {element.data.get('country', '')}\n"
                    message_text += f"Город: {element.data.get('city', '')}\n"
                    message_text += f"Улица: {element.data.get('street', '')}\n"

                elif element_type == "utility_bill":
                    message_text += "Тип элемента: Квитанция за коммунальные услуги\n"
                    message_text += f"Номер квитанции: {element.data.get('utility_bill_number', '')}\n"

                elif element_type == "bank_statement":
                    message_text += "Тип элемента: Выписка из банка\n"
                    message_text += f"Номер выписки: {element.data.get('bank_statement_number', '')}\n"

                elif element_type == "rental_agreement":
                    message_text += "Тип элемента: Договор аренды\n"
                    message_text += f"Номер договора аренды: {element.data.get('rental_agreement_number', '')}\n"

                elif element_type == "passport_registration":
                    message_text += "Тип элемента: Регистрация по паспорту\n"
                    message_text += f"Номер регистрации по паспорту: {element.data.get('registration_number', '')}\n"

                elif element_type == "temporary_registration":
                    message_text += "Тип элемента: Временная регистрация\n"
                    message_text += f"Номер временной регистрации: {element.data.get('registration_number', '')}\n"

                elif element_type == "phone_number":
                    message_text += "Тип элемента: Телефонный номер\n"
                    message_text += f"Номер телефона: {element.phone_number}\n"

                elif element_type == "email":
                    message_text += "Тип элемента: Email-адрес\n"
                    message_text += f"Email: {element.email}\n"
           
            await message.answer(message_text)

        except Exception as e:
            await message.reply(f'Запрос {func}: Ошибка отправки.')
    else:
        await message.reply(f'Запрос {func}: Ошибка идентификатора.')

# ======================================================================== #
# ======================================================================== #

async def kick(*agrs, **kwargs):
    return

async def text(ms: types.Message):
    info_key = types.InlineKeyboardMarkup()
    info_key.add(
        types.InlineKeyboardButton(
            text="текст",
            callback_data='_test'
        )
    )
    await ms.answer('Вот кнопка: ', reply_markup=info_key)

async def test(cb: types.CallbackQuery):
    text = 'Лёд Hoshizaki в форме куба производится'\
        ' на оригинальном Японском оборудовании.\nЭтот кубик — '\
        'основа любого бара, пользуется '\
        'популярностью по всему миру.\n\nМасса: 20 гр.\nРазмеры: 28х28х32 мм.'
    await cb.answer(text, show_alert=True)

def register_dialog_commands(dp: Dispatcher):
    dp.register_message_handler(
        kick,
        filters.in_blacklist,
        content_types=types.ContentType.all()
        # здесь так как эта регистрация самая первая.
    )
    dp.register_callback_query_handler(
        kick,
        filters.in_blacklist_cb
    )
    dp.register_message_handler(
        add_autoresponce_got_keyword,
        filters.admin_ls,
        state=add_autoresponce_states.waiting_for_keyword
    )
    dp.register_message_handler(
        add_autoresponce_got_text,
        filters.admin_ls,
        state=add_autoresponce_states.waiting_for_text
    )
    dp.register_message_handler(
        add_autoresponce_got_photo,
        filters.admin_ls,
        state=add_autoresponce_states.waiting_for_photo,
        content_types=types.ContentType.PHOTO
    )
    dp.register_callback_query_handler(
        add_autoresponce_no_photo,
        lambda query: query.data == "_add_autoresponce_no_photo",
        filters.callback_admin_ls,
        state=add_autoresponce_states.waiting_for_photo,
    )
    dp.register_callback_query_handler(
        add_autoresponce_got_confirmation,
        lambda query: query.data == "_add_autoresponce_save",
        filters.callback_admin_ls,
        state=add_autoresponce_states.waiting_for_confirmation
    )
    dp.register_callback_query_handler(
        add_autoresponce_cancel,
        lambda query: query.data == "_add_autoresponce_cancel",
        filters.callback_admin_ls,
        state=add_autoresponce_states.all_states
    )
    dp.register_callback_query_handler(
        add_autoresponce_info,
        lambda query: query.data == "_add_autoresponce_info",
        filters.callback_admin_ls,
        state=add_autoresponce_states.all_states
    )
    # ======================PRODUCT==================================
    dp.register_callback_query_handler(
        add_prod_cancel,
        lambda query: query.data == "_add_prod_cancel",
        filters.callback_admin_ls,
        state=add_prod_states.all_states
    )
    dp.register_message_handler(
        add_prod_got_name,
        filters.admin_ls,
        state=add_prod_states.waiting_for_name
    )
    dp.register_message_handler(
        add_prod_got_info,
        filters.admin_ls,
        state=add_prod_states.waiting_for_info
    )
    dp.register_message_handler(
        add_prod_got_price,
        filters.admin_ls,
        state=add_prod_states.waiting_for_price
    )
    dp.register_message_handler(
        add_prod_got_photo,
        filters.admin_ls,
        state=add_prod_states.waiting_for_photo,
        content_types=types.ContentType.PHOTO
    )
    dp.register_callback_query_handler(
        add_prod_got_confirmation,
        lambda query: query.data == "_add_prod_save",
        filters.callback_admin_ls,
        state=add_prod_states.waiting_for_confirmation
    )


def register_main_commands(dp: Dispatcher):
    dp.register_message_handler(
        text,
        lambda message: message.text.startswith('/test ')
    )
    dp.register_callback_query_handler(
        test,
        lambda query: query.data == '_test'
    )
    dp.register_message_handler(
        reply,
        filters.in_group,
        filters.is_not_cmd,
        content_types=types.ContentType.all()
    )
    dp.register_callback_query_handler(
        ignore_message,
        lambda query: query.message.chat.id == group_chat_id \
            and query.data.startswith("_Ignore:")
    )
    dp.register_message_handler(
        get_prods,
        commands=['товары', 'products', 'product', 'меню', 'menu']
    )
    dp.register_callback_query_handler(
        prod_info,
        lambda query: query.data.startswith('_prod_info:')
    )
    dp.register_message_handler(
        session_history,
        filters.session_cmd,
        filters.in_group
    )
    dp.register_message_handler(
        history,
        filters.history_cmd,
        filters.in_group
    )
    dp.register_message_handler(
        delete_message,
        filters.delete_cmd,
        filters.in_group
    )
    dp.register_message_handler(
        send_rate,
        filters.in_group,
        commands=['оцените', 'оценить', 'Оценить', 'Оцените', 'ОЦЕНИТЕ', 'ОЦЕНКА', 'оценка']
    )
    dp.register_message_handler(
        add_comment,
        filters.add_comment,
        filters.in_group
    )
    dp.register_message_handler(
        del_comment,
        filters.del_comment,
        filters.in_group
    )
    dp.register_message_handler(
        active_session,
        filters.active_session_cmd,
        filters.group_member,
        commands=['активныхсессий', 'активных_сессий']
    )
    dp.register_message_handler(
        message_count_per_day,
        filters.group_member,
        commands=['задень', 'засутки', 'perday']
    )
    dp.register_message_handler(
        add_to_blacklist, 
        filters.in_group,
        commands=['вчс']
    )
    dp.register_message_handler(
        get_blacklist,
        filters.group_member,
        commands=['blacklist', 'bl', 'чс', 'черныйсписок', 'черный_список']
    )
    dp.register_message_handler(
        execute_sql_query,
        filters.execute_sql_query,
        filters.group_member
    )
    dp.register_message_handler(
        remove_from_blacklist,
        filters.remove_from_blacklist_cmd,
        filters.group_member
    )
    dp.register_message_handler(
        add_autoresponce_start, 
        filters.admin_ls,
        commands=['добавить_автоответ', 'add_autoresponce', 'добавить_автоответчик']
    )
    dp.register_message_handler(
        get_autoresponces, 
        filters.group_member,
        commands=['автоответчик', 'autoresponce', 'autoresponces', 'автоответы']
    )
    dp.register_message_handler(
        del_autoresponce,
        filters.del_autoresponce_cmd,
        filters.group_member
    )

    dp.register_message_handler(
        add_prod_start, 
        filters.admin_ls,
        commands=['добавить_товар', 'add_product']
    )
    dp.register_message_handler(
        del_prod,
        filters.del_prod_cmd,
        filters.group_member
    )
    dp.register_callback_query_handler(
        add_prod_info,
        lambda query: query.data == "_add_prod_info",
        filters.callback_admin_ls
    )
    dp.register_message_handler(
        get_performance,
        filters.performance,
        filters.group_member
    )
    dp.register_message_handler(
        peak_performance,
        filters.group_member,
        commands=['пик_произвоительности', 'пикпроизводительности', 'peak_performance']
    )
    dp.register_message_handler(
        howto,
        filters.group_member,
        commands=['правила', 'как_пользоваться', 'как_работает', 'faq', 'howto']
    )
    dp.register_message_handler(
        commands,
        filters.group_member,
        commands=['команды', 'commands', 'кмд', 'cmd']
    )
    dp.register_inline_handler(
        inline_commands,
        filters.inline_group_member
        )
    
def register_dynamic_commands(dp: Dispatcher):
    # Динамические команды
    dp.register_message_handler(
        get_photo,
        filters.get_photo_cmd,
        filters.group_member
    )
    dp.register_message_handler(
        get_animation,
        filters.get_animation_cmd,
        filters.group_member
    )
    dp.register_message_handler(
        get_audio,
        filters.get_audio_cmd,
        filters.group_member
    )
    dp.register_message_handler(
        get_document,
        filters.get_document_cmd,
        filters.group_member
    )
    dp.register_message_handler(
        get_sticker,
        filters.get_sticker_cmd,
        filters.group_member
    )
    dp.register_message_handler(
        get_video,
        filters.get_video_cmd,
        filters.group_member
    )
    dp.register_message_handler(
        get_voice,
        filters.get_voice_cmd,
        filters.group_member
    )
    dp.register_message_handler(
        get_contact,
        filters.get_contact_cmd,
        filters.group_member
    )
    dp.register_message_handler(
        get_location,
        filters.get_location_cmd,
        filters.group_member
    )
    dp.register_message_handler(
        get_invoice,
        filters.get_invoice_cmd,
        filters.group_member
    )
    dp.register_message_handler(
        get_passport,
        filters.get_passport_cmd,
        filters.group_member
    )
