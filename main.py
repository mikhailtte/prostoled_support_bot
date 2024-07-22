from config import TOKEN
from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.utils.executor import start_webhook
from aiogram.types.input_file import InputFile
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import asyncio
from handlers import client, admin
import config
from _logging import setup_logger
import services
from database import db
import requests
from time import sleep

storage = MemoryStorage()
_bot = Bot(token=TOKEN)
dp = Dispatcher(_bot, storage=storage)
# список запущенных в фоне задач
tasks = []
# объект события остановки
stop = asyncio.Event()

# инициализация команд

admin.register_dialog_commands(dp)
client.register_dialog_commands(dp)
admin.register_main_commands(dp)
client.register_commands(dp)
admin.register_dynamic_commands(dp)


async def on_startup(dp: Dispatcher):
    
    await _bot.delete_webhook()
    await _bot.set_webhook(
        config.WEBHOOK_URL,
        certificate=InputFile(config.CERT)
    )
    asyncio.create_task(db.open())
    asyncio.create_task(services.init_userdata(_bot, db))
    
    global tasks, stop
    tasks.append(asyncio.create_task(services.remove_old_sessions(db, stop)))
    # передаем бот для отправки уведомлов и объект события остановки
    tasks.append(asyncio.create_task(services.messages_reminder(_bot, stop)))
    tasks.append(asyncio.create_task(services.performance(db, stop)))


async def on_shutdown(dp):
    await _bot.delete_webhook()

    global stop, tasks
    tasks.append(asyncio.create_task(db.close()))
    # активируем остановку
    stop.set()
    # # ждем окончания их выполнения
    await asyncio.gather(*tasks, return_exceptions=True)
    print('\n')

def on_line():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

if __name__ == '__main__':

    log = setup_logger(__name__)

    start_webhook(
        dispatcher=dp,
        webhook_path=config.WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=config.WEBAPP_HOST,
        port=config.WEBAPP_PORT,
    )
