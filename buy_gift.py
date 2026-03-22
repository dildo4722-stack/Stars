from aiogram import F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, SuccessfulPayment
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command

from bot_instance import dp, bot
from database import (get_balance, update_balance, add_transaction, 
                      get_bot_stars_balance, update_bot_stars_balance,
                      get_user_by_username)
from keyboards import (get_back_to_menu_button, get_gift_selection_kb, 
                       get_gift_currency_selection_kb, get_cancel_button)
from config import STAR_PRICE_RUB, STAR_PRICE_USD, STAR_PRICE_TON, ADMIN_IDS
import logging
import re
import uuid

# Словарь с подарками (6 штук)
GIFTS = {
    "gift_1": {
        "id": "5893356958802511476",
        "custom_emoji_id": "5317000922096769303",
        "name": "Подарок 1",
        "stars_price": 50,
        "rub_price": 50 * STAR_PRICE_RUB,
        "usd_price": 50 * STAR_PRICE_USD,
        "ton_price": 50 * STAR_PRICE_TON
    },
    "gift_2": {
        "id": "5866352046986232958",
        "custom_emoji_id": "5289761157173775507",
        "name": "Подарок 2",
        "stars_price": 50,
        "rub_price": 50 * STAR_PRICE_RUB,
        "usd_price": 50 * STAR_PRICE_USD,
        "ton_price": 50 * STAR_PRICE_TON
    },
    "gift_3": {
        "id": "5800655655995968830",
        "custom_emoji_id": "5226661632259691727",
        "name": "Подарок 3",
        "stars_price": 50,
        "rub_price": 50 * STAR_PRICE_RUB,
        "usd_price": 50 * STAR_PRICE_USD,
        "ton_price": 50 * STAR_PRICE_TON
    },
    "gift_4": {
        "id": "5801108895304779062",
        "custom_emoji_id": "5224628072619216265",
        "name": "Подарок 4",
        "stars_price": 50,
        "rub_price": 50 * STAR_PRICE_RUB,
        "usd_price": 50 * STAR_PRICE_USD,
        "ton_price": 50 * STAR_PRICE_TON
    },
    "gift_5": {
        "id": "5956217000635139069",
        "custom_emoji_id": "5379850840691476775",
        "name": "Подарок 5",
        "stars_price": 50,
        "rub_price": 50 * STAR_PRICE_RUB,
        "usd_price": 50 * STAR_PRICE_USD,
        "ton_price": 50 * STAR_PRICE_TON
    },
    "gift_6": {
        "id": "5922558454332916696",
        "custom_emoji_id": "5345935030143196497",
        "name": "Подарок 6",
        "stars_price": 50,
        "rub_price": 50 * STAR_PRICE_RUB,
        "usd_price": 50 * STAR_PRICE_USD,
        "ton_price": 50 * STAR_PRICE_TON
    }
}

def get_custom_emoji(emoji_id: str) -> str:
    """Возвращает HTML тег для кастомного эмодзи"""
    return f'<tg-emoji emoji-id="{emoji_id}">🎁</tg-emoji>'

class BuyGiftStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_gift_selection = State()
    waiting_for_currency = State()
    waiting_for_stars_payment = State()

async def notify_admins_about_low_stars(needed_stars: int, gift_name: str, user_id: int, user_name: str):
    """Уведомление админов о нехватке звезд"""
    bot_balance = await get_bot_stars_balance()
    
    for admin_id in ADMIN_IDS:
        try:
            builder = InlineKeyboardBuilder()
            builder.button(text="💰 Пополнить через /pay", callback_data="admin_pay_help")
            builder.button(text="✅ Проверить баланс", callback_data="admin_check_balance")
            builder.adjust(1)
            
            await bot.send_message(
                admin_id,
                f"⚠️ <b>ВНИМАНИЕ! НЕХВАТКА ЗВЕЗД!</b>\n\n"
                f"👤 Пользователь: {user_name} (ID: {user_id})\n"
                f"🎁 Подарок: {gift_name}\n"
                f"⭐ Требуется звезд: {needed_stars}\n"
                f"💳 Текущий баланс бота: {bot_balance} ⭐\n\n"
                f"Для пополнения используйте /pay (количество)\n"
                f"После пополнения используйте /add_balance (количество)",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Ошибка при уведомлении админа {admin_id}: {e}")

@dp.callback_query(F.data == "menu:buy_gift")
async def buy_gift_start(callback: CallbackQuery, state: FSMContext):
    """Начало процесса покупки подарка"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Купить для себя", callback_data="gift_for_self")
    builder.button(text="👤 Для другого", callback_data="gift_for_other")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "🎁 <b>Покупка подарка</b>\n\n"
        "🔎 Выберите, для кого будет подарок:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "gift_for_self")
async def gift_for_self(callback: CallbackQuery, state: FSMContext):
    """Подарок для себя"""
    await state.update_data(
        receiver_username=callback.from_user.first_name,
        receiver_id=callback.from_user.id
    )
    
    # Получаем кастомные эмодзи для каждого подарка
    gift_emoji_1 = get_custom_emoji(GIFTS["gift_1"]["custom_emoji_id"])
    gift_emoji_2 = get_custom_emoji(GIFTS["gift_2"]["custom_emoji_id"])
    gift_emoji_3 = get_custom_emoji(GIFTS["gift_3"]["custom_emoji_id"])
    gift_emoji_4 = get_custom_emoji(GIFTS["gift_4"]["custom_emoji_id"])
    gift_emoji_5 = get_custom_emoji(GIFTS["gift_5"]["custom_emoji_id"])
    gift_emoji_6 = get_custom_emoji(GIFTS["gift_6"]["custom_emoji_id"])
    
    await callback.message.edit_text(
        f"🎁 <b>Выберите подарок</b>\n\n"
        f"👤 Получатель: {callback.from_user.first_name}\n\n"
        f"Доступные подарки:\n"
        f"{gift_emoji_1} Подарок 1\n"
        f"{gift_emoji_2} Подарок 2\n"
        f"{gift_emoji_3} Подарок 3\n"
        f"{gift_emoji_4} Подарок 4\n"
        f"{gift_emoji_5} Подарок 5\n"
        f"{gift_emoji_6} Подарок 6\n\n"
        f"Нажмите на кнопку с номером подарка:",
        reply_markup=get_gift_selection_kb(),
        parse_mode="HTML"
    )
    await state.set_state(BuyGiftStates.waiting_for_gift_selection)
    await callback.answer()

@dp.callback_query(F.data == "gift_for_other")
async def gift_for_other(callback: CallbackQuery, state: FSMContext):
    """Подарок для другого"""
    await callback.message.edit_text(
        "👤 Введите @username получателя подарка:",
        reply_markup=get_cancel_button()
    )
    await state.set_state(BuyGiftStates.waiting_for_username)
    await callback.answer()

@dp.message(BuyGiftStates.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    """Обработка введенного username"""
    username = message.text.strip()
    
    if not username.startswith('@'):
        username = '@' + username
    
    if not re.match(r'^@[a-zA-Z0-9_]{5,}$', username):
        await message.answer("❌ Неверный формат username. Пример: @durov")
        return
    
    clean_username = username.replace('@', '').lower()
    receiver = await get_user_by_username(clean_username)
    
    if receiver:
        await state.update_data(receiver_username=username, receiver_id=receiver['user_id'])
        await message.answer(f"✅ Пользователь {username} найден!")
        
        # Получаем кастомные эмодзи для каждого подарка
        gift_emoji_1 = get_custom_emoji(GIFTS["gift_1"]["custom_emoji_id"])
        gift_emoji_2 = get_custom_emoji(GIFTS["gift_2"]["custom_emoji_id"])
        gift_emoji_3 = get_custom_emoji(GIFTS["gift_3"]["custom_emoji_id"])
        gift_emoji_4 = get_custom_emoji(GIFTS["gift_4"]["custom_emoji_id"])
        gift_emoji_5 = get_custom_emoji(GIFTS["gift_5"]["custom_emoji_id"])
        gift_emoji_6 = get_custom_emoji(GIFTS["gift_6"]["custom_emoji_id"])
        
        await message.answer(
            f"🎁 <b>Выберите подарок</b>\n\n"
            f"👤 Получатель: {username}\n\n"
            f"Доступные подарки:\n"
            f"{gift_emoji_1} Подарок 1\n"
            f"{gift_emoji_2} Подарок 2\n"
            f"{gift_emoji_3} Подарок 3\n"
            f"{gift_emoji_4} Подарок 4\n"
            f"{gift_emoji_5} Подарок 5\n"
            f"{gift_emoji_6} Подарок 6\n\n"
            f"Нажмите на кнопку с номером подарка:",
            reply_markup=get_gift_selection_kb(),
            parse_mode="HTML"
        )
        await state.set_state(BuyGiftStates.waiting_for_gift_selection)
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Попробовать другой", callback_data="gift_for_other")
        builder.button(text="❌ Отмена", callback_data="cancel_action")
        
        await message.answer(
            f"⚠️ Пользователь {username} не найден в базе бота.\n\n"
            f"Возможные причины:\n"
            f"• Он еще не запускал бота\n"
            f"• Неправильный username\n\n"
            f"Попробуйте другой username или попросите пользователя написать /start",
            reply_markup=builder.as_markup()
        )
    
    await message.delete()

@dp.callback_query(F.data.startswith("gift:"), BuyGiftStates.waiting_for_gift_selection)
async def select_gift(callback: CallbackQuery, state: FSMContext):
    """Выбор подарка"""
    gift_key = callback.data.split(":")[1]
    gift = GIFTS.get(gift_key)
    
    if not gift:
        await callback.answer("❌ Подарок не найден")
        return
    
    await state.update_data(selected_gift=gift, selected_gift_key=gift_key)
    
    data = await state.get_data()
    receiver = data.get('receiver_username', 'не указан')
    
    # Кастомное эмодзи для выбранного подарка
    custom_emoji = get_custom_emoji(gift['custom_emoji_id'])
    
    await callback.message.edit_text(
        f"🎁 <b>Покупка подарка</b>\n\n"
        f"👤 Получатель: {receiver}\n"
        f"🎀 Подарок: {custom_emoji} {gift['name']}\n\n"
        f"💰 <b>Стоимость:</b>\n"
        f"⭐ Звезды: {gift['stars_price']}\n"
        f"₽ Рубли: {gift['rub_price']:.2f}\n"
        f"💵 Доллары: {gift['usd_price']:.2f}\n"
        f"💎 TON: {gift['ton_price']:.2f}\n\n"
        f"Выберите валюту для оплаты:",
        reply_markup=get_gift_currency_selection_kb(gift_key),
        parse_mode="HTML"
    )
    await state.set_state(BuyGiftStates.waiting_for_currency)
    await callback.answer()

async def send_gift_and_deduct(user_id: int, receiver_id: int, gift: dict, currency: str, price: float):
    """Отправка подарка и списание средств"""
    custom_emoji = get_custom_emoji(gift['custom_emoji_id'])
    
    # Отправляем подарок
    await bot.send_gift(
        user_id=receiver_id,
        gift_id=gift['id'],
        text=f"Подарок от пользователя! {custom_emoji}",
        text_parse_mode="HTML"
    )
    
    # Сохраняем транзакцию
    await add_transaction(
        user_id,
        "gift_purchase",
        amount_rub=price if currency == 'rub' else 0,
        amount_stars=gift['stars_price'] if currency == 'stars' else 0,
        amount_ton=price if currency == 'ton' else 0,
        amount_usd=price if currency == 'usd' else 0,
        status="completed"
    )
    
    return custom_emoji

@dp.callback_query(BuyGiftStates.waiting_for_currency, F.data.startswith("gift_pay_stars:"))
async def process_gift_payment_stars(callback: CallbackQuery, state: FSMContext):
    """Оплата подарка звездами через чек"""
    data = await state.get_data()
    gift = data.get('selected_gift')
    gift_key = data.get('selected_gift_key')
    receiver_id = data.get('receiver_id')
    receiver_username = data.get('receiver_username')
    user_id = callback.from_user.id
    
    if not gift:
        await callback.answer("❌ Ошибка: подарок не выбран")
        return
    
    stars_amount = gift['stars_price']
    
    # Создаем payload для платежа
    payload = f"gift_{user_id}_{gift_key}_{uuid.uuid4().hex[:8]}"
    
    # Сохраняем данные в состояние
    await state.update_data(
        payment_payload=payload,
        payment_gift=gift,
        payment_receiver_id=receiver_id,
        payment_receiver_username=receiver_username
    )
    
    # Создаем клавиатуру с кнопкой оплаты
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💳 Оплатить {stars_amount} ⭐", pay=True)
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1)
    
    # Удаляем старое сообщение
    await callback.message.delete()
    
    # Отправляем инвойс, а не обычное сообщение!
    await callback.message.answer_invoice(
        title=f"🎁 Подарок: {gift['name']}",
        description=f"Покупка подарка для {receiver_username}",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{gift['name']}", amount=stars_amount)],
        reply_markup=builder.as_markup(),
        start_parameter=f"gift_{gift_key}"
    )
    
    await callback.answer()

@dp.callback_query(BuyGiftStates.waiting_for_currency, F.data.startswith("gift_pay_rub:"))
async def process_gift_payment_rub(callback: CallbackQuery, state: FSMContext):
    """Оплата подарка рублями с баланса"""
    await process_currency_payment(callback, state, 'rub')

@dp.callback_query(BuyGiftStates.waiting_for_currency, F.data.startswith("gift_pay_usd:"))
async def process_gift_payment_usd(callback: CallbackQuery, state: FSMContext):
    """Оплата подарка долларами с баланса"""
    await process_currency_payment(callback, state, 'usd')

@dp.callback_query(BuyGiftStates.waiting_for_currency, F.data.startswith("gift_pay_ton:"))
async def process_gift_payment_ton(callback: CallbackQuery, state: FSMContext):
    """Оплата подарка TON с баланса"""
    await process_currency_payment(callback, state, 'ton')

async def process_currency_payment(callback: CallbackQuery, state: FSMContext, currency_type: str):
    """Обработка оплаты подарка валютой с баланса"""
    data = await state.get_data()
    gift = data.get('selected_gift')
    receiver_id = data.get('receiver_id')
    receiver_username = data.get('receiver_username')
    user_id = callback.from_user.id
    
    if not gift:
        await callback.answer("❌ Ошибка: подарок не выбран")
        return
    
    # Получаем цену
    price_map = {
        'rub': gift['rub_price'],
        'usd': gift['usd_price'],
        'ton': gift['ton_price']
    }
    price = price_map.get(currency_type)
    
    if not price:
        await callback.answer("❌ Ошибка оплаты")
        return
    
    balance = await get_balance(user_id, currency_type)
    
    if balance >= price:
        # Проверяем баланс звезд бота
        bot_stars = await get_bot_stars_balance()
        
        if bot_stars >= gift['stars_price']:
            # Достаточно звезд у бота
            # Списываем валюту у пользователя
            await update_balance(user_id, **{currency_type: -price})
            
            # Списываем звезды у бота
            await update_bot_stars_balance(-gift['stars_price'])
            
            # Отправляем подарок
            try:
                custom_emoji = await send_gift_and_deduct(
                    user_id, receiver_id, gift, currency_type, price
                )
                
                # Уведомляем получателя
                if receiver_id != user_id:
                    try:
                        await bot.send_message(
                            receiver_id,
                            f"🎁 Вам подарили подарок {custom_emoji}!\n"
                            f"От: {callback.from_user.first_name}",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
                
                # Успех
                builder = InlineKeyboardBuilder()
                builder.button(text="🎁 Купить еще", callback_data="menu:buy_gift")
                builder.button(text="◀️ В меню", callback_data="back_to_menu")
                builder.adjust(1)
                
                # Название валюты
                currency_names = {'rub': '₽', 'usd': '$', 'ton': 'TON'}
                currency_symbol = currency_names.get(currency_type, currency_type.upper())
                
                await callback.message.edit_text(
                    f"✅ <b>Подарок успешно отправлен!</b>\n\n"
                    f"👤 Получатель: {receiver_username}\n"
                    f"🎀 Подарок: {custom_emoji} {gift['name']}\n"
                    f"💰 Оплачено: {price:.2f} {currency_symbol}\n\n"
                    f"Спасибо за покупку! 🎉",
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
                
            except Exception as e:
                # Возвращаем средства
                await update_balance(user_id, **{currency_type: price})
                await update_bot_stars_balance(gift['stars_price'])
                
                await callback.message.edit_text(
                    f"❌ Ошибка при отправке подарка: {e}",
                    reply_markup=get_back_to_menu_button()
                )
        else:
            # Не хватает звезд у бота
            needed = gift['stars_price'] - bot_stars
            await notify_admins_about_low_stars(
                needed, gift['name'], user_id, callback.from_user.first_name
            )
            
            builder = InlineKeyboardBuilder()
            builder.button(text="🔄 Проверить позже", callback_data="back_to_gifts")
            builder.button(text="❌ Отмена", callback_data="cancel_action")
            builder.adjust(1)
            
            await callback.message.edit_text(
                f"❌ <b>Временно недоступно</b>\n\n"
                f"Извините, сейчас технические работы.\n"
                f"Попробуйте позже или выберите другой способ оплаты.\n\n"
                f"Администраторы уже уведомлены о проблеме.",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
    else:
        # Недостаточно средств у пользователя
        builder = InlineKeyboardBuilder()
        builder.button(text="💰 Пополнить баланс", callback_data="menu:top_up")
        builder.button(text="◀️ Назад к подаркам", callback_data="back_to_gifts")
        builder.button(text="❌ Отмена", callback_data="cancel_action")
        builder.adjust(1)
        
        currency_names = {'rub': '₽', 'usd': '$', 'ton': 'TON'}
        currency_symbol = currency_names.get(currency_type, currency_type.upper())
        
        await callback.message.edit_text(
            f"❌ <b>Недостаточно средств!</b>\n\n"
            f"💰 Ваш баланс: {balance:.2f} {currency_symbol}\n"
            f"💎 Нужно: {price:.2f} {currency_symbol}\n\n"
            f"Выберите другую валюту или пополните баланс.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    
    await state.clear()
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout: PreCheckoutQuery, state: FSMContext):
    """Обработчик проверки платежа для оплаты подарка звездами"""
    try:
        data = await state.get_data()
        # Используем invoice_payload, а не payload
        if data.get('payment_payload') == pre_checkout.invoice_payload:
            await pre_checkout.answer(ok=True)
        else:
            await pre_checkout.answer(ok=False, error_message="Ошибка проверки платежа")
    except Exception as e:
        logging.error(f"Ошибка в pre_checkout: {e}")
        await pre_checkout.answer(ok=False, error_message="Ошибка проверки платежа")

@dp.message(F.successful_payment)
async def successful_gift_payment(message: Message, state: FSMContext):
    """Обработчик успешной оплаты подарка звездами"""
    try:
        data = await state.get_data()
        gift = data.get('payment_gift')
        receiver_id = data.get('payment_receiver_id')
        receiver_username = data.get('payment_receiver_username')
        user_id = message.from_user.id
        
        if not gift:
            await message.answer("❌ Ошибка: данные о подарке не найдены")
            return
        
        # Получаем сумму из платежа
        stars_amount = message.successful_payment.total_amount
        
        # Отправляем подарок
        custom_emoji = get_custom_emoji(gift['custom_emoji_id'])
        
        await bot.send_gift(
            user_id=receiver_id,
            gift_id=gift['id'],
            text=f"Подарок от {message.from_user.first_name}! {custom_emoji}",
            text_parse_mode="HTML"
        )
        
        # Сохраняем транзакцию
        await add_transaction(
            user_id,
            "gift_purchase_stars",
            amount_stars=stars_amount,
            status="completed"
        )
        
        # Уведомляем получателя
        if receiver_id != user_id:
            try:
                await bot.send_message(
                    receiver_id,
                    f"🎁 Вам подарили подарок {custom_emoji}!\n"
                    f"От: {message.from_user.first_name}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        
        # Успех
        builder = InlineKeyboardBuilder()
        builder.button(text="🎁 Купить еще", callback_data="menu:buy_gift")
        builder.button(text="◀️ В меню", callback_data="back_to_menu")
        builder.adjust(1)
        
        await message.answer(
            f"✅ <b>Подарок успешно отправлен!</b>\n\n"
            f"👤 Получатель: {receiver_username}\n"
            f"🎀 Подарок: {custom_emoji} {gift['name']}\n"
            f"💰 Оплачено: {stars_amount} ⭐\n\n"
            f"Спасибо за покупку! 🎉",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
        await state.clear()
        
    except Exception as e:
        logging.error(f"Ошибка при успешной оплате подарка: {e}")
        await message.answer(f"❌ Ошибка при отправке подарка: {e}")

@dp.callback_query(F.data == "back_to_gifts")
async def back_to_gifts(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору подарков"""
    data = await state.get_data()
    receiver = data.get('receiver_username', 'не указан')
    
    # Получаем кастомные эмодзи для каждого подарка
    gift_emoji_1 = get_custom_emoji(GIFTS["gift_1"]["custom_emoji_id"])
    gift_emoji_2 = get_custom_emoji(GIFTS["gift_2"]["custom_emoji_id"])
    gift_emoji_3 = get_custom_emoji(GIFTS["gift_3"]["custom_emoji_id"])
    gift_emoji_4 = get_custom_emoji(GIFTS["gift_4"]["custom_emoji_id"])
    gift_emoji_5 = get_custom_emoji(GIFTS["gift_5"]["custom_emoji_id"])
    gift_emoji_6 = get_custom_emoji(GIFTS["gift_6"]["custom_emoji_id"])
    
    await callback.message.edit_text(
        f"🎁 <b>Выберите подарок</b>\n\n"
        f"👤 Получатель: {receiver}\n\n"
        f"Доступные подарки:\n"
        f"{gift_emoji_1} Подарок 1\n"
        f"{gift_emoji_2} Подарок 2\n"
        f"{gift_emoji_3} Подарок 3\n"
        f"{gift_emoji_4} Подарок 4\n"
        f"{gift_emoji_5} Подарок 5\n"
        f"{gift_emoji_6} Подарок 6\n\n"
        f"Нажмите на кнопку с номером подарка:",
        reply_markup=get_gift_selection_kb(),
        parse_mode="HTML"
    )
    await state.set_state(BuyGiftStates.waiting_for_gift_selection)
    await callback.answer()

@dp.callback_query(F.data == "admin_check_balance")
async def admin_check_balance(callback: CallbackQuery):
    """Админ проверяет баланс бота"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ У вас нет прав")
        return
    
    balance = await get_bot_stars_balance()
    await callback.message.edit_text(
        f"🤖 Баланс звезд бота: {balance} ⭐",
        reply_markup=get_back_to_menu_button()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_pay_help")
async def admin_pay_help(callback: CallbackQuery):
    """Помощь по пополнению"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ У вас нет прав")
        return
    
    await callback.message.edit_text(
        f"📖 <b>Инструкция по пополнению звезд бота</b>\n\n"
        f"1️⃣ Используйте команду /pay <количество>\n"
        f"   Пример: /pay 1000\n\n"
        f"2️⃣ Оплатите созданный чек\n\n"
        f"3️⃣ Используйте команду /add_balance <количество>\n"
        f"   Пример: /add_balance 1000\n\n"
        f"После этого звезды появятся на балансе бота.",
        parse_mode="HTML"
    )
    await callback.answer()