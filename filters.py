from config import SUPPORT_CHAT_ID as group_chat_id
from aiogram import types
from services import sessions, blacklist

async def in_group(message: types.Message):
        return message.chat.id == group_chat_id

async def group_member(message: types.Message):
    ''' id состоит в группе и при наличии текста он начинается со '/' '''
    
    chat_member = await message.bot.get_chat_member(group_chat_id, message.from_id)
    
    # denied = ['restricted', 'left', 'kicked']
    available = ['member', 'administrator”', 'creator']

    if chat_member['status'] in available:
        if hasattr(message, 'text'):
            return message.text.startswith('/')
        else:
            return True
    else:
        return False

async def inline_group_member(query: types.InlineQuery):
    try:
        chat_member = await query.bot.get_chat_member(group_chat_id, query.from_user.id)
        # denied = ['restricted', 'left', 'kicked']
        available = ['member', 'administrator”', 'creator']
        return chat_member['status'] in available
    except Exception as e:
        return False 

async def session_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.split('@')[0].upper() in ('/СЕССИЯ', '/ССЕСИЯ', '/СЕССИА', '/SESSION', '/SSESION', '/СЕССИЧ')

async def history_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.split('@')[0].upper() in ('/ИСТРИЯ', '/ИСТОРИЯ', '/ИСТРИЧ', '/HYSTORY', ', /HISTORY', '/ИСТОРИЧ')

async def delete_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.split('@')[0].upper() in ('/УДАЛИТЬ', '/УДАЛИТ', '/DELETE', '/REMOVE')

async def active_session_cmd(message:types.Message):
    return hasattr(message, 'text') and message.text.split('@')[0].upper() in ('/АКТИВНЫХСЕССИЙ', '/АКТИВНЫХ_СЕССИЙ')

async def message_count_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.split('@')[0].upper() in ('/ЗАДЕНЬ', '/ЗА_ДЕНЬ')

async def add_to_blacklist_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.split('@')[0].upper() in ('/ВЧС', '/ВЧЕРНЫЙСПИСОК')

async def remove_from_blacklist_cmd(message: types.Message):
    return hasattr(message, 'text') and \
        (message.text.split('@')[0].startswith('/del') or message.text.upper() in ('/ИЗЧС'))

async def execute_sql_query(message: types.Message):
    return hasattr(message, 'text') and message.text.split('@')[0].startswith('/db:')

async def get_blacklist_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.split('@')[0].upper() in ('/ЧС', '/ЧЕРНЫЙСПИСОК')

async def add_comment(message: types.Message):
    return hasattr(message, 'text') and \
        (message.text.split('@')[0].startswith('/коммент') or message.text.split('@')[0].startswith('/заметка'))

async def performance(message: types.Message):
    return hasattr(message, 'text') and \
        (message.text.split('@')[0].startswith('/производительность') or message.text.split('@')[0].startswith('/performance'))

async def del_comment(message: types.Message):
    if hasattr(message, 'text'):
        text = message.text.split('@')[0]
        cmds = ('/удалить_заметку', '/коммент_удалить', '/коммент удалить', '/коммент_стереть',
                '/коммент стереть', '/заметка_удалить', '/заметка удалить', '/заметка_стереть',
                '/заметка стереть', '/удалить коммент', '/удалить_коммент', '/стереть_коммент',
                '/стереть коммент', '/удалить заметку', '/стереть_заметку', '/стереть заметку')
        if text.strip().lower() in cmds:
            return True
    return False

async def is_not_cmd(message: types.Message):
    return hasattr(message, 'text') \
        and not message.text is None \
        and not message.text.startswith('/') \
        and not message.text.startswith('\\')

async def in_blacklist(message: types.Message):
    return message.from_user.id in blacklist

async def in_blacklist_cb(cb: types.CallbackQuery):
    return cb.from_user.id in blacklist

async def admin_ls(message: types.Message):
    if message.chat.id != group_chat_id:
        
        # denied = ['restricted', 'left', 'kicked']
        available = ['member', 'administrator”', 'creator']

        chat_member = await message.bot.get_chat_member(group_chat_id, message.from_id)
        return chat_member['status'] in available
    else:
        return False

async def callback_admin_ls(callback: types.CallbackQuery):
    if callback.message.chat.id != group_chat_id:
        chat_member = await callback.message.bot.get_chat_member(group_chat_id, callback.from_user.id)
        # denied = ['restricted', 'left', 'kicked']
        available = ['member', 'administrator”', 'creator']
        return chat_member['status'] in available
    else:
        return False

async def add_autoresponce_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/добавить_автоответ')

async def del_autoresponce_cmd(message: types.Message):
    return hasattr(message, 'text') and \
        (   
            message.text.startswith('/удалить_автоответ') or
            message.text.startswith('/удалить_ответ') or
            message.text.startswith('del_autoresponce')
        )

async def del_prod_cmd(message: types.Message):
    return hasattr(message, 'text') and \
        (   
            message.text.startswith('/удалить_товар') or
            message.text.startswith('/del_product')
        )

async def is_cmd(message: types.Message):
    return hasattr(message, 'text') and ( message.text.startswith('/') or message.text.startswith('\\'))

# ======================================================================== #
# ======================================================================== #
async def get_photo_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/photo:')

async def get_animation_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/animation:')

async def get_audio_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/audio:')

async def get_document_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/document:')

async def get_video_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/video:')

async def get_sticker_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/sticker:')

async def get_voice_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/voice:')

async def get_contact_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/contact:')

async def get_location_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/location:')

async def get_invoice_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/invoice:')

async def get_successful_payment_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/successful_payment:')

async def get_passport_cmd(message: types.Message):
    return hasattr(message, 'text') and message.text.startswith('/passport:')

async def human(message: types.Message):
    if message.chat.id not in sessions:
        if hasattr(message, 'text') and message.text is not None:
            for key in ('поддержка', 'человек', 'помощь', 'бля', 'работник', 'support', 'help'):
                if key in message.text:
                    return True
    return False

async def order(message: types.Message):
    if hasattr(message, 'text') and message.text is not None:
        return message.text.replace('/', '') in ('заказ', 'order', 'заказать')
    return False

async def not_group(message: types.Message):
    return message.chat.id != group_chat_id

async def not_group_cb(cb: types.CallbackQuery):
    return cb.message.chat.id != group_chat_id
