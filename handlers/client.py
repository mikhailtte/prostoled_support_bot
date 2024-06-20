from aiogram import types
from aiogram.dispatcher import Dispatcher

# команды бота
async def echo(msg: types.Message):
    return await msg.answer(msg.text)

# здесь необходимо прописать инициализацию всех команд бота
def register_commands(dp: Dispatcher):
    dp.register_message_handler(echo)
