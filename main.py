import asyncio
import logging

from bot_instance import dp, bot
from database import init_db
import user_handlers
import admin_handlers
import admin_commands
import buy_stars
import buy_gift
import calculator
import support
import top_up

logging.basicConfig(level=logging.INFO)

async def main():
    """Запуск бота"""
    # Удаляем вебхук, если он был установлен
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Вебхук удален")
    
    # Инициализируем базу данных
    init_db()
    logging.info("База данных инициализирована")
    
    # Запускаем бота
    logging.info("Бот запущен в режиме long polling")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())