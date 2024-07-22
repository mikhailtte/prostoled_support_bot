from datetime import datetime
from aiogram import types, Bot
from aiogram.dispatcher import Dispatcher, FSMContext
import filters
from services import sessions, active_messages, keywords
from config import SUPPORT_CHAT_ID as group_chat_id
from database import db, prod_cell
import difflib
from aiogram.dispatcher.filters.state import State, StatesGroup

def get_best_match(input_text):
    # Находим наилучшее соответствие ключевому слову
    matches = difflib.get_close_matches(input_text, keywords, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    return None

async def to_group(message: types.Message):
    '''
    Пересылка пользовательского сообщения в группу 
    '''
    await db.check_user(message)
    
    if message.chat.id not in sessions.keys():
        # запрашиваем совпадение
        match = get_best_match(message.text)
        if match is not None:
            # запрашиваем текст ключа
            responce = await db.get_autoresponce(match)

            menu = types.InlineKeyboardMarkup()
            menu.add(
            types.InlineKeyboardButton(
                text="Задать вопрос",
                callback_data=f"_human")
            )
            menu.add(
            types.InlineKeyboardButton(
                text="Заказать",
                callback_data=f"_order")
            )
            _text = 1; _photo = 2
            if responce[0][_photo]:
                await message.answer_photo(
                    photo=responce[0][_photo], 
                    caption=responce[0][_text],
                    parse_mode='Markdown',
                    reply_markup=menu
                )
                return
            else:
                await message.answer(
                    text=responce[0][_text],
                    parse_mode='Markdown',
                    reply_markup=menu
                )
                return
    
    # пересылаем сообщение из лички в группу
    sent = await message.bot.forward_message(
        chat_id=group_chat_id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        disable_notification=False,
        protect_content=False
    )
    
    # сообщение ожидания с игнором
    ignore_key = types.InlineKeyboardMarkup()
    ignore_key.add(
        types.InlineKeyboardButton(
            text="Игнор",
            callback_data=f"_Ignore:{sent.message_id}")
        )
    sent_status = await message.bot.send_message(
        chat_id=group_chat_id,
        text='Ожидает ⬆️',
        reply_markup=ignore_key
    )

    # создание сессии
    if message.chat.id not in sessions.keys():

        # проверка наличия комента - это отправляется толко один раз при создани сессии.
        comment = await db.get_comment(message.from_id)
        if comment[0][0] is not None:
            await message.bot.send_message(
                chat_id=group_chat_id,
                text=''.join(('❕ *заметка:* ', comment[0][0])),
                parse_mode='Markdown'
            )

        # добавление новой сессии
        sessions[message.chat.id]= {
            'messages_id': [sent.message_id,],
            'date': message.date.timestamp(),
            'user_id': message.from_id
        }

        await db.open_session(message.chat.id, message.from_id, sent.message_id)
        print('session created')
    else:
        sessions[message.chat.id]['messages_id'].append(sent.message_id)

    # добавляем в активные
    active_messages[sent.message_id] = {
        # айди чата пользователя
        'chat_id': message.chat.id,
        'date': message.date.timestamp(),
        'callback_message_id': sent_status.message_id,
        'reminds_id': []
    }
    await db.write_message(message, client=True, group_message_id=sent.message_id)
    await db.update_user(message)

async def cb_human(cb: types.CallbackQuery):
    await cb.answer(text='Вам ответит cпециалист', show_alert=False)
    await cb.message.answer('Задайте свой вопрос: ')
    # запись новой сессии
    await db.open_session(cb.message.chat.id, cb.from_user.id, cb.message.message_id)
    
    sessions[cb.message.chat.id] = {
        'messages_id': [],
        'date': cb.message.date.timestamp(),
        'user_id': cb.message.from_id
    }

async def human(message: types.Message):
    await message.answer('Вам ответит специалист,\nЗадайте свой вопрос: ')
    await db.open_session(message.chat.id, message.from_id, message.message_id)

    sessions[message.chat.id] = {
        'messages_id': [],
        'date': message.date.timestamp(),
        'user_id': message.from_id
    }

class order_states(StatesGroup):
    wait_for_name = State()
    wait_for_quantity = State()
    wait_for_continue = State() # вот это надо обыграть
    wait_for_container = State()
    wait_for_delivery = State()
    wait_for_number = State()
    wait_for_comment = State()
    wait_confirm = State()

# ========================================================================== #
# ORDER CREATING

async def order(message: types.Message):
    prods = await db.get_products()
    if not prods:
        await message.reply('Список товаров пуст')
        return

    # отправляем каждый товар.
    # описание запршивается по инлайн кнопке -> во всплывающем окне
    
    for prod in prods:

        name_formatted = f'*{prod[prod_cell.name]}*'
        text = '\n'.join((name_formatted, prod[prod_cell.price]))

        info_key = types.InlineKeyboardMarkup(row_width=2)
        info_key.add(
            types.InlineKeyboardButton(text="Описание", callback_data=f"_prod_info:{prod[prod_cell.id]}")
        )
        info_key.add(
            types.InlineKeyboardButton(text="Выбрать", callback_data=f"_select_prod:{prod[prod_cell.id]}")
        )

        text = text.replace('(', r'\(').replace(')', r'\)')
        await message.answer_photo(
            photo=prod[prod_cell.photo],
            caption=text,
            parse_mode=types.ParseMode.MARKDOWN,
            reply_markup=info_key,
        )
  
    control_key = types.InlineKeyboardMarkup(row_width=1)
    control_key.add(
        types.InlineKeyboardButton(text="Отмена", callback_data="_order_cancel")
    )
    await message.answer("Выберите тип льда", reply_markup=control_key)
    await order_states.wait_for_name.set()

async def order_cancel(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer('Отменено')
    await cb.message.answer('Создание заказа отменено.')
    await state.finish()

async def got_name(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer('Выбрано')
    text = await db.get_quantity_message()
    if not text:
        text = 'Напишите сколько килограм льда вам нужно:\n'\
        '\* Фасовка по 5/10 кг\nКонтейнер по 40 кг'

    control_key = types.InlineKeyboardMarkup(row_width=2)
    control_key.add(
        types.InlineKeyboardButton(text="Отмена", callback_data="_order_cancel")
    )
    control_key.add(
        types.InlineKeyboardButton(text="Назад", callback_data="_order_prev_state")
    )

    await cb.message.answer(
        text,
        reply_markup=control_key,
        parse_mode=types.ParseMode.MARKDOWN
    )
    await order_states.wait_for_quantity.set()
    
    prod_id = cb.data.split(':')[1]
    prod = await db.get_product(prod_id)
    prod_name = prod[prod_cell.name]

    print('Мы тут!!!')
    async with state.proxy() as data:
        prods = data.get('prods', {})
        # Название : Кол-во
        prods[prod_name] = None
        print('\n\n')
        # ЭТОТ КОД ВООБЩЕ НЕ ВЫПОЛНЯЕТСЯ!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        print('====================================')
        data['prods'] = prods 
        print(f'{data["prods"] = }')
        print('====================================')        
        print('\n\n')
        # ждем кол-во данного товара
        data['wait_quantity'] = prod_name
        data['chat_id'] = cb.message.chat.id
        data['user_id'] = cb.from_user.id

async def got_quantity(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        prods = data['prods']
        name = data['wait_quantity']
        # Название : Кол-во
        prods[name] = message.text
        data['prods'] = prods

        # data['prods'][data['wait_quantity']] = message.text
        # print(f'{data[data["wait_quantity"]] = }')
        # print(f'{message.text = }')
        # print(f'{data["wait_quantity"] = }')
        # # for i, j in data['prods']

        del data['wait_quantity']


        selected = ''
        for i, (prod_name, quantity) in enumerate(data['prods'].items(), start=1):
            selected += f'{i}. {prod_name} {quantity} (кг)\n'

        text = f'Вы выбрали:\n{selected}'
    
    control_key = types.InlineKeyboardMarkup(row_width=2)
    control_key.add(
        types.InlineKeyboardButton(text="Выбрать еще", callback_data="_order_add")
    )
    control_key.add(
        types.InlineKeyboardButton(text="Продолжить", callback_data="_order_continue")
    )
    control_key.add(
        types.InlineKeyboardButton(text="Отмена", callback_data="_order_cancel")
    )
    control_key.add(
        types.InlineKeyboardButton(text="Назад", callback_data="_order_prev_state")
    )

    await message.answer(text, reply_markup=control_key)
    await order_states.wait_for_continue.set()

async def order_cb(cb: types.CallbackQuery, state: FSMContext):
    cb.answer('Выберите еще:')
    prods = await db.get_products()

    if not prods:
        await cb.message.reply('Список товаров пуст')
        return

    # отправляем каждый товар.
    # описание запршивается по инлайн кнопке -> во всплывающем окне
    for prod in prods:

        name_formatted = f'*{prod[prod_cell.name]}*'
        text = '\n'.join((name_formatted, prod[prod_cell.price]))
        
        info_key = types.InlineKeyboardMarkup(row_width=2)
        info_key.add(
            types.InlineKeyboardButton(text="Описание", callback_data=f"_prod_info:{prod[prod_cell.id]}")
        )
        info_key.add(
            types.InlineKeyboardButton(text="Выбрать",callback_data=f"_select_prod:{prod[prod_cell.id]}")
        )

        text = text.replace('(', r'\(').replace(')', r'\)')
        await cb.message.answer_photo(
            photo=prod[prod_cell.photo],
            caption=text,
            parse_mode=types.ParseMode.MARKDOWN,
            reply_markup=info_key
        )

    continue_key = types.InlineKeyboardMarkup(row_width=1)
    continue_key.add(
        types.InlineKeyboardButton(text="Продолжить", callback_data="_order_continue")
    )
    continue_key.add(
        types.InlineKeyboardButton(text="Отмена",callback_data="_order_cancel")
    )
    continue_key.add(
        types.InlineKeyboardButton(text="Назад", callback_data="_order_prev_state")
    )

    await cb.message.answer("Выберите тип льда", reply_markup=continue_key)
    await order_states.wait_for_name.set()

async def got_continue(cb: types.CallbackQuery, state: FSMContext):
    container_message = await db.get_container_message()

    if not container_message:
        container_message = 'Мы предлагаем Вам контейнер на 40 кг для '\
        'транспортировки и хранения льда.'\
        '\nЦена контейнера - 400₽\n\n Сколько контейнеров вам нужно?'

    no_cointaner = types.InlineKeyboardMarkup()
    no_cointaner.add(
        types.InlineKeyboardButton(text="Не нужен", callback_data=f"_no_container")
    )
    no_cointaner.add(
        types.InlineKeyboardButton(text="Назад", callback_data="_order_prev_state")
    )

    await cb.message.answer(container_message, reply_markup=no_cointaner, parse_mode=types.ParseMode.MARKDOWN)
    await order_states.wait_for_container.set()

async def got_no_container(cb: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['container'] = 'Не нужен'

    await order_delivery(cb=cb, state=state)

async def got_container_quantity(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['container'] = message.text

    await order_delivery(message=message, state=state)

async def order_delivery(cb: types.CallbackQuery = None, message: types.Message = None, state: FSMContext = None):
    '''state - Required! state - Обязателен! Либо сообщение либо коллбек-запрос'''

    delivery_message = await db.get_delivery_message()
    if not delivery_message:
        delivery_message = '\n\Напишите адрес доставки:'
    else:
        text = str(delivery_message) + '\n\Напишите адрес доставки:'

    pickup = types.InlineKeyboardMarkup()
    pickup.add(
        types.InlineKeyboardButton(text="Самовывоз", callback_data="_prod_pickup")
    )
    pickup.add(
        types.InlineKeyboardButton(text="Отмена", callback_data="_order_cancel")
    )
    pickup.add(
        types.InlineKeyboardButton(text="Назад", callback_data="_order_prev_state")
    )

    if message:
        await message.answer(text=text, reply_markup=pickup)
    if cb:    
        await cb.message.answer(text=text, reply_markup=pickup)

    await order_states.wait_for_delivery.set()

async def got_address(message: types.Message, state: FSMContext):    
    
    async with state.proxy() as data:
        data['address'] = message.text
    await ask_number(message = message, cb = None, state=state)
    
async def got_pickup(cb: types.CallbackQuery, state: FSMContext):
    pickup_message = await db.get_pickup_message()
    if not pickup_message:
        pickup_message = "Мы перезвоним Вам и сообщим адрес самовывоза, '\
        'после завершения создания заказа"
    
    await cb.message.answer(pickup_message, parse_mode=types.ParseMode.MARKDOWN)
    
    async with state.proxy() as data:
        data['address'] = 'Самовывоз'
    await ask_number(message = None, cb = cb, state=state)

async def ask_number(cb: types.CallbackQuery = None, message: types.Message = None, state: FSMContext = None):
    text = 'Напишите Ваш контактный номер телефона для связи. Мы Вам перезвоним для подтверждения заказа'

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        types.KeyboardButton(text='Номер', request_contact=True)
    )
    ctrl_key = types.InlineKeyboardMarkup()
    ctrl_key.add(
        types.InlineKeyboardButton(text="Отмена", callback_data="_order_cancel")
    )
    ctrl_key.add(
        types.InlineKeyboardButton(text="Назад", callback_data="_order_prev_state")
    )

    if cb:
        await cb.message.answer(text=text, reply_markup=(kb, ctrl_key))
    if message:
        await message.answer(text=text, reply_markup=(kb, ctrl_key))
    
    await order_states.wait_for_number.set()

async def got_number(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['contact'] = message.text
    await ask_comment(message=message, state=state)

async def got_contact(contact: types.Contact, state: FSMContext):
    async with state.proxy() as data:
        data['contact'] = contact.phone_number
    await ask_comment(contact=contact, state=state)

async def ask_comment(contact: types.Contact = None,
                      message: types.Message = None,
                      state: FSMContext = None):
    text = 'Напишите любой коментарий к заказу, например когда ожидаете получить заказ:'

    ctrl_key = types.InlineKeyboardMarkup()
    ctrl_key.add(
        types.InlineKeyboardButton(text="Отмена", callback_data="_order_cancel")
    )
    ctrl_key.add(
        types.InlineKeyboardButton(text="Назад", callback_data="_order_prev_state")
    )

    if contact:
        async with state.proxy() as data:
            chat_id = data['chat_id']
        await contact.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=ctrl_key,
            parse_mode=types.ParseMode.MARKDOWN
        )
    if message:
        await message.answer(
            text=text,
            reply_markup=ctrl_key,
            parse_mode=types.ParseMode.MARKDOWN
        )

    await order_states.wait_for_comment.set()

async def got_comment(message: types.Message, state=FSMContext):

    async with state.proxy() as data:
        data['comment'] = message.text
    await send_confirm_order(message, state)
    
async def send_confirm_order(message: types.Message, state=FSMContext):
    order_text = ''

    async with state.proxy() as data:
          
        for i, (prod_name, quantity) in enumerate(data['prods'], start=1):
            order_text += f'{i}. {prod_name}: {quantity} (кг)\n'

        if data['container'] != 'Не нужен':
            order_text += f'\n\n Контейнер: {data["container"]}'

        order_text += f'\nДоставка: {data["address"]}'
        order_text += f'\nКонтактный телефон: {data["contact"]}'
        order_text += f'\nКомментарий: {data["comment"]}'
    
    keys = types.InlineKeyboardMarkup(row_width=1)
    keys.add(
        types.InlineKeyboardButton(text="Подтвердить", callback_data="_order_continue")
    )
    keys.add(
        types.InlineKeyboardButton(text="Отмена", callback_data="_order_cancel")
    )
    keys.add(
        types.InlineKeyboardButton(text="Назад", callback_data="_order_prev_state")
        )

    await message.answer(order_text, reply_markup=keys, parse_mode=types.ParseMode.MARKDOWN)
    await message.answer('_Позднее вы так же сможете изменить или отменить заказ._')
    await order_states.wait_confirm.set()

async def order_done(cb: types.CallbackQuery, state: FSMContext):

    text = 'Ваш заказ принят, мы Вам перезвним в ближайшее время для '\
        'подтверждения заказа.\n\nЧто бы изменить или отменить заказ, а так '\
        'же что бы задать вопрос — пишите нам в поддержку, мы с радостью Вам ответим!'
    
    await cb.message.answer(text)
    # now = datetime.now()

    order_text = f'Новый заказ!\n\n'

    async with state.proxy() as data:
          
        for i, (prod_name, quantity) in enumerate(data['prods'], start=1):
            order_text += f'{i}. {prod_name}: {quantity} (кг)\n'

        if data['container'] != 'Не нужен':
            order_text += f'\n\n Контейнер: {data["container"]}'

        order_text += f'\nДоставка: {data["address"]}'
        order_text += f'\nКонтактный телефон: {data["contact"]}'
        order_text += f'\nКомментарий: {data["comment"]}'
        user_id = data['user_id']

    await cb.bot.send_message(
        chat_id=group_chat_id,
        text=order_text,
    )
    user_comment = await db.get_comment(user_id)
    if user_comment:
        await cb.bot.send_message(
        chat_id=group_chat_id,
        text="⬆️ Заметка о покупателе:\n" + user_comment
    )

    await state.finish()

async def order_prev_state(cb: types.CallbackQuery, state: FSMContext):
    state_name = await state.get_state()
    prev = await order_states.previous()
    print(state_name)
    print(prev)



    # match state_name:
    #     case order_states.first():
    #         ...
    #     case order_states.wait_for_quantity:

async def prod_info(cb: types.CallbackQuery, state: FSMContext = None):
    try:
        prod = await db.get_product(cb.data.split(':')[1])
        await cb.answer(
            text=prod[0][2].replace('\\', ''),
            show_alert=True,
        )
    except Exception as e:
        print(f'\n\n EXCEPTION PROD INFO: {e}\n\n')


def register_dialog_commands(dp: Dispatcher):
    # кнопка отмена
    dp.register_callback_query_handler(
        order_cancel,
        lambda query: query.data == ('_order_cancel'),
        filters.not_group_cb,
        state=order_states.all_states
    )
    # кнопка назад
    dp.register_callback_query_handler(
        order_prev_state,
        lambda query: query.data == ("_order_prev_state"),
        filters.not_group_cb,
        state=order_states.all_states
    )
    dp.register_callback_query_handler(
        prod_info,
        lambda query: query.data.startswith('_prod_info:'),
        state=order_states.all_states
    )
    # получили название товара
    dp.register_callback_query_handler(
        got_name,
        filters.not_group_cb,
        lambda query: query.data.startswith('_select_prod:'),
        state=order_states.wait_for_name
    )
    # получили кол-во товара
    # отправляет предложение добавить еще товар или продолжить
    dp.register_message_handler(
        got_quantity,
        filters.not_group,
        state=order_states.wait_for_quantity
    )
    # добавить еще товар
    dp.register_callback_query_handler(
        order_cb,
        lambda query: query.data == ("_order_add"),
        filters.not_group_cb,
        state=order_states.wait_for_continue
    )
    dp.register_callback_query_handler(
        got_continue,
        lambda query: query.data == "_order_continue",
        filters.not_group_cb,
        state=order_states.wait_for_name
    )
    

    # продолжить с выбранным товаром
    # кол-во контейнеров или отказаться
    dp.register_callback_query_handler(
        got_continue,
        lambda query: query.data == "_order_continue",
        filters.not_group_cb,
        state=order_states.wait_for_continue
    )
    # отказ от контейнера
    dp.register_callback_query_handler(
        got_no_container,
        lambda query: query.data == "_no_container",
        filters.not_group_cb,
        state=order_states.wait_for_container
    )
    # прислали ков-ло контейнеров
    dp.register_message_handler(
        got_container_quantity,
        filters.not_group,
        state=order_states.wait_for_container
    )
    # самовывоз
    dp.register_callback_query_handler(
        got_pickup,
        lambda query: query.data == "_prod_pickup",
        filters.not_group_cb,
        state=order_states.wait_for_delivery
    )
    # прислали адрес доставки
    dp.register_message_handler(
        got_address,
        filters.not_group,
        state=order_states.wait_for_container
    )
    # написали номер сообщением
    dp.register_message_handler(
        got_number,
        filters.not_group,
        state=order_states.wait_for_number
    )
    # прислали контакт
    dp.register_message_handler(
        got_contact,
        filters.not_group,
        content_types=types.ContentType.CONTACT,
        state=order_states.wait_for_number
    )
    # подтвержение заказа
    dp.register_callback_query_handler(
        order_done,
        lambda query: query.data == "_order_continue",
        filters.not_group_cb,
        state=order_states.wait_confirm
    )


def register_commands(dp: Dispatcher):
    dp.register_callback_query_handler(
        cb_human,
        lambda query: query.data == '_human',
        filters.not_group_cb
    )
    dp.register_message_handler(
        human,
        filters.human,
        filters.not_group
    )
    dp.register_message_handler(
        order,
        filters.order,
        filters.not_group
    )
    dp.register_message_handler(
        to_group,
        filters.not_group,
        filters.is_not_cmd,
        content_types=types.ContentType.all()
    )
