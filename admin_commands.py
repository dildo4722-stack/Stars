from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import PreCheckoutQuery, LabeledPrice, SuccessfulPayment
import uuid
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import dp, bot
from database import (get_user, update_balance, add_transaction, 
                      get_bot_stars_balance, update_bot_stars_balance,
                      get_all_users, register_user)
from config import ADMIN_IDS, STAR_PRICE_RUB, STAR_PRICE_USD, STAR_PRICE_TON
import logging
import asyncio

# Состояния для админ-команд
class AdminStates(StatesGroup):
    waiting_for_pay_amount = State()  # Для /pay
    waiting_for_broadcast_message = State()  # Для /rass

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

async def find_user(identifier: str):
    """Поиск пользователя по ID или username"""
    # Если это ID (число)
    if identifier.isdigit():
        return await get_user(int(identifier))
    
    # Если это username (с @ или без)
    username = identifier.replace('@', '').lower()
    from database import get_user_by_username
    return await get_user_by_username(username)

# ==================== КОМАНДА /AHELP ====================
@dp.message(Command("ahelp"))
async def admin_help(message: Message):
    """Список всех админ-команд"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    help_text = """
👑 <b>Админ-панель бота</b>

<b>📊 Управление балансами пользователей:</b>
• <code>/add_stars &lt;юзер/айди&gt; &lt;количество&gt;</code> - добавить звезды
• <code>/add_rub &lt;юзер/айди&gt; &lt;количество&gt;</code> - добавить рубли
• <code>/add_ton &lt;юзер/айди&gt; &lt;количество&gt;</code> - добавить TON
• <code>/add_usdt &lt;юзер/айди&gt; &lt;количество&gt;</code> - добавить USDT

<b>⭐ Управление звездами бота:</b>
• <code>/pay &lt;количество&gt;</code> - создать чек на покупку звезд для бота
• <code>/bot_balance</code> - проверить баланс звезд бота
• <code>/add_balance &lt;количество&gt;</code> - визуально пополнить баланс бота(обязательно после каждого пополнения)

<b>📢 Рассылка:</b>
• <code>/rass</code> - начать рассылку сообщения всем пользователям

<b>📊 Статистика:</b>
• <code>/stats</code> - показать статистику бота
• <code>/users</code> - список всех пользователей

<b>ℹ️ Другое:</b>
• <code>/ahelp</code> - показать это сообщение
• <code>/app</code> - посмотреть заявки на вывод

<b>Примеры:</b>
• <code>/add_stars @username 100</code>
• <code>/add_rub 123456789 50.5</code>
• <code>/pay 1000</code>
"""
    
    await message.answer(help_text, parse_mode="HTML")

# ==================== КОМАНДА /ADD_STARS ====================
@dp.message(Command("add_stars"))
async def add_stars(message: Message):
    """Добавление звезд на счет пользователя"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Использование: /add_stars <юзернейм или ID> <количество>\n"
            "Примеры:\n"
            "/add_stars @username 100\n"
            "/add_stars 123456789 50",
            parse_mode="HTML"
        )
        return
    
    user_identifier = args[1]
    try:
        amount = int(args[2])
        if amount <= 0:
            await message.answer("❌ Количество должно быть положительным числом.")
            return
    except ValueError:
        await message.answer("❌ Количество должно быть целым числом.")
        return
    
    # Поиск пользователя
    user = await find_user(user_identifier)
    if not user:
        await message.answer(f"❌ Пользователь {user_identifier} не найден в базе данных.")
        return
    
    old_balance = user.get('balance_stars', 0)
    new_balance = old_balance + amount
    
    # Добавляем звезды
    await update_balance(user['user_id'], stars=amount)
    
    # Сохраняем транзакцию
    await add_transaction(
        user['user_id'],
        "admin_add_stars",
        amount_stars=amount,
        status="completed",
        admin_id=message.from_user.id,
        comment=f"Админ добавил {amount} звезд"
    )
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            user['user_id'],
            f"✅ <b>Пополнение баланса</b>\n\n"
            f"⭐ Вам начислено: {amount} звезд\n"
            f"👨‍💼 Администратор: {message.from_user.first_name}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    await message.answer(
        f"✅ <b>Баланс обновлен</b>\n\n"
        f"👤 Пользователь: {user['first_name']} (@{user.get('username', 'нет')})\n"
        f"🆔 ID: {user['user_id']}\n"
        f"⭐ Добавлено: {amount} звезд\n"
        f"💳 Старый баланс: {old_balance} звезд\n"
        f"💳 Новый баланс: {new_balance} звезд",
        parse_mode="HTML"
    )

# ==================== КОМАНДА /ADD_RUB ====================
@dp.message(Command("add_rub"))
async def add_rub(message: Message):
    """Добавление рублей на счет пользователя"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Использование: /add_rub <юзернейм или ID> <количество>\n"
            "Примеры:\n"
            "/add_rub @username 100\n"
            "/add_rub 123456789 50.5",
            parse_mode="HTML"
        )
        return
    
    user_identifier = args[1]
    try:
        amount = float(args[2])
        if amount <= 0:
            await message.answer("❌ Количество должно быть положительным числом.")
            return
    except ValueError:
        await message.answer("❌ Количество должно быть числом.")
        return
    
    # Поиск пользователя
    user = await find_user(user_identifier)
    if not user:
        await message.answer(f"❌ Пользователь {user_identifier} не найден в базе данных.")
        return
    
    old_balance = user.get('balance_rub', 0)
    new_balance = old_balance + amount
    
    # Добавляем рубли
    await update_balance(user['user_id'], rub=amount)
    
    # Сохраняем транзакцию
    await add_transaction(
        user['user_id'],
        "admin_add_rub",
        amount_rub=amount,
        status="completed",
        admin_id=message.from_user.id,
        comment=f"Админ добавил {amount} руб"
    )
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            user['user_id'],
            f"✅ <b>Пополнение баланса</b>\n\n"
            f"💰 Вам начислено: {amount:.2f} ₽\n"
            f"👨‍💼 Администратор: {message.from_user.first_name}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    await message.answer(
        f"✅ <b>Баланс обновлен</b>\n\n"
        f"👤 Пользователь: {user['first_name']} (@{user.get('username', 'нет')})\n"
        f"🆔 ID: {user['user_id']}\n"
        f"💰 Добавлено: {amount:.2f} ₽\n"
        f"💳 Старый баланс: {old_balance:.2f} ₽\n"
        f"💳 Новый баланс: {new_balance:.2f} ₽",
        parse_mode="HTML"
    )

# ==================== КОМАНДА /ADD_TON ====================
@dp.message(Command("add_ton"))
async def add_ton(message: Message):
    """Добавление TON на счет пользователя"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Использование: /add_ton <юзернейм или ID> <количество>\n"
            "Примеры:\n"
            "/add_ton @username 100\n"
            "/add_ton 123456789 50.5",
            parse_mode="HTML"
        )
        return
    
    user_identifier = args[1]
    try:
        amount = float(args[2])
        if amount <= 0:
            await message.answer("❌ Количество должно быть положительным числом.")
            return
    except ValueError:
        await message.answer("❌ Количество должно быть числом.")
        return
    
    # Поиск пользователя
    user = await find_user(user_identifier)
    if not user:
        await message.answer(f"❌ Пользователь {user_identifier} не найден в базе данных.")
        return
    
    old_balance = user.get('balance_ton', 0)
    new_balance = old_balance + amount
    
    # Добавляем TON
    await update_balance(user['user_id'], ton=amount)
    
    # Сохраняем транзакцию
    await add_transaction(
        user['user_id'],
        "admin_add_ton",
        amount_ton=amount,
        status="completed",
        admin_id=message.from_user.id,
        comment=f"Админ добавил {amount} TON"
    )
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            user['user_id'],
            f"✅ <b>Пополнение баланса</b>\n\n"
            f"💎 Вам начислено: {amount:.2f} TON\n"
            f"👨‍💼 Администратор: {message.from_user.first_name}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    await message.answer(
        f"✅ <b>Баланс обновлен</b>\n\n"
        f"👤 Пользователь: {user['first_name']} (@{user.get('username', 'нет')})\n"
        f"🆔 ID: {user['user_id']}\n"
        f"💎 Добавлено: {amount:.2f} TON\n"
        f"💳 Старый баланс: {old_balance:.2f} TON\n"
        f"💳 Новый баланс: {new_balance:.2f} TON",
        parse_mode="HTML"
    )

# ==================== КОМАНДА /ADD_USDT ====================
@dp.message(Command("add_usdt"))
async def add_usdt(message: Message):
    """Добавление USDT на счет пользователя"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Использование: /add_usdt <юзернейм или ID> <количество>\n"
            "Примеры:\n"
            "/add_usdt @username 100\n"
            "/add_usdt 123456789 50.5",
            parse_mode="HTML"
        )
        return
    
    user_identifier = args[1]
    try:
        amount = float(args[2])
        if amount <= 0:
            await message.answer("❌ Количество должно быть положительным числом.")
            return
    except ValueError:
        await message.answer("❌ Количество должно быть числом.")
        return
    
    # Поиск пользователя
    user = await find_user(user_identifier)
    if not user:
        await message.answer(f"❌ Пользователь {user_identifier} не найден в базе данных.")
        return
    
    old_balance = user.get('balance_usd', 0)
    new_balance = old_balance + amount
    
    # Добавляем USDT (храним в balance_usd)
    await update_balance(user['user_id'], usd=amount)
    
    # Сохраняем транзакцию
    await add_transaction(
        user['user_id'],
        "admin_add_usdt",
        amount_usd=amount,
        status="completed",
        admin_id=message.from_user.id,
        comment=f"Админ добавил {amount} USDT"
    )
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            user['user_id'],
            f"✅ <b>Пополнение баланса</b>\n\n"
            f"💵 Вам начислено: {amount:.2f} USDT\n"
            f"👨‍💼 Администратор: {message.from_user.first_name}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    await message.answer(
        f"✅ <b>Баланс обновлен</b>\n\n"
        f"👤 Пользователь: {user['first_name']} (@{user.get('username', 'нет')})\n"
        f"🆔 ID: {user['user_id']}\n"
        f"💵 Добавлено: {amount:.2f} USDT\n"
        f"💳 Старый баланс: {old_balance:.2f} USDT\n"
        f"💳 Новый баланс: {new_balance:.2f} USDT",
        parse_mode="HTML"
    )

# ==================== КОМАНДА /PAY ====================
@dp.message(Command("pay"))
async def cmd_pay(message: Message, state: FSMContext):
    """Команда для оплаты звездами: /pay 2"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer(
                "❌ Использование: /pay <количество звезд>\n"
                "Пример: /pay 1000\n\n"
                "⭐ Количество звезд от 1 до 2500"
            )
            return
        
        stars_amount = int(args[1])
        if stars_amount < 1 or stars_amount > 2500:
            await message.answer("❌ Количество звезд должно быть от 1 до 2500")
            return
        
        payload = f"bot_stars_{message.from_user.id}_{uuid.uuid4().hex[:8]}"
        
        await state.update_data(stars_amount=stars_amount, payload=payload)
        
        kb = InlineKeyboardBuilder()
        kb.button(text=f"💳 Оплатить {stars_amount} ⭐", pay=True)
        kb.button(text="❌ Отмена", callback_data="cancel_payment")
        kb.adjust(1)
        
        # Удаляем команду
        await message.delete()
        
        # Отправляем инвойс
        await message.answer_invoice(
            title=f"⭐ Пополнение баланса бота",
            description=f"Пополнение баланса звезд бота на {stars_amount} ⭐",
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=f"{stars_amount} Stars", amount=stars_amount)],
            reply_markup=kb.as_markup(),
            start_parameter="bot_stars_topup"
        )
        
    except ValueError:
        await message.answer("❌ Введите число, например: /pay 1000")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout: PreCheckoutQuery, state: FSMContext):
    """Обработчик проверки платежа для пополнения бота"""
    try:
        data = await state.get_data()
        # Используем invoice_payload
        if data.get('payload') == pre_checkout.invoice_payload:
            await pre_checkout.answer(ok=True)
        else:
            await pre_checkout.answer(ok=False, error_message="Ошибка проверки платежа")
    except Exception as e:
        logging.error(f"Ошибка в pre_checkout: {e}")
        await pre_checkout.answer(ok=False, error_message="Ошибка проверки платежа")

@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message, state: FSMContext):
    """Обработчик успешной оплаты"""
    payment = message.successful_payment
    stars_amount = payment.total_amount
    
    await update_bot_stars_balance(stars_amount)
    
    await add_transaction(
        user_id=message.from_user.id,
        type="bot_stars_topup",
        amount_stars=stars_amount,
        status="completed",
        comment=f"Пополнение через Telegram Stars"
    )
    
    await message.answer(f"✅ Баланс бота пополнен на {stars_amount} ⭐")
    await state.clear()

@dp.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    """Отмена оплаты"""
    await state.clear()
    # Удаляем сообщение с кнопкой оплаты
    await callback.message.delete()
    # Отправляем новое сообщение об отмене
    await callback.message.answer("❌ Оплата отменена.")
    await callback.answer()
# ==================== КОМАНДА /BOT_BALANCE ====================
@dp.message(Command("bot_balance"))
async def bot_balance(message: Message):
    """Проверка баланса звезд бота"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    balance = await get_bot_stars_balance()
    
    await message.answer(
        f"🤖 <b>Баланс звезд бота</b>\n\n"
        f"⭐ Доступно звезд: {balance}\n\n"
        f"💰 <b>Стоимость пополнения:</b>\n"
        f"1000 ⭐ = {1000 * STAR_PRICE_RUB:.2f} ₽\n"
        f"5000 ⭐ = {5000 * STAR_PRICE_RUB:.2f} ₽\n"
        f"10000 ⭐ = {10000 * STAR_PRICE_RUB:.2f} ₽",
        parse_mode="HTML"
    )

# ==================== КОМАНДА /RASS ====================
@dp.message(Command("rass"))
async def start_broadcast(message: Message, state: FSMContext):
    """Начало рассылки сообщения всем пользователям"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    await message.answer(
        "📢 <b>Рассылка сообщения</b>\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям.\n"
        "Можно использовать HTML форматирование.\n\n"
        "Для отмены отправьте /cancel",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_broadcast_message)

@dp.message(AdminStates.waiting_for_broadcast_message)
async def process_broadcast(message: Message, state: FSMContext):
    """Обработка сообщения для рассылки"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Рассылка отменена.")
        return
    
    broadcast_text = message.text
    await message.answer(
        "📢 <b>Начинаю рассылку...</b>\n\n"
        "Это может занять некоторое время.",
        parse_mode="HTML"
    )
    
    # Получаем всех пользователей
    users = await get_all_users()
    total_users = len(users)
    success = 0
    failed = 0
    
    # Отправляем сообщение каждому пользователю
    for user in users:
        try:
            await bot.send_message(
                user['user_id'],
                broadcast_text,
                parse_mode="HTML"
            )
            success += 1
        except Exception as e:
            failed += 1
            logging.error(f"Ошибка отправки пользователю {user['user_id']}: {e}")
        
        # Небольшая задержка, чтобы не превысить лимиты
        await asyncio.sleep(0.05)
    
    # Отчет о рассылке
    await message.answer(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"📊 Всего пользователей: {total_users}\n"
        f"✅ Успешно доставлено: {success}\n"
        f"❌ Не доставлено: {failed}",
        parse_mode="HTML"
    )
    
    await state.clear()

# Добавьте в admin_commands.py

@dp.message(Command("add_balance"))
async def add_balance(message: Message):
    """Добавление звезд на баланс бота: /add_balance 1000"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Использование: /add_balance <количество звезд>\n"
            "Пример: /add_balance 1000\n\n"
            "Используйте после пополнения звезд через /pay"
        )
        return
    
    try:
        stars_amount = int(args[1])
        if stars_amount <= 0:
            await message.answer("❌ Количество должно быть положительным числом.")
            return
    except ValueError:
        await message.answer("❌ Количество должно быть целым числом.")
        return
    
    # Добавляем звезды на баланс бота
    await update_bot_stars_balance(stars_amount)
    new_balance = await get_bot_stars_balance()
    
    await message.answer(
        f"✅ <b>Баланс бота пополнен!</b>\n\n"
        f"⭐ Добавлено звезд: {stars_amount}\n"
        f"💳 Новый баланс бота: {new_balance} ⭐",
        parse_mode="HTML"
    )
# ==================== КОМАНДА /STATS ====================
@dp.message(Command("stats"))
async def show_stats(message: Message):
    """Показать статистику бота"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    users = await get_all_users()
    total_users = len(users)
    bot_stars = await get_bot_stars_balance()
    
    # Подсчитываем общие балансы
    total_rub = sum(user.get('balance_rub', 0) for user in users)
    total_stars = sum(user.get('balance_stars', 0) for user in users)
    total_ton = sum(user.get('balance_ton', 0) for user in users)
    total_usd = sum(user.get('balance_usd', 0) for user in users)
    
    await message.answer(
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f"Всего: {total_users}\n\n"
        f"💰 <b>Общие балансы пользователей:</b>\n"
        f"⭐ Звезды: {total_stars:.0f}\n"
        f"₽ Рубли: {total_rub:.2f}\n"
        f"💵 Доллары: {total_usd:.2f}\n"
        f"💎 TON: {total_ton:.2f}\n\n"
        f"🤖 <b>Баланс бота:</b>\n"
        f"⭐ Звезды: {bot_stars}",
        parse_mode="HTML"
    )

# ==================== КОМАНДА /USERS ====================
@dp.message(Command("users"))
async def list_users(message: Message):
    """Список всех пользователей"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    users = await get_all_users()
    
    if not users:
        await message.answer("❌ Нет зарегистрированных пользователей.")
        return
    
    # Формируем список пользователей
    user_list = []
    for user in users[:20]:  # Показываем первых 20
        username = f"@{user.get('username')}" if user.get('username') else "нет"
        user_list.append(
            f"🆔 <code>{user['user_id']}</code> | {user['first_name']} | {username}\n"
            f"   ⭐ {user.get('balance_stars', 0)} | ₽ {user.get('balance_rub', 0):.2f}"
        )
    
    text = f"📊 <b>Список пользователей</b>\n\n"
    text += "\n".join(user_list)
    
    if len(users) > 20:
        text += f"\n\n... и еще {len(users) - 20} пользователей"
    
    await message.answer(text, parse_mode="HTML")

# ==================== КОМАНДА ДЛЯ ТЕСТА ПРОКСИ ====================
@dp.message(Command("test"))
async def test_command(message: Message):
    """Тестовая команда для проверки работы бота"""
    await message.answer("✅ Бот работает корректно!")