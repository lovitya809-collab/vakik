import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# Налаштування
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Тимчасове сховище мови (User ID -> 'ua', 'ru', 'en')
user_languages = {}

# Тексти для перекладу
MESSAGES = {
    'ua': {
        'welcome': 'Оберіть мову:',
        'main_menu': 'Ви обрали українську мову 🇺🇦',
        'profile': '👤 Профіль',
        'profile_text': 'Твій профіль у Standoff 2 Market:\nID: {id}\nСтатус: Клієнт'
    },
    'ru': {
        'welcome': 'Выберите язык:',
        'main_menu': 'Вы выбрали русский язык 🇷🇺',
        'profile': '👤 Профиль',
        'profile_text': 'Твой профиль в Standoff 2 Market:\nID: {id}\nСтатус: Клиент'
    },
    'en': {
        'welcome': 'Choose your language:',
        'main_menu': 'You selected English 🇬🇧',
        'profile': '👤 Profile',
        'profile_text': 'Your profile in Standoff 2 Market:\nID: {id}\nStatus: Client'
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
    await message.answer("Hello! / Привіт! / Привет!", reply_markup=get_lang_keyboard())

@dp.callback_query(F.data.startswith("setlang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    user_languages[callback.from_user.id] = lang
    
    await callback.message.delete() # Видаляємо повідомлення з вибором мови
    await callback.message.answer(
        MESSAGES[lang]['main_menu'], 
        reply_markup=get_main_keyboard(lang)
    )
    await callback.answer()

@dp.message(F.text.in_([MESSAGES['ua']['profile'], MESSAGES['ru']['profile'], MESSAGES['en']['profile']]))
async def show_profile(message: types.Message):
    lang = user_languages.get(message.from_user.id, 'ua') # за замовчуванням ua
    text = MESSAGES[lang]['profile_text'].format(id=message.from_user.id)
    await message.answer(text)

async def main():
    print("Бот Standoff 2 запущений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
