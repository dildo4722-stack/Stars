from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню с 6 кнопками"""
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Профиль", callback_data="menu:profile")
    builder.button(text="⭐ Купить звезды", callback_data="menu:buy_stars")
    builder.button(text="💰 Пополнить баланс", callback_data="menu:top_up")
    builder.button(text="🧮 Калькулятор звезд", callback_data="menu:calculator")
    builder.button(text="🎁 Купить подарок", callback_data="menu:buy_gift")
    builder.button(text="🆘 Техподдержка", callback_data="menu:support")
    builder.adjust(2)
    return builder.as_markup()

def get_back_to_menu_button() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ В главное меню", callback_data="back_to_menu")
    return builder.as_markup()

def get_cancel_button() -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    return builder.as_markup()

def get_currency_selection_kb(stars_amount: int) -> InlineKeyboardMarkup:
    """Кнопки выбора валюты для оплаты звезд"""
    builder = InlineKeyboardBuilder()
    builder.button(text="₽ Рубли", callback_data=f"pay_with_rub:{stars_amount}")
    builder.button(text="💵 Доллары", callback_data=f"pay_with_usd:{stars_amount}")
    builder.button(text="💎 TON", callback_data=f"pay_with_ton:{stars_amount}")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(2)
    return builder.as_markup()

def get_gift_currency_selection_kb(gift_key: str) -> InlineKeyboardMarkup:
    """Кнопки выбора валюты для покупки подарка"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Звезды", callback_data=f"gift_pay_stars:{gift_key}")
    builder.button(text="₽ Рубли", callback_data=f"gift_pay_rub:{gift_key}")
    builder.button(text="💵 Доллары", callback_data=f"gift_pay_usd:{gift_key}")
    builder.button(text="💎 TON", callback_data=f"gift_pay_ton:{gift_key}")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(2)
    return builder.as_markup()

def get_gift_selection_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора подарков (6 кнопок 1-6)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="1️⃣", callback_data="gift:gift_1")
    builder.button(text="2️⃣", callback_data="gift:gift_2")
    builder.button(text="3️⃣", callback_data="gift:gift_3")
    builder.button(text="4️⃣", callback_data="gift:gift_4")
    builder.button(text="5️⃣", callback_data="gift:gift_5")
    builder.button(text="6️⃣", callback_data="gift:gift_6")
    builder.adjust(3)  # 3 кнопки в ряд
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    return builder.as_markup()

def get_admin_request_kb(request_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для админа при рассмотрении заявки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить", callback_data=f"admin_approve:{request_id}")
    builder.button(text="❌ Отклонить", callback_data=f"admin_reject:{request_id}")
    builder.adjust(2)
    return builder.as_markup()