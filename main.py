import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Тимчасові сховища (у реальному проєкті тут буде БД)
user_languages = {}
user_reg_date = {}

MESSAGES = {
    'ua': {
        'welcome': 'Оберіть мову:',
        'main_menu': 'Головне меню 🏠',
        'profile': '👤 Профіль',
        'profile_text': (
            "ℹ️ **Інформація про вас:**\n\n"
            "🆔 `{id}`\n"
            "✨ **Баланс:** 0 грн ≈ 0 G\n\n"
            "**Куплено всього:** 0 грн ~ 0 G\n"
            "**Виведено всього:** 0 G\n"
            "**Виводів:** 0\n\n"
            "**Запрошено друзів:** 0\n\n"
            "🗓️ **Реєстрація:** {reg_date}"
        )
    },
    'ru': {
        'welcome': 'Выберите язык:',
        'main_menu': 'Главное меню 🏠',
        'profile': '👤 Профиль',
        'profile_text': (
            "ℹ️ **Информация о вас:**\n\n"
            "🆔 `{id}`\n"
            "✨ **Баланс:** 0 грн ≈ 0 G\n\n"
            "**Куплено всего:** 0 грн ~ 0 G\n"
            "**Выведено всего:** 0 G\n"
            "**Выводов:** 0\n\n"
            "**Приглашено друзей:** 0\n\n"
            "🗓️ **Регистрация:** {reg_date}"
        )
    },
    'en': {
        'welcome': 'Choose your language:',
        'main_menu': 'Main menu 🏠',
        'profile': '👤 Profile',
        'profile_text': (
            "ℹ️ **Information about you:**\n\n"
            "🆔 `{id}`\n"
            "✨ **Balance:** 0 UAH ≈ 0 G\n\n"
            "**Total bought:** 0 UAH ~ 0 G\n"
            "**Total withdrawn:** 0 G\n"
            "**Withdrawals:** 0\n\n"
            "**Friends invited:** 0\n\n"
            "🗓️ **Registration:** {reg_date}"
        )
    }
}

# --- КЛАВІАТУРИ ---

def get_lang_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Українська 🇺🇦", callback_data="setlang_ua")
    builder.button(text="Русский 🇷🇺", callback_data="setlang_ru")
    builder.button(text="English 🇬🇧", callback_data="setlang_en")
    builder.adjust(1)
    return builder.as_markup()

def get_main_keyboard(lang):
    builder = ReplyKeyboardBuilder()
    builder.button(text=MESSAGES[lang]['profile'])
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# --- ХЕНДЛЕРИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Фіксуємо дату реєстрації, якщо юзера ще немає в пам'яті
    if message.from_user.id not in user_reg_date:
        user_reg_date[message.from_user.id] = datetime.now().strftime("%d.%m.%Y")
    
    await message.answer("Hello! / Привіт! / Привет!", reply_markup=get_lang_keyboard())

@dp.callback_query(F.data.startswith("setlang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    user_languages[callback.from_user.id] = lang
    
    await callback.message.delete()
    await callback.message.answer(
        MESSAGES[lang]['main_menu'], 
        reply_markup=get_main_keyboard(lang)
    )
    await callback.answer()

@dp.message(F.text.in_([MESSAGES['ua']['profile'], MESSAGES['ru']['profile'], MESSAGES['en']['profile']]))
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    lang = user_languages.get(user_id, 'ua')
    reg_date = user_reg_date.get(user_id, "Невідомо")
    
    # Форматуємо текст профілю
    text = MESSAGES[lang]['profile_text'].format(
        id=user_id,
        reg_date=reg_date
    )
    
    await message.answer(text, parse_mode="Markdown")

async def main():
    print("Бот Standoff 2 запущений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
