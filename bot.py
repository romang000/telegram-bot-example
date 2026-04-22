# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.user_handlers import router as user_router
from handlers.admin_handlers import router as admin_router
from scheduler import start_scheduler, stop_scheduler, restore_reminders

# Настройка логирования
logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрация роутеров
    dp.include_router(user_router)
    dp.include_router(admin_router)
    
    # Восстановление напоминаний
    await restore_reminders()
    
    # Запуск планировщика
    start_scheduler()
    
    try:
        await dp.start_polling(bot)
    finally:
        stop_scheduler()

if __name__ == "__main__":
    asyncio.run(main())