# handlers/user_handlers.py
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from datetime import datetime, timedelta
from calendar import monthrange
from database import get_available_slots, book_slot, cancel_booking, get_user_booking, get_dates_with_slots
from scheduler import add_reminder_task, remove_reminder_task
from config import ADMIN_ID, CHANNEL_ID, CHANNEL_LINK, SCHEDULE_CHANNEL_ID, CHECK_SUBSCRIPTION

router = Router()

class BookingState(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_name = State()
    waiting_for_phone = State()

async def create_calendar(year, month):
    keyboard = []
    keyboard.append([InlineKeyboardButton(text=f"📅 {year}-{month:02d}", callback_data="ignore")])
    keyboard.append([
        InlineKeyboardButton(text=day, callback_data="ignore")
        for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    ])

    first_day = datetime(year, month, 1).weekday()
    days_in_month = monthrange(year, month)[1]

    today = datetime.now().date()
    dates_with_slots = await get_dates_with_slots(year, month)

    week = []

    for _ in range(first_day):
        week.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    for day in range(1, days_in_month + 1):
        current_date_obj = datetime(year, month, day).date()
        current_date_str = f"{year}-{month:02d}-{day:02d}"

        if current_date_obj < today or current_date_str not in dates_with_slots:
            week.append(InlineKeyboardButton(text="—", callback_data="ignore"))
        else:
            week.append(
                InlineKeyboardButton(
                    text=str(day),
                    callback_data=f"date_{year}_{month}_{day}"
                )
            )

        if len(week) == 7:
            keyboard.append(week)
            week = []

    if week:
        while len(week) < 7:
            week.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
        keyboard.append(week)

    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1

    nav_row = [
        InlineKeyboardButton(text="⬅️", callback_data=f"month_{prev_year}_{prev_month}"),
        InlineKeyboardButton(text="Сегодня", callback_data="today"),
        InlineKeyboardButton(text="➡️", callback_data=f"month_{next_year}_{next_month}"),
    ]
    keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def get_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Записаться", callback_data="book")],
        [InlineKeyboardButton(text="📋 Моя запись", callback_data="my_booking")],
        [InlineKeyboardButton(text="💅 Прайсы", callback_data="prices")],
        [InlineKeyboardButton(text="🖼 Портфолио", callback_data="portfolio")]
    ])
    if user_id == ADMIN_ID:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin")])
    return keyboard

WELCOME_TEXT = (
    "<b>Добро пожаловать!</b>\n\n"
    "Рады вас видеть 💅 Выберите действие:"
)

@router.message(Command("start"))
async def start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user_id = message.from_user.id

    if CHECK_SUBSCRIPTION and not await check_subscription(bot, user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
        ])
        await message.answer("Для записи необходимо подписаться на канал.", reply_markup=keyboard)
        return

    await message.answer(WELCOME_TEXT, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")

async def show_main_menu(callback: CallbackQuery, bot: Bot):
    await callback.message.edit_text(
        WELCOME_TEXT,
        reply_markup=get_main_keyboard(callback.from_user.id),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    if await check_subscription(bot, user_id):
        await callback.message.edit_text("✅ Подписка подтверждена! Теперь вы можете записаться.")
        await show_main_menu(callback, bot)
    else:
        await callback.answer("Вы ещё не подписаны на канал.")

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, bot: Bot):
    await show_main_menu(callback, bot)

@router.callback_query(F.data == "book")
async def book(callback: CallbackQuery, state: FSMContext):
    now = datetime.now()
    await callback.message.edit_text(
        "📅 <b>Выберите дату:</b>",
        reply_markup=await create_calendar(now.year, now.month),
        parse_mode="HTML"
    )
    await state.set_state(BookingState.waiting_for_date)

@router.callback_query(F.data.startswith("month_"))
async def change_month(callback: CallbackQuery):
    _, year, month = callback.data.split("_")
    year, month = int(year), int(month)
    if month == 0:
        month = 12
        year -= 1
    elif month == 13:
        month = 1
        year += 1
    await callback.message.edit_reply_markup(reply_markup=await create_calendar(year, month))

@router.callback_query(F.data == "today")
async def today(callback: CallbackQuery):
    now = datetime.now()
    await callback.message.edit_reply_markup(reply_markup=await create_calendar(now.year, now.month))

@router.callback_query(F.data.startswith("date_"))
async def select_date(callback: CallbackQuery, state: FSMContext):
    _, year, month, day = callback.data.split("_")
    date = f"{year}-{int(month):02d}-{int(day):02d}"

    slots = await get_available_slots(date)
    if not slots:
        await callback.answer("На эту дату нет свободных слотов.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🕐 {time}", callback_data=f"time_{date}_{time}")] for time in slots
    ] + [[InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]])

    await callback.message.edit_text(
        f"🕐 <b>Свободное время на {date}:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.update_data(date=date)
    await state.set_state(BookingState.waiting_for_time)

@router.callback_query(F.data.startswith("time_"))
async def select_time(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    # Проверяем, есть ли уже активная запись
    existing_booking = await get_user_booking(user_id)
    if existing_booking:
        date, time, name, phone = existing_booking

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Моя запись", callback_data="my_booking")],
            [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
        ])

        await callback.message.edit_text(
            f"❌ <b>У вас уже есть активная запись.</b>\n\n"
            f"📅 Дата: <b>{date}</b>\n"
            f"🕐 Время: <b>{time}</b>\n"
            f"👤 Имя: <b>{name}</b>\n"
            f"📞 Телефон: <b>{phone}</b>\n\n"
            f"Чтобы записаться на другое время, сначала отмените текущую запись.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.clear()
        return

    _, date, time = callback.data.split("_", 2)
    await state.update_data(time=time)
    await callback.message.edit_text(
        "✏️ <b>Введите ваше имя:</b>",
        parse_mode="HTML"
    )
    await state.set_state(BookingState.waiting_for_name)

@router.message(BookingState.waiting_for_name)
async def enter_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Имя не может быть пустым. Введите имя:")
        return
    await state.update_data(name=name)
    await message.answer("📞 <b>Введите ваш номер телефона:</b>", parse_mode="HTML")
    await state.set_state(BookingState.waiting_for_phone)

@router.message(BookingState.waiting_for_phone)
async def enter_phone(message: Message, state: FSMContext, bot: Bot):
    phone = message.text.strip()
    if not phone:
        await message.answer("Телефон не может быть пустым. Введите ваш номер телефона:")
        return

    data = await state.get_data()
    date = data['date']
    time = data['time']
    name = data['name']
    user_id = message.from_user.id

    success, error = await book_slot(date, time, user_id, name, phone)
    if not success:
        await message.answer(f"❌ {error}")
        await state.clear()
        return

    try:
        await bot.send_message(
            ADMIN_ID,
            f"🔔 <b>Новая запись:</b>\n\n"
            f"📅 Дата: <b>{date}</b>\n"
            f"🕐 Время: <b>{time}</b>\n"
            f"👤 Имя: <b>{name}</b>\n"
            f"📞 Телефон: <b>{phone}</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка уведомления админа: {e}")

    try:
        await bot.send_message(
            SCHEDULE_CHANNEL_ID,
            f"📌 Запись на {date} {time}: {name} ({phone})"
        )
    except Exception as e:
        print(f"Ошибка отправки в канал: {e}")

    try:
        booking_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        await add_reminder_task(user_id, booking_dt)
    except Exception as e:
        print(f"Ошибка создания напоминания: {e}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
    ])
    await message.answer(
        f"✅ <b>Запись подтверждена!</b>\n\n"
        f"📅 Дата: <b>{date}</b>\n"
        f"🕐 Время: <b>{time}</b>\n\n"
        f"Ждём вас! 💅",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.clear()

# ── Моя запись ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_booking")
async def my_booking(callback: CallbackQuery):
    user_id = callback.from_user.id
    booking = await get_user_booking(user_id)
    if not booking:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Записаться", callback_data="book")],
            [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
        ])
        await callback.message.edit_text(
            "📋 <b>У вас нет активной записи.</b>\n\nХотите записаться?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    date, time, name, phone = booking
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel")],
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(
        f"📋 <b>Ваша запись:</b>\n\n"
        f"📅 Дата: <b>{date}</b>\n"
        f"🕐 Время: <b>{time}</b>\n"
        f"👤 Имя: <b>{name}</b>\n"
        f"📞 Телефон: <b>{phone}</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    booking = await get_user_booking(user_id)
    if not booking:
        await callback.answer("У вас нет активной записи.")
        return

    date, time, name, phone = booking
    success, _ = await cancel_booking(user_id)
    if success:
        await remove_reminder_task(user_id)

        try:
            await bot.send_message(
                ADMIN_ID,
                f"🚫 <b>Запись отменена клиентом:</b>\n\n"
                f"📅 Дата: <b>{date}</b>\n"
                f"🕐 Время: <b>{time}</b>\n"
                f"👤 Имя: <b>{name}</b>\n"
                f"📞 Телефон: <b>{phone}</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка уведомления админа: {e}")

        try:
            await bot.send_message(
                SCHEDULE_CHANNEL_ID,
                f"🚫 Отмена записи:\n"
                f"📅 Дата: {date}\n"
                f"🕐 Время: {time}\n"
                f"👤 Имя: {name}\n"
                f"📞 Телефон: {phone}"
            )
        except Exception as e:
            print(f"Ошибка отправки отмены в канал: {e}")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Записаться снова", callback_data="book")],
            [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
        ])

        await callback.message.edit_text(
            "✅ <b>Запись отменена.</b>\n\nБудем ждать вас в другой раз! 💅",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.answer("Ошибка при отмене записи.")

# ── Прайсы ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "prices")
async def prices(callback: CallbackQuery):
    text = (
        "💅 <b>Прайс-лист:</b>\n\n"
        "┌ Френч — <b>1 000 ₽</b>\n"
        "└ Квадрат — <b>500 ₽</b>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

# ── Портфолио ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "portfolio")
async def portfolio(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Смотреть портфолио", url="https://ru.pinterest.com/crystalwithluv/_created/")],
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(
        "🖼 <b>Портфолио</b>\n\nПосмотрите наши работы и убедитесь в качестве! ✨",
        reply_markup=keyboard,
        parse_mode="HTML"
    )