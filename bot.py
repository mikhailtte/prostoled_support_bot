from parameters import TOKEN
from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.utils.executor import start_webhook
from aiogram.types.input_file import InputFile
from handlers import client
import parameters
from _logging import setup_logger
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# инициализация команд клиентской части бота
client.register_commands(dp)

async def on_startup(dp):
    await bot.set_webhook(
        parameters.WEBHOOK_URL,
        certificate=InputFile(parameters.CERT)
    )

async def on_shutdown(dp):
    await bot.delete_webhook()

if __name__ == '__main__':
    log = setup_logger(__name__)
    try:
        print('setup webhook... ', end=' ')
        start_webhook(
            dispatcher=dp,
            webhook_path=parameters.WEBHOOK_PATH,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host=parameters.WEBAPP_HOST,
            port=parameters.WEBAPP_PORT,
        )
        print('successfully.')
    except Exception as ex:
        print(f'\nSetup webhook error: {ex}')
        log.fatal('Setup webhook error')