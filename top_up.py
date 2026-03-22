from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command

from bot_instance import dp, bot
from database import update_balance, add_transaction, get_user
from keyboards import get_back_to_menu_button, get_cancel_button
from config import ADMIN_IDS
import logging
import random
import string
import urllib.parse

# Состояния для пополнения баланса
class TopUpStates(StatesGroup):
    waiting_for_currency = State()
    waiting_for_amount = State()
    waiting_for_card_name = State()
    waiting_for_payment_confirmation = State()

# Хранилище заявок на пополнение
pending_topups = {}

def generate_code(length=8):
    """Генерация 8-значного кода"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# Реквизиты для пополнения
TON_WALLET = "UQDaNeHFZYWLv1mnMUD0HJamNBMMvZ3jlcqj4vBng6n8BKGM"
RUB_CARD = "89029412268"
RUB_NAME = "Анатолий Л"
RUB_BANK = "Альфа Банк"
USD_LINK = "http://t.me/send?start=IVtUkRSPQ52"

@dp.callback_query(F.data == "menu:top_up")
async def top_up_start(callback: CallbackQuery, state: FSMContext):
    """Начало пополнения баланса - выбор валюты"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💎 TON", callback_data="topup_currency:TON")
    builder.button(text="₽ Рубли", callback_data="topup_currency:RUB")
    builder.button(text="💵 Доллары (USDT)", callback_data="topup_currency:USD")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "💰 <b>Пополнение баланса</b>\n\n"
        "Выберите валюту для пополнения:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(TopUpStates.waiting_for_currency)
    await callback.answer()

@dp.callback_query(TopUpStates.waiting_for_currency, F.data.startswith("topup_currency:"))
async def select_currency(callback: CallbackQuery, state: FSMContext):
    """Выбор валюты - запрос суммы"""
    currency = callback.data.split(":")[1]
    await state.update_data(currency=currency)
    
    await callback.message.edit_text(
        f"💰 <b>Пополнение баланса</b>\n\n"
        f"Валюта: {currency}\n\n"
        f"✍️ Введите сумму пополнения:\n\n"
        f"{'<i>Минимальная сумма: 1 TON</i>' if currency == 'TON' else ''}"
        f"{'<i>Минимальная сумма: 10 ₽</i>' if currency == 'RUB' else ''}"
        f"{'<i>Минимальная сумма: 9 $ ( +0.1$ комиссия)</i>' if currency == 'USD' else ''}",
        reply_markup=get_cancel_button(),
        parse_mode="HTML"
    )
    await state.set_state(TopUpStates.waiting_for_amount)
    await callback.answer()

@dp.message(TopUpStates.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    """Обработка суммы пополнения"""
    try:
        amount = float(message.text.strip())
        data = await state.get_data()
        currency = data.get('currency')
        
        # Проверки минимальной суммы
        if currency == 'TON' and amount < 1:
            await message.answer("❌ Минимальная сумма для пополнения TON: 1 TON\nВведите другую сумму:")
            return
        elif currency == 'RUB' and amount <10:
            await message.answer("❌ Минимальная сумма для пополнения: 10 ₽\nВведите другую сумму:")
            return
        elif currency == 'USD' and amount < 1:
            await message.answer("❌ Минимальная сумма для пополнения: 10 $\nВведите другую сумму:")
            return
        
        await state.update_data(amount=amount)
        
        if currency == 'RUB':
            # Для рублей запрашиваем инициалы
            await message.answer(
                f"💰 <b>Пополнение баланса</b>\n\n"
                f"Сумма: {amount} ₽\n\n"
                f"📝 <b>Реквизиты для перевода:</b>\n"
                f"📞 Номер: <code>{RUB_CARD}</code>\n"
                f"👤 Инициалы: {RUB_NAME}\n"
                f"🏦 Банк: {RUB_BANK}\n\n"
                f"❌ <b>ВНИМАНИЕ!</b> Переводы с других банков не принимаются!\n\n"
                f"✍️ Введите ваши инициалы (как на карте) для проверки платежа:",
                reply_markup=get_cancel_button(),
                parse_mode="HTML"
            )
            await state.set_state(TopUpStates.waiting_for_card_name)
        else:
            # Для TON и USD показываем реквизиты
            await show_payment_details(message, state, amount, currency)
            
    except ValueError:
        await message.answer("❌ Введите число (сумму пополнения):", reply_markup=get_cancel_button())

@dp.message(TopUpStates.waiting_for_card_name)
async def process_card_name(message: Message, state: FSMContext):
    """Обработка инициалов для рублевого перевода"""
    card_name = message.text.strip()
    data = await state.get_data()
    amount = data.get('amount')
    
    await state.update_data(card_name=card_name)
    await show_payment_details(message, state, amount, 'RUB', card_name)

async def show_payment_details(message: Message, state: FSMContext, amount: float, currency: str, card_name: str = None):
    """Показ реквизитов и создание заявки"""
    user_id = message.from_user.id
    user = await get_user(user_id)
    username = user.get('username') or message.from_user.username or str(user_id)
    
    # Генерируем уникальный код для платежа
    payment_code = generate_code()
    
    # Сохраняем заявку
    topup_data = {
        'user_id': user_id,
        'username': username,
        'amount': amount,
        'currency': currency,
        'payment_code': payment_code,
        'card_name': card_name if currency == 'RUB' else None,
        'status': 'pending'
    }
    
    # Сохраняем в состояние и в общее хранилище
    await state.update_data(topup_data=topup_data)
    pending_topups[payment_code] = topup_data
    
    # Формируем сообщение с реквизитами
    if currency == 'TON':
        text = (
            f"💰 <b>Пополнение баланса</b>\n\n"
            f"Сумма: {amount} TON\n"
            f"Валюта: TON\n\n"
            f"📝 <b>Реквизиты для перевода:</b>\n"
            f"💎 Кошелек TON:\n"
            f"<code>{TON_WALLET}</code>\n\n"
            f"🔑 <b>Ваш уникальный код для перевода:</b>\n"
            f"<code>{payment_code}</code>\n\n"
            f"⚠️ <b>ВАЖНО!</b>\n"
            f"1️⃣ Переведите точную сумму: {amount} TON\n"
            f"2️⃣ В комментарии к переводу укажите код: <code>{payment_code}</code>\n"
            f"3️⃣ После перевода нажмите кнопку «Я оплатил»\n\n"
            f"⏱ Без кода платеж не будет идентифицирован!"
        )
    elif currency == 'RUB':
        text = (
            f"💰 <b>Пополнение баланса</b>\n\n"
            f"Сумма: {amount} ₽\n"
            f"Валюта: Рубли\n\n"
            f"📝 <b>Реквизиты для перевода:</b>\n"
            f"📞 Номер: <code>{RUB_CARD}</code>\n"
            f"👤 Инициалы: {RUB_NAME}\n"
            f"🏦 Банк: {RUB_BANK}\n"
            f"👤 Ваши инициалы: {card_name}\n\n"
            f"🔑 <b>Ваш уникальный код:</b>\n"
            f"<code>{payment_code}</code>\n\n"
            f"⚠️ <b>ВАЖНО!</b>\n"
            f"1️⃣ Переведите точную сумму: {amount} ₽\n"
            f"2️⃣ В комментарии к переводу укажите код: <code>{payment_code}</code>\n"
            f"3️⃣ После перевода нажмите кнопку «Я оплатил»\n\n"
            f"❌ Переводы с других банков не принимаются!\n"
            f"⏱ Без кода платеж не будет идентифицирован!"
        )
    else:  # USD
        # Добавляем комиссию
        final_amount = amount + 0.1
        text = (
            f"💰 <b>Пополнение баланса</b>\n\n"
            f"Сумма к зачислению: {amount} $\n"
            f"Комиссия: 0.1 $\n"
            f"<b>Итого к оплате: {final_amount:.2f} $</b>\n\n"
            f"📝 <b>Ссылка для оплаты:</b>\n"
            f"<a href=\"{USD_LINK}\">💳 Оплатить через @send</a>\n\n"
            f"🔑 <b>Ваш уникальный код:</b>\n"
            f"<code>{payment_code}</code>\n\n"
            f"⚠️ <b>ВАЖНО!</b>\n"
            f"1️⃣ Перейдите по ссылке и оплатите {final_amount:.2f} $\n"
            f"2️⃣ В комментарии к оплате укажите код: <code>{payment_code}</code>\n"
            f"3️⃣ После оплаты нажмите кнопку «Я оплатил»\n\n"
            f"⏱ Без кода платеж не будет идентифицирован!"
        )
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    if currency == 'USD':
        builder.button(text="💳 Оплатить", url=USD_LINK)
    builder.button(text="✅ Я оплатил", callback_data=f"confirm_topup:{payment_code}")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1)
    
    await message.answer(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await state.set_state(TopUpStates.waiting_for_payment_confirmation)

@dp.callback_query(TopUpStates.waiting_for_payment_confirmation, F.data.startswith("confirm_topup:"))
async def confirm_topup(callback: CallbackQuery, state: FSMContext):
    """Подтверждение оплаты - отправка заявки админам"""
    payment_code = callback.data.split(":")[1]
    data = await state.get_data()
    topup_data = data.get('topup_data')
    
    if not topup_data or topup_data.get('payment_code') != payment_code:
        await callback.answer("❌ Ошибка, попробуйте снова")
        return
    
    # Отправляем уведомление админам
    for admin_id in ADMIN_IDS:
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Подтвердить", callback_data=f"approve_topup:{payment_code}")
        builder.button(text="❌ Отклонить", callback_data=f"reject_topup:{payment_code}")
        builder.adjust(2)
        
        await bot.send_message(
            admin_id,
            f"🆕 <b>Новая заявка на пополнение!</b>\n\n"
            f"👤 Пользователь: {topup_data['username']}\n"
            f"🆔 ID: {topup_data['user_id']}\n"
            f"💰 Сумма: {topup_data['amount']} {topup_data['currency']}\n"
            f"🔑 Код: <code>{payment_code}</code>\n"
            f"{'👤 Инициалы: ' + topup_data['card_name'] if topup_data.get('card_name') else ''}\n\n"
            f"Проверьте поступление средств и подтвердите заявку.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    
    await callback.message.edit_text(
        f"✅ <b>Заявка на пополнение создана!</b>\n\n"
        f"💰 Сумма: {topup_data['amount']} {topup_data['currency']}\n"
        f"🔑 Код: <code>{payment_code}</code>\n\n"
        f"Администратор проверит поступление средств.\n"
        f"После подтверждения баланс будет пополнен.\n\n"
        f"Ожидайте уведомления.",
        reply_markup=get_back_to_menu_button(),
        parse_mode="HTML"
    )
    
    await state.clear()
    await callback.answer()

# ==================== АДМИН-КОМАНДЫ ДЛЯ ЗАЯВОК ====================

@dp.message(Command("app"))
async def show_pending_topups(message: Message):
    """Показать все ожидающие заявки на пополнение"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет прав")
        return
    
    pending = [t for t in pending_topups.values() if t['status'] == 'pending']
    
    if not pending:
        await message.answer("📭 Нет ожидающих заявок на пополнение.")
        return
    
    text = "📋 <b>Ожидающие заявки на пополнение:</b>\n\n"
    for t in pending:
        text += (
            f"👤 {t['username']} (ID: {t['user_id']})\n"
            f"💰 {t['amount']} {t['currency']}\n"
            f"🔑 Код: <code>{t['payment_code']}</code>\n"
            f"{'👤 Инициалы: ' + t['card_name'] if t.get('card_name') else ''}\n"
            f"➖➖➖➖➖➖➖➖\n"
        )
    
    await message.answer(text, parse_mode="HTML")

@dp.callback_query(F.data.startswith("approve_topup:"))
async def approve_topup(callback: CallbackQuery):
    """Админ подтверждает пополнение"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ У вас нет прав")
        return
    
    payment_code = callback.data.split(":")[1]
    topup = pending_topups.get(payment_code)
    
    if not topup or topup['status'] != 'pending':
        await callback.answer("❌ Заявка уже обработана")
        return
    
    # Начисляем средства
    user_id = topup['user_id']
    amount = topup['amount']
    currency = topup['currency']
    
    if currency == 'TON':
        await update_balance(user_id, ton=amount)
    elif currency == 'RUB':
        await update_balance(user_id, rub=amount)
    elif currency == 'USD':
        await update_balance(user_id, usd=amount)
    
    # Сохраняем транзакцию
    await add_transaction(
        user_id,
        "top_up",
        amount_rub=amount if currency == 'RUB' else 0,
        amount_ton=amount if currency == 'TON' else 0,
        amount_usd=amount if currency == 'USD' else 0,
        status="completed",
        admin_id=callback.from_user.id,
        comment=f"Пополнение через {currency}, код: {payment_code}"
    )
    
    # Обновляем статус
    topup['status'] = 'approved'
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            user_id,
            f"✅ <b>Ваш баланс пополнен!</b>\n\n"
            f"💰 Сумма: {amount} {currency}\n"
            f"🔑 Код: <code>{payment_code}</code>\n\n"
            f"Спасибо за пополнение!",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка уведомления пользователя: {e}")
    
    await callback.message.edit_text(
        f"✅ <b>Заявка #{payment_code} подтверждена</b>\n\n"
        f"👤 Пользователь: {topup['username']}\n"
        f"💰 Начислено: {amount} {currency}",
        reply_markup=get_back_to_menu_button()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_topup:"))
async def reject_topup(callback: CallbackQuery):
    """Админ отклоняет пополнение"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ У вас нет прав")
        return
    
    payment_code = callback.data.split(":")[1]
    topup = pending_topups.get(payment_code)
    
    if not topup or topup['status'] != 'pending':
        await callback.answer("❌ Заявка уже обработана")
        return
    
    # Обновляем статус
    topup['status'] = 'rejected'
    
    # Сохраняем транзакцию
    await add_transaction(
        topup['user_id'],
        "top_up",
        status="rejected",
        admin_id=callback.from_user.id,
        comment=f"Отклонено, код: {payment_code}"
    )
    
    # Уведомляем пользователя
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆘 Техподдержка", callback_data="menu:support")]
        ])
        
        await bot.send_message(
            topup['user_id'],
            f"❌ <b>Ваша заявка на пополнение отклонена</b>\n\n"
            f"💰 Сумма: {topup['amount']} {topup['currency']}\n"
            f"🔑 Код: <code>{payment_code}</code>\n\n"
            f"Возможные причины:\n"
            f"• Средства не поступили\n"
            f"• Неверная сумма или код\n\n"
            f"Если вы уверены, что оплата прошла, обратитесь в техподдержку.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка уведомления пользователя: {e}")
    
    await callback.message.edit_text(
        f"❌ <b>Заявка #{payment_code} отклонена</b>\n\n"
        f"👤 Пользователь: {topup['username']}\n"
        f"💰 Сумма: {topup['amount']} {topup['currency']}",
        reply_markup=get_back_to_menu_button()
    )
    await callback.answer()