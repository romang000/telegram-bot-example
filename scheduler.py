# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from aiogram import Bot
from database import get_all_reminders, add_reminder, remove_reminder
from config import BOT_TOKEN

scheduler = AsyncIOScheduler()
bot = Bot(token=BOT_TOKEN)

async def send_reminder(user_id, time_str):
    text = f"Напоминаем, что вы записаны на маникюр завтра в {time_str}.\nЖдём вас ❤️"
    await bot.send_message(chat_id=user_id, text=text)

def schedule_reminder(user_id, booking_datetime):
    reminder_time = booking_datetime - timedelta(hours=24)
    if reminder_time > datetime.now():
        job = scheduler.add_job(send_reminder, trigger=DateTrigger(run_date=reminder_time), args=[user_id, booking_datetime.strftime('%H:%M')])
        return job.id
    return None

async def add_reminder_task(user_id, booking_datetime):
    job_id = schedule_reminder(user_id, booking_datetime)
    if job_id:
        await add_reminder(user_id, booking_datetime, job_id)

async def remove_reminder_task(user_id):
    job_id = await remove_reminder(user_id)
    if job_id and scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

async def restore_reminders():
    reminders = await get_all_reminders()
    for user_id, dt_str, job_id in reminders:
        dt = datetime.fromisoformat(dt_str)
        if dt > datetime.now() + timedelta(hours=24):
            schedule_reminder(user_id, dt)
        else:
            # Если время прошло, удалить
            await remove_reminder(user_id)

def start_scheduler():
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()