from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import dp, bot
from database import (get_balance, update_balance, add_transaction, 
                      create_purchase_request, update_purchase_request_status)
from keyboards import get_back_to_menu_button, get_cancel_button, get_currency_selection_kb
from utils import calculate_prices
from config import ADMIN_IDS, MIN_STARS_PURCHASE
import logging

class BuyStarsStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_currency = State()
    waiting_for_confirmation = State()

@dp.callback_query(F.data == "menu:buy_stars")
async def buy_stars_start(callback: CallbackQuery, state: FSMContext):
    """Начало процесса покупки звезд"""
    await callback.message.edit_text(
        f"⭐ <b>Покупка звезд</b>\n\n"
        f"💰 <b>Курс:</b>\n"
        f"1 ⭐ = 1.43 ₽\n"
        f"1 ⭐ = 0.017 $\n"
        f"1 ⭐ = 0.014 TON\n\n"
        f"📝 <b>Минимальная покупка:</b> {MIN_STARS_PURCHASE} ⭐\n\n"
        f"✍️ Введите количество звезд для покупки:",
        reply_markup=get_cancel_button(),
        parse_mode="HTML"
    )
    await state.set_state(BuyStarsStates.waiting_for_amount)
    await callback.answer()

@dp.message(BuyStarsStates.waiting_for_amount)
async def process_stars_amount(message: Message, state: FSMContext):
    """Обработка введенного количества звезд"""
    try:
        stars_amount = int(message.text.strip())
        
        if stars_amount < MIN_STARS_PURCHASE:
            await message.answer(
                f"❌ Минимальное количество звезд для покупки: {MIN_STARS_PURCHASE}\n"
                f"Пожалуйста, введите число больше или равное {MIN_STARS_PURCHASE}",
                reply_markup=get_cancel_button()
            )
            return
        
        # Сохраняем количество звезд
        await state.update_data(stars_amount=stars_amount)
        
        # Рассчитываем стоимость
        prices = calculate_prices(stars_amount)
        
        # Показываем пользователю информацию
        await message.answer(
            f"⭐ <b>Покупка {stars_amount} звезд</b>\n\n"
            f"💰 <b>Стоимость:</b>\n"
            f"₽ Рубли: {prices['rub']:.2f}\n"
            f"💵 Доллары: {prices['usd']:.2f}\n"
            f"💎 TON: {prices['ton']:.2f}\n\n"
            f"Выберите валюту для оплаты:",
            reply_markup=get_currency_selection_kb(stars_amount),
            parse_mode="HTML"
        )
        await state.set_state(BuyStarsStates.waiting_for_currency)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите целое число (количество звезд)",
            reply_markup=get_cancel_button()
        )

@dp.callback_query(BuyStarsStates.waiting_for_currency, F.data.startswith("pay_with_"))
async def process_currency_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора валюты (рубли, доллары, TON)"""
    data = await state.get_data()
    stars_amount = data.get('stars_amount')
    
    if not stars_amount:
        await callback.answer("❌ Ошибка, попробуйте снова")
        await state.clear()
        return
    
    # Разбираем callback_data
    # Формат: "pay_with_rub:100" или "pay_with_usd:100" или "pay_with_ton:100"
    callback_parts = callback.data.split(":")
    if len(callback_parts) < 2:
        await callback.answer("❌ Неверный формат")
        return
    
    # Получаем валюту из первой части: "pay_with_rub" -> "rub"
    currency = callback_parts[0].replace("pay_with_", "")
    
    # Проверяем, что валюта допустима
    if currency not in ['rub', 'usd', 'ton']:
        await callback.answer(f"❌ Неверная валюта: {currency}")
        return
    
    # Получаем количество звезд из callback_data (для проверки)
    callback_stars = int(callback_parts[1])
    if callback_stars != stars_amount:
        await callback.answer("❌ Ошибка: несоответствие суммы")
        return
    
    # Получаем текущий баланс пользователя
    balance = await get_balance(callback.from_user.id, currency)
    prices = calculate_prices(stars_amount)
    required_amount = prices[currency]
    
    # Сохраняем данные
    await state.update_data(
        stars_amount=stars_amount,
        selected_currency=currency,
        required_amount=required_amount
    )
    
    # Названия валют
    currency_names = {
        'rub': ('₽', 'Рубли'),
        'usd': ('$', 'Доллары'),
        'ton': ('TON', 'TON')
    }
    symbol, name = currency_names.get(currency, (currency.upper(), currency.upper()))
    
    if balance >= required_amount:
        # Достаточно средств - создаем заявку админу
        request_id = await create_purchase_request(
            callback.from_user.id, stars_amount, currency, required_amount
        )
        
        # Сохраняем request_id в состояние
        await state.update_data(request_id=request_id)
        
        # Показываем подтверждение
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Подтвердить", callback_data="confirm_purchase")
        builder.button(text="❌ Отмена", callback_data="cancel_action")
        builder.adjust(1)
        
        await callback.message.edit_text(
            f"⭐ <b>Подтверждение покупки</b>\n\n"
            f"Количество звезд: {stars_amount} ⭐\n"
            f"Валюта оплаты: {name}\n"
            f"Сумма: {required_amount:.2f} {symbol}\n"
            f"Текущий баланс: {balance:.2f} {symbol}\n\n"
            f"После подтверждения будет создана заявка для администратора.\n"
            f"Администратор проверит оплату и начислит звезды.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        await state.set_state(BuyStarsStates.waiting_for_confirmation)
        
    else:
        # Недостаточно средств
        builder = InlineKeyboardBuilder()
        builder.button(text="💰 Пополнить баланс", callback_data="menu:top_up")
        builder.button(text="◀️ Выбрать другую валюту", callback_data="change_currency")
        builder.button(text="❌ Отмена", callback_data="cancel_action")
        builder.adjust(1)
        
        await callback.message.edit_text(
            f"❌ <b>Недостаточно средств!</b>\n\n"
            f"💰 Ваш баланс: {balance:.2f} {symbol}\n"
            f"💎 Нужно: {required_amount:.2f} {symbol}\n\n"
            f"Выберите другую валюту или пополните баланс.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    
    await callback.answer()

@dp.callback_query(BuyStarsStates.waiting_for_currency)
async def debug_currency(callback: CallbackQuery):
    """Отладка для всех callback в этом состоянии"""
    print(f"DEBUG: Получен callback: {callback.data}")
    # Если не обработано выше, пропускаем
    await callback.answer()

@dp.callback_query(F.data == "change_currency")
async def change_currency(callback: CallbackQuery, state: FSMContext):
    """Смена валюты"""
    data = await state.get_data()
    stars_amount = data.get('stars_amount')
    
    prices = calculate_prices(stars_amount)
    
    await callback.message.edit_text(
        f"⭐ <b>Покупка {stars_amount} звезд</b>\n\n"
        f"💰 <b>Стоимость:</b>\n"
        f"₽ Рубли: {prices['rub']:.2f}\n"
        f"💵 Доллары: {prices['usd']:.2f}\n"
        f"💎 TON: {prices['ton']:.2f}\n\n"
        f"Выберите валюту для оплаты:",
        reply_markup=get_currency_selection_kb(stars_amount),
        parse_mode="HTML"
    )
    await state.set_state(BuyStarsStates.waiting_for_currency)
    await callback.answer()

@dp.callback_query(F.data == "confirm_purchase", BuyStarsStates.waiting_for_confirmation)
async def confirm_purchase(callback: CallbackQuery, state: FSMContext):
    """Подтверждение покупки - отправка заявки админу"""
    data = await state.get_data()
    stars_amount = data.get('stars_amount')
    currency = data.get('selected_currency')
    required_amount = data.get('required_amount')
    request_id = data.get('request_id')
    
    if not request_id:
        # Если нет request_id, создаем заново
        request_id = await create_purchase_request(
            callback.from_user.id, stars_amount, currency, required_amount
        )
    
    # Названия валют
    currency_names = {
        'rub': ('₽', 'Рубли'),
        'usd': ('$', 'Доллары'),
        'ton': ('TON', 'TON')
    }
    symbol, name = currency_names.get(currency, (currency.upper(), currency.upper()))
    
    # Отправляем уведомление админам
    for admin_id in ADMIN_IDS:
        try:
            kb = InlineKeyboardBuilder()
            kb.button(text="✅ Одобрить", callback_data=f"admin_approve:{request_id}")
            kb.button(text="❌ Отклонить", callback_data=f"admin_reject:{request_id}")
            kb.adjust(2)
            
            await bot.send_message(
                admin_id,
                f"🆕 <b>Новая заявка на покупку звезд!</b>\n\n"
                f"👤 Пользователь: {callback.from_user.first_name}\n"
                f"🆔 ID: {callback.from_user.id}\n"
                f"⭐ Количество звезд: {stars_amount}\n"
                f"💰 Валюта: {name}\n"
                f"💎 Сумма: {required_amount:.2f} {symbol}\n"
                f"📝 ID заявки: {request_id}\n\n"
                f"Списать средства и начислить звезды?",
                reply_markup=kb.as_markup(),
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления админу {admin_id}: {e}")
    
    # Уведомляем пользователя
    await callback.message.edit_text(
        f"✅ <b>Заявка на покупку создана!</b>\n\n"
        f"⭐ Звезды: {stars_amount}\n"
        f"💰 Валюта: {name}\n"
        f"💎 Сумма: {required_amount:.2f} {symbol}\n\n"
        f"Администратор рассмотрит вашу заявку в ближайшее время.\n"
        f"После подтверждения звезды будут начислены на ваш счет.",
        reply_markup=get_back_to_menu_button(),
        parse_mode="HTML"
    )
    
    await state.clear()
    await callback.answer()