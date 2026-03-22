from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from config import REQUIRED_CHANNEL_ID, STAR_PRICE_RUB, STAR_PRICE_USD, STAR_PRICE_TON
import logging

async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Проверка подписки пользователя на канал"""
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL_ID, user_id=user_id)
        return member.status in [
            ChatMemberStatus.CREATOR, 
            ChatMemberStatus.ADMINISTRATOR, 
            ChatMemberStatus.MEMBER, 
            ChatMemberStatus.RESTRICTED
        ]
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        return False

def format_profile(user_data: dict) -> str:
    """Форматирование профиля пользователя"""
    name = user_data.get('first_name', 'Не указано')
    if user_data.get('last_name'):
        name += f" {user_data['last_name']}"
    
    username = f"@{user_data.get('username')}" if user_data.get('username') else "Не указан"
    
    # Форматируем дату регистрации
    reg_date = user_data.get('registration_date', '')
    if reg_date and 'T' in reg_date:
        reg_date = reg_date.split('T')[0]
    
    return (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"👋 <b>Имя:</b> {name}\n"
        f"🆔 <b>ID:</b> <code>{user_data['user_id']}</code>\n"
        f"📝 <b>Юзернейм:</b> {username}\n"
        f"📅 <b>Дата регистрации:</b> {reg_date}\n\n"
        f"💰 <b>Балансы:</b>\n"
        f"⭐ <b>Звезды:</b> {user_data.get('balance_stars', 0)}\n"
        f"₽ <b>Рубли:</b> {user_data.get('balance_rub', 0):.2f}\n"
        f"💎 <b>TON:</b> {user_data.get('balance_ton', 0):.2f}\n"
        f"💵 <b>Доллары:</b> {user_data.get('balance_usd', 0):.2f}"
    )

def calculate_prices(stars: int) -> dict:
    """Рассчет стоимости звезд в разных валютах (только для покупки звезд)"""
    return {
        'rub': stars * STAR_PRICE_RUB,
        'usd': stars * STAR_PRICE_USD,
        'ton': stars * STAR_PRICE_TON
    }