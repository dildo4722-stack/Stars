from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import dp, bot
from database import register_user, get_user
from keyboards import get_main_menu, get_back_to_menu_button
from utils import check_subscription, format_profile
from config import REQUIRED_CHANNEL_ID
import logging

class MainStates(StatesGroup):
    waiting_for_subscription = State()

def get_channel_invite_link():
    """Получение ссылки на канал"""
    channel_id = REQUIRED_CHANNEL_ID
    
    if str(channel_id).startswith('@'):
        return f"https://t.me/{channel_id[1:]}"
    
    channel_id_str = str(channel_id)
    if channel_id_str.startswith('-100'):
        channel_id_str = channel_id_str[4:]
    
    return f"https://t.me/c/{channel_id_str}"

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    await register_user(user_id, username, first_name, last_name)
    
    if not await check_subscription(bot, user_id):
        channel_link = get_channel_invite_link()
        
        builder = InlineKeyboardBuilder()
        builder.button(text="📢 Подписаться на канал", url=channel_link)
        builder.button(text="✅ Я подписался", callback_data="check_subscription")
        builder.adjust(1)
        
        await message.answer(
            "📢 <b>Для использования бота необходимо подписаться на наш канал!</b>\n\n"
            "👇 Нажмите кнопку ниже, чтобы подписаться, а затем нажмите «Я подписался»",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        await state.set_state(MainStates.waiting_for_subscription)
    else:
        await show_main_menu(message)

@dp.callback_query(F.data == "check_subscription", MainStates.waiting_for_subscription)
async def check_subscription_callback(callback: CallbackQuery, state: FSMContext):
    """Проверка подписки после нажатия кнопки"""
    if await check_subscription(bot, callback.from_user.id):
        await callback.message.delete()
        await callback.message.answer(
            "✅ <b>Спасибо за подписку!</b>\n\n"
            "Добро пожаловать в бот!",
            parse_mode="HTML"
        )
        await show_main_menu(callback.message)
        await state.clear()
    else:
        channel_link = get_channel_invite_link()
        builder = InlineKeyboardBuilder()
        builder.button(text="📢 Подписаться на канал", url=channel_link)
        builder.button(text="✅ Я подписался", callback_data="check_subscription")
        builder.adjust(1)
        
        try:
            await callback.message.edit_text(
                "❌ <b>Вы еще не подписались на канал!</b>\n\n"
                "Пожалуйста, подпишитесь и нажмите «Я подписался»",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.delete()
            await callback.message.answer(
                "❌ <b>Вы еще не подписались на канал!</b>\n\n"
                "Пожалуйста, подпишитесь и нажмите «Я подписался»",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    try:
        await callback.message.edit_text(
            "🏠 <b>Главное меню</b>\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
    except Exception:
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(
            "🏠 <b>Главное меню</b>\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
    await callback.answer()

@dp.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия - удаляем сообщение и показываем меню"""
    await state.clear()
    
    # Пробуем удалить сообщение (если не удастся - игнорируем)
    try:
        await callback.message.delete()
    except:
        pass
    
    # Отправляем новое сообщение с меню
    await callback.message.answer(
        "❌ Действие отменено.\n\n"
        "🏠 <b>Главное меню</b>",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    
    try:
        await callback.answer()
    except:
        pass

@dp.callback_query(F.data == "menu:profile")
async def show_profile(callback: CallbackQuery):
    """Показ профиля пользователя"""
    user_data = await get_user(callback.from_user.id)
    if user_data:
        text = format_profile(user_data)
        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_back_to_menu_button(),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.delete()
            await callback.message.answer(
                text,
                reply_markup=get_back_to_menu_button(),
                parse_mode="HTML"
            )
    else:
        try:
            await callback.message.edit_text(
                "❌ Ошибка загрузки профиля",
                reply_markup=get_back_to_menu_button()
            )
        except Exception:
            await callback.message.delete()
            await callback.message.answer(
                "❌ Ошибка загрузки профиля",
                reply_markup=get_back_to_menu_button()
            )
    
    try:
        await callback.answer()
    except:
        pass

async def show_main_menu(message: Message):
    """Показать главное меню"""
    await message.answer(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )