# handlers/admin_handlers.py
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from datetime import datetime
from database import add_slot, remove_slot, close_day, get_schedule, cancel_client_booking
from config import ADMIN_ID

router = Router()

class AdminState(StatesGroup):
    waiting_for_date = State()
    waiting_for_time_add = State()
    waiting_for_time_remove = State()
    waiting_for_date_close = State()
    waiting_for_date_view = State()
    waiting_for_date_cancel = State()
    waiting_for_time_cancel = State()

@router.callback_query(F.data == "admin")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещен.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📆 Добавить рабочий день", callback_data="add_day")],
        [InlineKeyboardButton(text="➕ Добавить слот", callback_data="add_slot")],
        [InlineKeyboardButton(text="➖ Удалить слот", callback_data="remove_slot")],
        [InlineKeyboardButton(text="🔒 Закрыть день", callback_data="close_day")],
        [InlineKeyboardButton(text="📋 Просмотреть расписание", callback_data="view_schedule")],
        [InlineKeyboardButton(text="🚫 Отменить запись клиента", callback_data="cancel_booking")],
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(
        "⚙️ <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "add_day")
async def add_day(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(
        "📆 <b>Добавить рабочий день</b>\n\nВведите дату в формате <code>YYYY-MM-DD</code>:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_for_date)

@router.message(AdminState.waiting_for_date)
async def enter_date(message: Message, state: FSMContext):
    date = message.text.strip()
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        await message.answer("❌ Неверный формат даты. Введите <code>YYYY-MM-DD</code>:", parse_mode="HTML")
        return

    for hour in range(9, 18):
        time = f"{hour:02d}:00"
        await add_slot(date, time)

    await message.answer(
        f"✅ День <b>{date}</b> добавлен со слотами с 9:00 до 18:00.",
        parse_mode="HTML"
    )
    await state.clear()

@router.callback_query(F.data == "add_slot")
async def add_slot_start(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(
        "➕ <b>Добавить слот</b>\n\nВведите дату и время в формате <code>YYYY-MM-DD HH:MM</code>:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_for_time_add)

@router.message(AdminState.waiting_for_time_add)
async def add_slot_time(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        date, time = text.split()
        datetime.strptime(date, "%Y-%m-%d")
        datetime.strptime(time, "%H:%M")
    except:
        await message.answer("❌ Неверный формат. Введите <code>YYYY-MM-DD HH:MM</code>:", parse_mode="HTML")
        return

    success = await add_slot(date, time)
    if success:
        await message.answer(f"✅ Слот <b>{date} {time}</b> добавлен.", parse_mode="HTML")
    else:
        await message.answer("⚠️ Такой слот уже существует.")
    await state.clear()

@router.callback_query(F.data == "remove_slot")
async def remove_slot_start(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(
        "➖ <b>Удалить слот</b>\n\nВведите дату и время в формате <code>YYYY-MM-DD HH:MM</code>:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_for_time_remove)

@router.message(AdminState.waiting_for_time_remove)
async def remove_slot_time(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        date, time = text.split()
    except:
        await message.answer("❌ Неверный формат. Введите <code>YYYY-MM-DD HH:MM</code>:", parse_mode="HTML")
        return

    await remove_slot(date, time)
    await message.answer(f"✅ Слот <b>{date} {time}</b> удалён.", parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data == "close_day")
async def close_day_start(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(
        "🔒 <b>Закрыть день</b>\n\nВведите дату в формате <code>YYYY-MM-DD</code>:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_for_date_close)

@router.message(AdminState.waiting_for_date_close)
async def close_day_date(message: Message, state: FSMContext):
    date = message.text.strip()
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except:
        await message.answer("❌ Неверный формат даты.", parse_mode="HTML")
        return

    await close_day(date)
    await message.answer(f"🔒 День <b>{date}</b> закрыт.", parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data == "view_schedule")
async def view_schedule_start(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(
        "📋 <b>Просмотр расписания</b>\n\nВведите дату в формате <code>YYYY-MM-DD</code>:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_for_date_view)

@router.message(AdminState.waiting_for_date_view)
async def view_schedule_date(message: Message, state: FSMContext):
    date = message.text.strip()
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except:
        await message.answer("❌ Неверный формат даты.")
        return

    schedule = await get_schedule(date)
    if not schedule:
        await message.answer(f"📋 На <b>{date}</b> нет слотов.", parse_mode="HTML")
        await state.clear()
        return

    text = f"📋 <b>Расписание на {date}:</b>\n\n"
    for time, available, name, phone in schedule:
        if available:
            text += f"🕐 {time} — ✅ Свободен\n"
        else:
            text += f"🕐 {time} — 👤 {name} ({phone})\n"

    await message.answer(text, parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data == "cancel_booking")
async def cancel_booking_start(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(
        "🚫 <b>Отменить запись клиента</b>\n\nВведите дату и время в формате <code>YYYY-MM-DD HH:MM</code>:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_for_date_cancel)

@router.message(AdminState.waiting_for_date_cancel)
async def cancel_booking_time(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    try:
        date, time = text.split()
    except:
        await message.answer("❌ Неверный формат. Введите <code>YYYY-MM-DD HH:MM</code>:", parse_mode="HTML")
        return

    # cancel_client_booking теперь возвращает (user_id, name, phone) или None
    result = await cancel_client_booking(date, time)
    if result:
        user_id, name, phone = result
        try:
            await bot.send_message(
                user_id,
                f"⚠️ <b>Ваша запись была отменена администратором.</b>\n\n"
                f"📅 Дата: <b>{date}</b>\n"
                f"🕐 Время: <b>{time}</b>\n"
                f"👤 Имя: <b>{name}</b>\n"
                f"📞 Телефон: <b>{phone}</b>\n\n"
                f"Приносим извинения за неудобства. Вы можете записаться на другое время.",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка уведомления пользователя: {e}")
        await message.answer(
            f"✅ Запись <b>{name}</b> на {date} {time} отменена. Клиент уведомлён.",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Запись не найдена.")
    await state.clear()