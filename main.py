import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from motor.motor_asyncio import AsyncIOMotorClient

# Налаштування
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
ADMIN_ID = os.getenv("ADMIN_ID")
SUPPORT_LINK = "@your_manager_username" # Сюди впиши юзернейм підтримки

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Підключення до БД
cluster = AsyncIOMotorClient(MONGO_URL)
db = cluster["standoff_bot"]
users_col = db["users"]

# --- ТЕКСТИ ---
MESSAGES = {
    'ua': {
        'welcome': 'Оберіть мову:',
        'main_menu': '🏠 Головне меню',
        'profile': '👤 Профіль',
        'buy_gold': '💰 Купити Голду',
        'withdraw_gold': '📤 Вивести Голду',
        'sell_gold': '📥 Продати Голду',
        'support': '🆘 Підтримка',
        'support_text': f"За всіма питаннями пишіть сюди: {SUPPORT_LINK}",
        'profile_text': (
            "ℹ️ **Інформація про вас:**\n\n"
            "🆔 `{id}`\n"
            "✨ **Баланс:** {balance} грн ≈ {gold} G\n\n"
            "**Куплено всього:** {bought} грн\n"
            "**Виведено всього:** {withdrawn} G\n"
            "**Виводів:** {w_count}\n\n"
            "**Запрошено друзів:** {friends}\n\n"
            "🗓️ **Реєстрація:** {reg_date}"
        )
    },
    'ru': {
        'welcome': 'Выберите язык:',
        'main_menu': '🏠 Главное меню',
        'profile': '👤 Профиль',
        'buy_gold': '💰 Купить Голду',
        'withdraw_gold': '📤 Вывести Голду',
        'sell_gold': '📥 Продать Голду',
        'support': '🆘 Поддержка',
        'support_text': f"По всем вопросам пишите сюда: {SUPPORT_LINK}",
        'profile_text': "ℹ️ **Информация о вас:**\n\n🆔 `{id}`\n✨ **Баланс:** {balance} грн ≈ {gold} G\n\n**Куплено всего:** {bought} грн\n**Выведено всего:** {withdrawn} G\n**Выводов:** {w_count}\n\n**Приглашено друзей:** {friends}\n\n🗓️ **Регистрация:** {reg_date}"
    },
    'en': {
        'welcome': 'Choose language:',
        'main_menu': '🏠 Main menu',
        'profile': '👤 Profile',
        'buy_gold': '💰 Buy Gold',
        'withdraw_gold': '📤 Withdraw Gold',
        'sell_gold': '📥 Sell Gold',
        'support': '🆘 Support',
        'support_text': f"For all questions write here: {SUPPORT_LINK}",
        'profile_text': "ℹ️ **Information about you:**\n\n🆔 `{id}`\n✨ **Balance:** {balance} UAH ≈ {gold} G\n\n**Total bought:** {bought} UAH\n**Total withdrawn:** {withdrawn} G\n**Withdrawals:** {w_count}\n\n**Friends invited:** {friends}\n\n🗓️ **Registration:** {reg_date}"
    }
}

# --- КЛАВІАТУРИ ---

def get_main_keyboard(lang):
    builder = ReplyKeyboardBuilder()
    # Перший ряд: Купити та Продати
    builder.row(
        types.KeyboardButton(text=MESSAGES[lang]['buy_gold']),
        types.KeyboardButton(text=MESSAGES[lang]['sell_gold'])
    )
    # Другий ряд: Вивести
    builder.row(types.KeyboardButton(text=MESSAGES[lang]['withdraw_gold']))
    # Третій ряд: Профіль та Підтримка
    builder.row(
        types.KeyboardButton(text=MESSAGES[lang]['profile']),
        types.KeyboardButton(text=MESSAGES[lang]['support'])
    )
    return builder.as_markup(resize_keyboard=True)

def get_lang_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Українська 🇺🇦", callback_data="setlang_ua")
    builder.button(text="Русский 🇷🇺", callback_data="setlang_ru")
    builder.button(text="English 🇬🇧", callback_data="setlang_en")
    builder.adjust(1)
    return builder.as_markup()

# --- ХЕНДЛЕРИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user = await users_col.find_one({"user_id": user_id})
    if not user:
        await users_col.insert_one({
            "user_id": user_id,
            "lang": "ua",
            "balance_uah": 0.0,
            "total_bought": 0.0,
            "total_withdrawn": 0.0,
            "withdrawals_count": 0,
            "friends_count": 0,
            "reg_date": datetime.now().strftime("%d.%m.%Y")
        })
    await message.answer("🇺🇦 Оберіть мову / 🇬🇧 Choose language:", reply_markup=get_lang_keyboard())

@dp.callback_query(F.data.startswith("setlang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    await users_col.update_one({"user_id": callback.from_user.id}, {"$set": {"lang": lang}})
    await callback.message.delete()
    await callback.message.answer(MESSAGES[lang]['main_menu'], reply_markup=get_main_keyboard(lang))
    await callback.answer()

@dp.message(lambda m: any(m.text == MESSAGES[l]['profile'] for l in MESSAGES))
async def show_profile(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if not user: return
    lang = user.get('lang', 'ua')
    gold_rate = 2 
    text = MESSAGES[lang]['profile_text'].format(
        id=user['user_id'], balance=user['balance_uah'], gold=user['balance_uah'] * gold_rate,
        bought=user['total_bought'], withdrawn=user['total_withdrawn'],
        w_count=user['withdrawals_count'], friends=user['friends_count'], reg_date=user['reg_date']
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(lambda m: any(m.text == MESSAGES[l]['support'] for l in MESSAGES))
async def show_support(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user.get('lang', 'ua') if user else 'ua'
    await message.answer(MESSAGES[lang]['support_text'])

# Тимчасові відповіді для інших кнопок
@dp.message(F.text.in_([MESSAGES['ua']['buy_gold'], MESSAGES['ru']['buy_gold'], MESSAGES['en']['buy_gold']]))
async def buy_gold_temp(message: types.Message):
    await message.answer("🚧 Цей розділ знаходиться в розробці...")

async def main():
    print("Бот Standoff 2 запущений з повним меню...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
