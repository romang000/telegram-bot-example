# database.py
import sqlite3
from datetime import datetime, timedelta
import aiosqlite
import asyncio
import os
from config import ADMIN_ID

DB_PATH = '/data/bot.db'

def ensure_data_dir():
    if not os.path.exists('data'):
        os.makedirs('data')

# Синхронные функции для инициализации
def init_db():
    ensure_data_dir()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица слотов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            available BOOLEAN DEFAULT 1,
            user_id INTEGER,
            name TEXT,
            phone TEXT,
            UNIQUE(date, time)
        )
    ''')
    
    # Таблица напоминаний
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            datetime TEXT NOT NULL,
            job_id TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

# Асинхронные функции для работы с БД
async def get_available_slots(date):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT time FROM slots WHERE date = ? AND available = 1 ORDER BY time', (date,))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def book_slot(date, time, user_id, name, phone):
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверить, нет ли уже записи у пользователя
        cursor = await db.execute('SELECT id FROM slots WHERE user_id = ? AND available = 0', (user_id,))
        if await cursor.fetchone():
            return False, "У вас уже есть активная запись."
        
        # Забронировать слот
        await db.execute('UPDATE slots SET available = 0, user_id = ?, name = ?, phone = ? WHERE date = ? AND time = ? AND available = 1',
                        (user_id, name, phone, date, time))
        await db.commit()
        
        # Проверить, забронировался ли слот
        cursor = await db.execute('SELECT id FROM slots WHERE date = ? AND time = ? AND user_id = ?', (date, time, user_id))
        if await cursor.fetchone():
            return True, None
        else:
            return False, "Слот уже занят."

async def cancel_booking(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT date, time FROM slots WHERE user_id = ? AND available = 0', (user_id,))
        booking = await cursor.fetchone()
        if not booking:
            return False, "У вас нет активной записи."
        
        await db.execute('UPDATE slots SET available = 1, user_id = NULL, name = NULL, phone = NULL WHERE user_id = ?', (user_id,))
        await db.commit()
        return True, booking

async def get_user_booking(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT date, time, name, phone FROM slots WHERE user_id = ? AND available = 0', (user_id,))
        return await cursor.fetchone()

async def add_slot(date, time):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute('INSERT INTO slots (date, time, available) VALUES (?, ?, 1)', (date, time))
            await db.commit()
            return True
        except sqlite3.IntegrityError:
            return False

async def remove_slot(date, time):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM slots WHERE date = ? AND time = ? AND available = 1', (date, time))
        await db.commit()

async def close_day(date):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE slots SET available = 0 WHERE date = ? AND available = 1', (date,))
        await db.commit()

async def get_schedule(date):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT time, available, name, phone FROM slots WHERE date = ? ORDER BY time', (date,))
        return await cursor.fetchall()

async def cancel_client_booking(date, time):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT user_id FROM slots WHERE date = ? AND time = ? AND available = 0', (date, time))
        user = await cursor.fetchone()
        if user:
            await db.execute('UPDATE slots SET available = 1, user_id = NULL, name = NULL, phone = NULL WHERE date = ? AND time = ?', (date, time))
            await db.commit()
            return user[0]
        return None

async def add_reminder(user_id, dt, job_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT INTO reminders (user_id, datetime, job_id) VALUES (?, ?, ?)', (user_id, dt.isoformat(), job_id))
        await db.commit()

async def remove_reminder(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT job_id FROM reminders WHERE user_id = ?', (user_id,))
        job = await cursor.fetchone()
        if job:
            await db.execute('DELETE FROM reminders WHERE user_id = ?', (user_id,))
            await db.commit()
            return job[0]
        return None

async def get_all_reminders():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT user_id, datetime, job_id FROM reminders')
        return await cursor.fetchall()
    
async def get_dates_with_slots(year: int, month: int):
    start_date = f"{year}-{month:02d}-01"
    
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            SELECT DISTINCT date
            FROM slots
            WHERE date >= ? AND date < ?
            ORDER BY date
        ''', (start_date, end_date))
        rows = await cursor.fetchall()
        return {row[0] for row in rows}

# Инициализация БД при импорте
init_db()