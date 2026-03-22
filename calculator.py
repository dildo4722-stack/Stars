from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import dp, bot
from keyboards import get_back_to_menu_button
from utils import calculate_prices

class CalculatorStates(StatesGroup):
    waiting_for_stars = State()

@dp.callback_query(F.data == "menu:calculator")
async def calculator_start(callback: CallbackQuery, state: FSMContext):
    """Запуск калькулятора звезд"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    
    await callback.message.edit_text(
        "🧮 <b>Калькулятор звезд</b>\n\n"
        "Введите количество звезд для конвертации:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(CalculatorStates.waiting_for_stars)
    await callback.answer()

@dp.message(CalculatorStates.waiting_for_stars)
async def process_calculator(message: Message, state: FSMContext):
    """Обработка введенного количества звезд"""
    try:
        stars = int(message.text.strip())
        
        if stars <= 0:
            await message.answer(
                "❌ Введите положительное число",
                reply_markup=get_back_to_menu_button()
            )
            return
        
        prices = calculate_prices(stars)
        
        # Создаем клавиатуру с кнопкой "Рассчитать еще"
        builder = InlineKeyboardBuilder()
        builder.button(text="🧮 Рассчитать еще", callback_data="menu:calculator")
        builder.button(text="◀️ В меню", callback_data="back_to_menu")
        builder.adjust(1)
        
        await message.answer(
            f"🧮 <b>Результат конвертации</b>\n\n"
            f"⭐ <b>{stars} звезд</b> это:\n\n"
            f"₽ Рубли: {prices['rub']:.2f}\n"
            f"💵 Доллары: {prices['usd']:.2f}\n"
            f"💎 TON: {prices['ton']:.2f}",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите целое число (количество звезд)",
            reply_markup=get_back_to_menu_button()
        )
    
    await state.clear()