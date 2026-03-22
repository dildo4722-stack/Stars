# admin_handlers.py оставляем только для обработки заявок на покупку звезд
from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import dp, bot
from database import (get_purchase_request, update_purchase_request_status, 
                      update_balance, add_transaction, get_user)
from keyboards import get_back_to_menu_button
from config import ADMIN_IDS
import logging

@dp.callback_query(F.data.startswith("admin_approve:"))
async def approve_purchase(callback: CallbackQuery):
    """Одобрение заявки на покупку звезд"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ У вас нет прав для этого действия")
        return
    
    request_id = int(callback.data.split(":")[1])
    request = await get_purchase_request(request_id)
    
    if not request or request['status'] != 'pending':
        await callback.answer("❌ Заявка уже обработана")
        return
    
    user_id = request['user_id']
    stars_amount = request['stars_amount']
    currency = request['currency']
    amount = request['amount']
    
    # Списываем средства у пользователя
    if currency == 'rub':
        await update_balance(user_id, rub=-amount)
    elif currency == 'usd':
        await update_balance(user_id, usd=-amount)
    elif currency == 'ton':
        await update_balance(user_id, ton=-amount)
    
    # Начисляем звезды
    await update_balance(user_id, stars=stars_amount)
    
    # Сохраняем транзакцию
    await add_transaction(
        user_id,
        "stars_purchase",
        amount_rub=amount if currency == 'rub' else 0,
        amount_stars=stars_amount,
        amount_ton=amount if currency == 'ton' else 0,
        amount_usd=amount if currency == 'usd' else 0,
        status="completed",
        admin_id=callback.from_user.id
    )
    
    # Обновляем статус заявки
    await update_purchase_request_status(request_id, "approved")
    
    # Уведомляем пользователя
    try:
        currency_names = {'rub': '₽', 'usd': '$', 'ton': 'TON'}
        currency_symbol = currency_names.get(currency, currency.upper())
        
        await bot.send_message(
            user_id,
            f"✅ <b>Ваша заявка на покупку одобрена!</b>\n\n"
            f"⭐ Начислено звезд: {stars_amount}\n"
            f"💰 Списано: {amount:.2f} {currency_symbol}\n\n"
            f"Спасибо за покупку!",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка при уведомлении пользователя {user_id}: {e}")
    
    # Уведомляем админа
    await callback.message.edit_text(
        f"✅ <b>Заявка #{request_id} одобрена</b>\n\n"
        f"👤 Пользователь: {callback.from_user.first_name}\n"
        f"⭐ Начислено звезд: {stars_amount}\n"
        f"💰 Списано: {amount:.2f} {currency.upper()}\n\n"
        f"Операция выполнена успешно.",
        reply_markup=get_back_to_menu_button()
    )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_reject:"))
async def reject_purchase(callback: CallbackQuery):
    """Отклонение заявки на покупку звезд"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ У вас нет прав для этого действия")
        return
    
    request_id = int(callback.data.split(":")[1])
    request = await get_purchase_request(request_id)
    
    if not request or request['status'] != 'pending':
        await callback.answer("❌ Заявка уже обработана")
        return
    
    user_id = request['user_id']
    stars_amount = request['stars_amount']
    currency = request['currency']
    amount = request['amount']
    
    # Обновляем статус заявки
    await update_purchase_request_status(request_id, "rejected")
    
    # Сохраняем транзакцию
    await add_transaction(
        user_id,
        "stars_purchase",
        amount_rub=amount if currency == 'rub' else 0,
        amount_stars=stars_amount,
        amount_ton=amount if currency == 'ton' else 0,
        amount_usd=amount if currency == 'usd' else 0,
        status="rejected",
        admin_id=callback.from_user.id
    )
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            user_id,
            f"❌ <b>Ваша заявка на покупку отклонена</b>\n\n"
            f"⭐ Звезды: {stars_amount}\n"
            f"💰 Сумма: {amount:.2f} {currency.upper()}\n\n"
            f"Причина: не прошла проверку администратором.\n"
            f"Пожалуйста, создайте новую заявку.",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка при уведомлении пользователя {user_id}: {e}")
    
    # Уведомляем админа
    await callback.message.edit_text(
        f"❌ <b>Заявка #{request_id} отклонена</b>\n\n"
        f"👤 Пользователь: {callback.from_user.first_name}\n"
        f"⭐ Звезды: {stars_amount}\n"
        f"💰 Сумма: {amount:.2f} {currency.upper()}\n\n"
        f"Заявка отклонена.",
        reply_markup=get_back_to_menu_button()
    )
    
    await callback.answer()