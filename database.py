import aiosqlite
import asyncio
from aiogram import types
import services
from config import DATABASE
from time import time

class message_cell():
    '''Используется в качестве Enum'''
    message_id = 0
    user_chat_message_id = 1
    user_id = 2
    chat_id = 3
    username = 4
    specialist_id = 5
    date = 6
    reply_to_message = 7
    edit_date = 8
    has_protected_content = 9
    text = 10
    animation = 11
    audio = 12
    document = 13
    photo = 14
    sticker = 15
    video = 16
    voice = 17
    contact = 18
    location = 19
    invoice = 20
    successful_payment = 21
    connected_website = 22
    passport_data = 23
    reply_markup = 24

class user_cell():
    '''Используется в качестве Enum'''
    user_id = 0
    first_name = 1
    fullname = 2
    username = 3
    orders  = 4
    active_session = 5
    session_start = 6
    date = 7
    comment = 8
class prod_cell():
    id = 0
    name = 1
    info = 2
    price = 3
    photo = 4

class Database:
    '''Необходимо запустить open() и при выключении завершить close()'''

    def __init__(self, database):
        self.__database = database
        self.__conn = None

    def __del__(self):
        pass

    async def open(self):
        if self.__conn is None:
            self.__conn = await aiosqlite.connect(self.__database)

        query = 'CREATE TABLE IF NOT EXISTS active_messages (' \
            'message_id INTEGER PRIMARY KEY, ' \
            'chat_id INTEGER, ' \
            'date INTEGER, ' \
            'callback_message_id INTEGER, ' \
            'reminds_id TEXT ' \
            ');' \

        query = 'CREATE TABLE IF NOT EXISTS sessions (' \
            'chat_id INTEGER PRIMARY KEY,' \
            'messages_id TEXT,' \
            'date INTEGER,' \
            'user_id INTEGER' \
            ');'

        service_query = 'CREATE TABLE IF NOT EXISTS service (' \
            'name TEXT PRIMARY KEY, '\
            'message TEXT' \
            ');'

        async with self.__conn.cursor() as cur:
            await cur.execute(service_query)
        await self.__conn.commit()

        products_query = 'CREATE TABLE IF NOT EXISTS products (' \
        'id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,' \
        'name TEXT UNIQUE NOT NULL, ' \
        'info TEXT NULL, ' \
        'price TEXT NOT NULL, ' \
        'photo TEXT NULL' \
        ');'

        async with self.__conn.cursor() as cur:
            await cur.execute(products_query)
        await self.__conn.commit()

        performance_query = 'CREATE TABLE IF NOT EXISTS performance (' \
            'timestamp INTEGER PRIMARY KEY, ' \
            'memory_used INETEGER, ' \
            'memory_total INTEGER, ' \
            'cpu_used REAL' \
            ');'

        async with self.__conn.cursor() as cur:
            await cur.execute(performance_query)
        await self.__conn.commit()

        autoresponces_query = 'CREATE TABLE IF NOT EXISTS autoresponces (' \
            'keyword TEXT PRIMARY KEY, ' \
            'responce TEXT NOT NULL, ' \
            'photo TEXT NULL' \
            ');'
        
        async with self.__conn.cursor() as cur:
            await cur.execute(autoresponces_query)
        await self.__conn.commit()

        blacklist_query = 'CREATE TABLE IF NOT EXISTS blacklist (' \
            'user_id INTEGER PRIMARY KEY' \
            ');'

        async with self.__conn.cursor() as cur:
            await cur.execute(blacklist_query)
        await self.__conn.commit()

        query = 'CREATE TABLE IF NOT EXISTS users (' \
            'user_id INTEGER PRIMARY KEY, ' \
            'first_name TEXT, '\
            'fullname TEXT NULL, '\
            'username TEXT NULL, '\
            'orders INTEGER NULL, ' \
            'active_session INTEGER NULL, ' \
            'session_start TEXT NULL, ' \
            'date INTEGER NULL, ' \
            'comment TEXT NULL' \
            ');'

        # username будет хранится в messages, и свежее username 
        # пользователя можно брать оттуда по user_id
        # аналогично с chat_id

        async with self.__conn.cursor() as cur:
            await cur.execute(query)
        await self.__conn.commit()

        query = 'CREATE TABLE IF NOT EXISTS messages ('\
        'message_id INTEGER PRIMARY KEY, '\
        'user_chat_message_id INTEGER NULL, '\
        'user_id INTEGER NULL, '\
        'chat_id INTEGER NULL, '\
        'username TEXT NULL, '\
        'specialist_id INTEGER NULL, '\
        'date INTEGER NULL, '\
        'reply_to_message INTEGER NULL, '\
        'edit_date INTEGER NULL, '\
        'has_protected_content INTEGER NULL, '\
        'text TEXT NULL, '\
        'animation INTEGER NULL, '\
        'audio INTEGER NULL, '\
        'document INTEGER NULL, '\
        'photo TEXT NULL, '\
        'sticker INTEGER NULL, '\
        'video INTEGER NULL, '\
        'voice INTEGER NULL, '\
        'contact TEXT NULL, '\
        'location TEXT NULL, '\
        'invoice TEXT NULL, '\
        'successful_payment TEXT NULL, '\
        'connected_website TEXT NULL, '\
        'passport_data TEXT NULL, '\
        'reply_markup TEXT NULL'\
        ');'
        # 'FOREIGN KEY (user_id) REFERENCES users (user_id)'\

        async with self.__conn.cursor() as cur:
            await cur.execute(query)
            await self.__conn.commit()

    async def reconnect(self):
        new_connection = await aiosqlite.connect(self.__database)
        old_connection = self.__conn
        self.__conn = new_connection
        await old_connection.close()

    async def add_delivery_message(self, message: str):
        query = 'INSERT OR REPLACE INTO service (message)'\
        'VALUES ? WHERE name = delivery_message;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query, message)
                    await self.__conn.commit()
                except aiosqlite.Error as e:
                    print(f"Ошибка aiosqlite: {e}")
    
    async def get_delivery_message(self):
        query = 'SELECT message FROM service '\
            'WHERE name = delivery_message ;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query)
                    message = await cur.fetchall()
                    return message
                except Exception as e:
                    return False

    async def add_pickup_message(self, message: str):
        query = 'INSERT OR REPLACE INTO service (message)'\
        'VALUES ? WHERE name = pickup_message;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query, message)
                    await self.__conn.commit()
                except aiosqlite.Error as e:
                    print(f"Ошибка aiosqlite: {e}")
    
    async def get_pickup_message(self):
        query = 'SELECT message FROM service '\
            'WHERE name = pickup_message ;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query)
                    message = await cur.fetchall()
                    return message
                except Exception as e:
                    return False

    async def add_quantity_message(self, message: str):
        query = 'INSERT OR REPLACE INTO service (message)'\
        'VALUES ? WHERE name = quantity_message;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query, message)
                    await self.__conn.commit()
                except aiosqlite.Error as e:
                    print(f"Ошибка aiosqlite: {e}")
    
    async def get_quantity_message(self):
        query = 'SELECT message FROM service '\
            'WHERE name = quantity_message ;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query)
                    message = await cur.fetchall()
                    return message
                except Exception as e:
                    return False

    async def add_container_message(self, message: str):
        query = 'INSERT OR REPLACE INTO service (message)'\
        'VALUES ? WHERE name = container_message;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query, message)
                    await self.__conn.commit()
                except aiosqlite.Error as e:
                    print(f"Ошибка aiosqlite: {e}")
    
    async def get_container_message(self):
        query = 'SELECT message FROM service '\
            'WHERE name = container_message ;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query)
                    message = await cur.fetchall()
                    return message
                except Exception as e:
                    return False

    async def write_performance(self, memory_used: int, memory_total: int, cpu_used: float):
        query = 'INSERT OR IGNORE INTO performance (' \
            'timestamp, ' \
            'memory_used, ' \
            'memory_total, ' \
            'cpu_used' \
            ') VALUES (?, ?, ?, ?);'
        
        values = (
            int(time()),
            memory_used,
            memory_total,
            cpu_used
        )

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                await cur.execute(query, values)
                await self.__conn.commit()

    async def get_performance(self, limit=1000):
        query = 'SELECT * FROM performance ' \
            'ORDER BY timestamp DESC LIMIT ?;'
        
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query, (limit,))
                perf = await cur.fetchall()
                return perf
            
    async def peak_performance(self):
        query = 'SELECT * FROM performance '\
        'WHERE timestamp >= strftime(\'%s\', \'now\', \'-7 days\')'\
        'AND (memory_used = (SELECT MAX(memory_used) '\
        'FROM performance WHERE timestamp >= strftime(\'%s\', \'now\', \'-7 days\'))'\
        'OR cpu_used = (SELECT MAX(cpu_used) FROM performance '\
        'WHERE timestamp >= strftime(\'%s\', \'now\', \'-7 days\')))'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query)
                perf = await cur.fetchall()
                return perf

    async def close(self):
        if type(self.__conn) == aiosqlite.Connection:
            await self.__conn.close()

    async def close_session(self, user_id):
        query = 'UPDATE users '\
            'SET active_session = ?'\
            ' WHERE user_id = ?;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                await cur.execute(query, (False, user_id))
                await self.__conn.commit()

        chat_id = next(
            (_chat_id for _chat_id, data in services.sessions.items()
            if data['user_id'] == user_id),
            None
        )
        del services.sessions[chat_id]

    async def check_user(self, message: types.Message):
        '''Добавляем юзера если такого нет'''

        values = (
            # user_id
            message.from_id,
            message.from_user.first_name,
            message.from_user.full_name,
            message.from_user.username,
            0,
            int(message.date.timestamp()),
            message.from_id
        )

        query = 'INSERT INTO users (' \
            'user_id,' \
            'first_name,' \
            'fullname,' \
            'username,' \
            'orders, ' \
            'date) ' \
            'SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS ' \
            '(SELECT 1 FROM users WHERE user_id = ?);'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                await cur.execute(query, values)
                await self.__conn.commit()

    async def open_session(self, chat_id: int, user_id: int, session_start: int):
        query = 'UPDATE users '\
            'SET active_session = ?, '\
            'session_start = ? '\
            'WHERE user_id = ?'
        values = (True, session_start, user_id)

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                await cur.execute(query, values)
                await self.__conn.commit()

    async def update_user(self, message: types.Message):
        '''Перезаписываем данные пользователя! Кроме кол-ва заказов и сессии'''        

        values = (
            # user_id
            message.from_id,
            message.from_user.first_name,
            message.from_user.full_name,
            message.from_user.username
        )
        query = 'INSERT OR REPLACE INTO users (' \
            'user_id,' \
            'first_name,' \
            'fullname,' \
            'username)' \
            'VALUES (?, ?, ?, ?);'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                await cur.execute(query, values)
                await self.__conn.commit()

    async def write_message(self, message: types.Message, 
                            client: bool, client_chat_id: int = None,
                            group_message_id = None, client_chat_message_id=None):
        '''
        При записи сообщения специалиста user_chat_id берется из списка активных сообщений,
        в случае отсутствия активного сообщения необходимо передать дополнительно user_chat_id
        '''

        if client and group_message_id is None:
            raise

        values = (
            # айди сообщения в группе
            group_message_id if client else message.message_id,
            # айди сообщения специалиста в чате пользователя (необходимо для удаления сообщений специалистом) 
            client_chat_message_id if not client else None,
            # айди клиента
            message.from_id if client else None,
            # айди чата клиента
            message.chat.id 
            if client 
            else services.active_messages.get(message.reply_to_message.message_id, {}).get('chat_id', client_chat_id) \
                if hasattr(services.active_messages, str(message.reply_to_message.message_id))
                else client_chat_id,
            # никнейм отправителя сообщения
            message.from_user.username if message.from_user.username else None,
            # айди специалиста
            message.from_id if not client else None,
            # время сообщения
            int(message.date.timestamp()),
            # сообщение на которое был ответ специалиста
            message.reply_to_message.message_id if not client and hasattr(message.reply_to_message, 'message_id') else None,
            # время исправления
            message.edit_date if message.edit_date else None,
            # имеет ли защиту
            message.has_protected_content if message.has_protected_content else None,
            # текст сообщения
            message.text if message.text else None,
            message.animation.file_id if message.animation else None,
            message.audio.file_id if message.audio else None,
            message.document.file_id if message.document else None,
            # каждое фото шлется отдельным сообщением
            message.photo[-1].file_id if message.photo else None,
            # message.photo.pop().file_id if message.photo else None,
            message.sticker.file_id if message.sticker else None,
            message.video.file_id if message.video else None,
            message.voice.file_id if message.voice else None,
            message.contact.as_json() if message.contact else None,
            message.location.as_json() if message.location else None,
            message.invoice.as_json() if message.invoice else None,
            message.successful_payment.as_json() if message.successful_payment else None, 
            # order_info не поддерживается в aiogram
            # shipping_address не поддерживается в aiogram
            # telegram_payment_charge_id не поддерживается
            # provider_payment_charge_id не поддерживается
            message.connected_website if message.connected_website else None,
            message.passport_data.as_json() if message.passport_data else None,
            message.reply_markup.as_json() if message.reply_markup else None
        )

        query = 'INSERT OR IGNORE INTO messages (' \
            'message_id, ' \
            'user_chat_message_id, ' \
            'user_id, ' \
            'chat_id, ' \
            'username, ' \
            'specialist_id, ' \
            'date, ' \
            'reply_to_message, ' \
            'edit_date, ' \
            'has_protected_content, ' \
            'text, ' \
            'animation, ' \
            'audio, ' \
            'document, ' \
            'photo, ' \
            'sticker, ' \
            'video, ' \
            'voice, ' \
            'contact, ' \
            'location, ' \
            'invoice, ' \
            'successful_payment, ' \
            'connected_website, ' \
            'passport_data, ' \
            'reply_markup ' \
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,' \
            ' ?, ?, ?, ?, ?, ?, ?)'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query, values)
                    await self.__conn.commit()
                except aiosqlite.Error as e:
                    print(f"Ошибка aiosqlite: {e}")

    async def get_message(self, message_id: int):

        query = 'SELECT * FROM messages'\
            f' WHERE message_id = ?;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query, (message_id,))
                    message = await cur.fetchall()
                    return message[0]
                except Exception as e:
                    return False

    async def get_history(self, chat_id: int):

        query = 'SELECT * FROM messages'\
            f' WHERE chat_id = ?;'
                
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query, (chat_id,))
                messages = await cur.fetchall()
                return messages

    async def get_session(self, chat_id: int):
        '''
        1. Достаем session_start из users.
        2. Достаем все из messages до session_start
        '''
        query = 'SELECT session_start FROM users'\
            f' WHERE user_id = ?;'
        
        session_start = None

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query, (chat_id,))
                session_start = await cur.fetchall()

        query = 'SELECT * FROM messages'\
            f' WHERE chat_id = ?'\
            f' AND date > ?'

        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query, (chat_id, session_start[0][0]))
                    messages = await cur.fetchall()
                    return messages
                except Exception as e:
                    return False

    async def get_user(self, user_id: int):
        
        query = 'SELECT * FROM users'\
            f' WHERE user_id = ?;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query, (user_id,))
                user = await cur.fetchall()
                return user

    async def message_per_day(self):
        
        # таймштамп сутки назад
        day = time() - (24 * 60 * 60)
        # если нету айди специалиста значит это сообщение пользователя
        query = 'SELECT COUNT(*) FROM messages '\
            f'WHERE date < ? AND specialist_id IS NULL;'
        
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query, (day,))
                count = await cur.fetchall()
                return count

    async def add_to_blacklist(self, user_id: int):
        query = 'INSERT OR IGNORE INTO blacklist (user_id) VALUES (?);'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                await cur.execute(query, (user_id,))
                await self.__conn.commit()
        
        services.blacklist.append(user_id)

    async def get_blacklist(self):
        query = 'SELECT u.user_id, u.first_name, u.fullname, u.username ' \
            'FROM users u ' \
            'INNER JOIN blacklist b ON u.user_id = b.user_id; '

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query)
                blacklist = await cur.fetchall()
                return blacklist

    async def add_comment(self, user_id: int, text: str):
        '''Записывает чистый текст комментария без обработки'''

        query = 'UPDATE users SET comment = ? WHERE user_id = ?;'
        
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                await cur.execute(query, (text, user_id))
                await self.__conn.commit()
    
    async def get_comment(self, user_id):
        query = 'SELECT comment FROM users WHERE user_id = ?;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query, (user_id,))
                comment = await cur.fetchall()
                return comment

    async def del_comment(self, user_id):
        query = 'UPDATE users SET comment=NULL WHERE user_id = ?;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                await cur.execute(query, (user_id,))
                await self.__conn.commit()

    async def remove_from_blacklist(self, user_id: int):
        query = f'DELETE FROM blacklist WHERE user_id = ?;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query, (user_id,))
                    await self.__conn.commit()
                    services.blacklist.remove(user_id)
                    return True
                except aiosqlite.Error as e:
                    print(f"Ошибка aiosqlite: {e}")
                    return False

    async def get_autoresponces(self):
        query = 'SELECT * from autoresponces;'
        
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query)
                autoresps = await cur.fetchall()
                return autoresps

    async def get_autoresponces_keywords(self):
        query = 'SELECT keyword from autoresponces;'
        
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query)
                keywords = await cur.fetchall()
                return keywords

    async def get_autoresponce(self, keyword: int):
        query = 'SELECT * FROM autoresponces WHERE keyword = ?;'
        
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query, (keyword,))
                autoresp = await cur.fetchall()
                return autoresp

    async def add_autoresponce(self, keyword: str, responce: str, photo=None):
        try:
            query = 'INSERT OR REPLACE INTO autoresponces '\
                '(keyword, responce, photo) VALUES (?, ?, ?);'

            lock = asyncio.Lock()
            async with lock:
                async with self.__conn.cursor() as cur:
                    await cur.execute(query, (keyword, responce, photo))
                    await self.__conn.commit()
                    services.keywords.append(keyword)
                    return True

        except Exception as e:
            return False

    async def add_product(self, name, info, price, photo):
        try:
            query = 'INSERT OR REPLACE INTO products '\
                '(name, info, price, photo) VALUES (?, ?, ?, ?);'

            lock = asyncio.Lock()
            async with lock:
                async with self.__conn.cursor() as cur:
                    await cur.execute(query, (name, info, price, photo))
                    await self.__conn.commit()
                    return True     

        except Exception as e:
            return False

    async def get_products(self):
        query = 'SELECT * from products;'
        
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query)
                prods = await cur.fetchall()
                return prods

    async def get_product(self, id):
        query = 'SELECT * from products '\
            'WHERE id = ?;'
        
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query, (id,))
                    prod = await cur.fetchall()
                    return prod
                except Exception as e:
                    return False

    async def del_product(self, name):
        query = f'DELETE FROM products WHERE name = ?;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query, (name,))
                    await self.__conn.commit()
                    return True
                except aiosqlite.Error as e:
                    print(f"Ошибка aiosqlite: {e}")
                    return False 

    async def del_autoresponce(self, keyword: str):
        query = f'DELETE FROM autoresponces WHERE keyword = ?;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query, (keyword,))
                    await self.__conn.commit()
                    services.keywords.remove(keyword)
                    return True
                except aiosqlite.Error as e:
                    (f"Ошибка aiosqlite: {e}")
                    return False

    async def execute_sql_command(self, query):
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:
                try:
                    await cur.execute(query)
                    await self.__conn.commit()
                    result = await cur.fetchall()
                    return result
                except Exception as e:
                    return e

# ======================================================================== #
# ======================================================================== #

    async def get_contact(self, message_id: int):

        query = 'SELECT contact FROM messages'\
            f' WHERE message_id = ?;'

        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query, (message_id,))
                contact = await cur.fetchall()
                return contact

    async def get_location(self, message_id: int):
       
        query = 'SELECT location FROM messages'\
            f' WHERE message_id = ?;'
    
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query, (message_id,))
                location = await cur.fetchall()
                return location

    async def get_invoice(self, message_id: int):
       
        query = 'SELECT invoice FROM messages'\
            f' WHERE message_id = ?;'
    
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query, (message_id,))
                invoice = await cur.fetchall()
                return invoice
    
    async def get_successful_payment(self, message_id: int):

        query = 'SELECT successful_payment FROM messages'\
            f' WHERE message_id = ?;'
    
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query, (message_id,))
                successful_payment = await cur.fetchall()
                return successful_payment
            
    async def get_passport(self, message_id: int):

        query = 'SELECT passport_data FROM messages'\
            f' WHERE message_id = ?;'
    
        lock = asyncio.Lock()
        async with lock:
            async with self.__conn.cursor() as cur:

                await cur.execute(query, (message_id,))
                passport_data = await cur.fetchall()
                return passport_data

db = Database(DATABASE)
