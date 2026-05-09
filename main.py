import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Отримуємо змінні з оточення (Railway)
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Привіт! Бот працює. Твій ID: {message.from_user.id}")
    # Перевірка на адміна
    if str(message.from_user.id) == ADMIN_ID:
        await message.answer("Ви авторизовані як адмін 🛠")

async def main():
    print("Бот запущений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
