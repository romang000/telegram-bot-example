# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # загружает .env файл
# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Отсутствует токен бота. Убедитесь, что переменная BOT_TOKEN установлена в .env файле.")

# ID администратора
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ID канала для проверки подписки
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Ссылка на канал
CHANNEL_LINK = os.getenv("CHANNEL_LINK")

# ID канала для расписания
SCHEDULE_CHANNEL_ID = os.getenv("SCHEDULE_CHANNEL_ID")

# Включить проверку подписки
CHECK_SUBSCRIPTION = os.getenv("CHECK_SUBSCRIPTION", "False").lower() == "true"