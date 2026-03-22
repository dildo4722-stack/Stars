from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import dp
import urllib.parse

SUPPORT_USERNAME = "whoppaton"

@dp.callback_query(F.data == "menu:support")
async def support_start(callback: CallbackQuery):
    text = "Привет, пишу по поводу бота. У меня появилась проблема, опишу ниже: "
    
    # правильная URL-кодировка
    encoded_text = urllib.parse.quote_plus(text)

    # правильная ссылка
    support_url = f"https://t.me/{SUPPORT_USERNAME}?text={encoded_text}"

    builder = InlineKeyboardBuilder()
    builder.button(text="📨 Написать в поддержку", url=support_url)
    builder.button(text="◀️ Назад", callback_data="back_to_menu")
    builder.adjust(1)

    await callback.message.edit_text(
        "🆘 <b>Техническая поддержка</b>\n\n"
        "Если у вас возникли вопросы или проблемы с ботом, "
        "вы можете обратиться в нашу службу поддержки.\n\n"
        "Нажмите на кнопку ниже, чтобы написать сообщение.\n"
        "Пожалуйста, опишите вашу проблему подробно.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()