import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from motor.motor_asyncio import AsyncIOMotorClient

# --- НАЛАШТУВАННЯ ---
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
ADMIN_ID = os.getenv("ADMIN_ID")
SUPPORT_LINK = "@manager_standoff" # Твій юзернейм

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Підключення до БД
cluster = AsyncIOMotorClient(MONGO_URL)
db = cluster["standoff_bot"]
users_col = db["users"]

# Стани для FSM
class BuyGold(StatesGroup):
    waiting_for_amount = State()

# --- ТЕКСТИ ---
MESSAGES = {
    'ua': {
        'welcome': '🇺🇦 Оберіть мову:',
        'main_menu': '🏠 Головне меню',
        'profile': '👤 Профіль',
        'buy': '💰 Купити Голду',
        'sell': '📥 Продати Голду',
        'withdraw': '📤 Вивести Голду',
        'support': '🆘 Підтримка',
        'buy_title': "Price💰:\n100 голди - 32грн\n\n✍️Введіть сумму в грн, на яку хочете поповнити",
        'payment_confirm': "✅Супер\n💴До оплати: {uah}грн\n🫰🏻Получиш: {gold}g\n\nВиберіть спосіб оплати:",
        'profile_text': "ℹ️ **Інформація про вас:**\n\n🆔 `{id}`\n✨ **Баланс:** {balance} грн ≈ {gold} G\n\n**Куплено всього:** {bought} грн\n**Виведено всього:** {withdrawn} G\n**Виводів:** {w_count}\n\n**Запрошено друзів:** {friends}\n\n🗓️ **Реєстрація:** {reg_date}"
    },
    'ru': {
        'welcome': '🇷🇺 Выберите язык:',
        'main_menu': '🏠 Главное меню',
        'profile': '👤 Профиль',
        'buy': '💰 Купить Голду',
        'sell': '📥 Продать Голду',
        'withdraw': '📤 Вывести Голду',
        'support': '🆘 Поддержка',
        'buy_title': "Price💰:\n100 голды - 32грн\n\n✍️Введите сумму в грн, на которую хотите пополнить",
        'payment_confirm': "✅Супер\n💴К оплате: {uah}грн\n🫰🏻Получишь: {gold}g\n\nВыберите способ оплаты:",
        'profile_text': "ℹ️ **Информация о вас:**\n\n🆔 `{id}`\n✨ **Баланс:** {balance} грн ≈ {gold} G\n\n**Куплено всего:** {bought} грн\n**Выведено всего:** {withdrawn} G\n**Выводов:** {w_count}\n\n**Приглашено друзей:** {friends}\n\n🗓️ **Регистрация:** {reg_date}"
    },
    'en': {
        'welcome': '🇬🇧 Choose language:',
        'main_menu': '🏠 Main menu',
        'profile': '👤 Profile',
        'buy': '💰 Buy Gold',
        'sell': '📥 Sell Gold',
        'withdraw': '📤 Withdraw Gold',
        'support': '🆘 Support',
        'buy_title': "Price💰:\n100 gold - 32 UAH\n\n✍️Enter the amount in UAH you want to top up",
        'payment_confirm': "✅Great\n💴To pay: {uah} UAH\n🫰🏻You get: {gold}g\n\nChoose payment method:",
        'profile_text': "ℹ️ **Information about you:**\n\n🆔 `{id}`\n✨ **Balance:** {balance} UAH ≈ {gold} G\n\n**Total bought:** {bought} UAH\n**Total withdrawn:** {withdrawn} G\n**Withdrawals:** {w_count}\n\n**Friends invited:** {friends}\n\n🗓️ **Registration:** {reg_date}"
    }
}

# --- КЛАВІАТУРИ ---
def get_lang_kb():
    b = InlineKeyboardBuilder()
    b.button(text="Українська 🇺🇦", callback_data="setlang_ua")
    b.button(text="Русский 🇷🇺", callback_data="setlang_ru")
    b.button(text="English 🇬🇧", callback_data="setlang_en")
    return b.adjust(1).as_markup()

def get_main_kb(lang):
    b = ReplyKeyboardBuilder()
    b.row(types.KeyboardButton(text=MESSAGES[lang]['buy']), types.KeyboardButton(text=MESSAGES[lang]['sell']))
    b.row(types.KeyboardButton(text=MESSAGES[lang]['withdraw']))
    b.row(types.KeyboardButton(text=MESSAGES[lang]['profile']), types.KeyboardButton(text=MESSAGES[lang]['support']))
    return b.as_markup(resize_keyboard=True)

def get_pay_kb():
    b = InlineKeyboardBuilder()
    b.button(text="💳 Карта", callback_data="pay_card")
    b.button(text="💎 Crypto Bot", callback_data="pay_crypto")
    return b.adjust(1).as_markup()

# --- ХЕНДЛЕРИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if not user:
        await users_col.insert_one({
            "user_id": message.from_user.id, "lang": "ua", "balance_uah": 0.0,
            "total_bought": 0.0, "total_withdrawn": 0.0, "withdrawals_count": 0,
            "friends_count": 0, "reg_date": datetime.now().strftime("%d.%m.%Y")
        })
    await message.answer("🇺🇦 Оберіть мову / 🇷🇺 Выберите язык / 🇬🇧 Choose language:", reply_markup=get_lang_kb())

@dp.callback_query(F.data.startswith("setlang_"))
async def set_lang(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    await users_col.update_one({"user_id": callback.from_user.id}, {"$set": {"lang": lang}})
    await callback.message.delete()
    await callback.message.answer(MESSAGES[lang]['main_menu'], reply_markup=get_main_kb(lang))

@dp.message(lambda m: any(m.text == MESSAGES[l]['profile'] for l in MESSAGES))
async def show_profile(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user.get('lang', 'ua')
    text = MESSAGES[lang]['profile_text'].format(
        id=user['user_id'], balance=user['balance_uah'], gold=user['balance_uah'] * 3.125,
        bought=user['total_bought'], withdrawn=user['total_withdrawn'],
        w_count=user['withdrawals_count'], friends=user['friends_count'], reg_date=user['reg_date']
    )
    await message.answer(text, parse_mode="Markdown")

# Логіка Купівлі
@dp.message(lambda m: any(m.text == MESSAGES[l]['buy'] for l in MESSAGES))
async def buy_gold_start(message: types.Message, state: FSMContext):
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user.get('lang', 'ua')
    await message.answer(MESSAGES[lang]['buy_title'])
    await state.set_state(BuyGold.waiting_for_amount)

@dp.message(BuyGold.waiting_for_amount)
async def buy_gold_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Введіть число!")
        return
    uah = int(message.text)
    gold = round((uah / 32) * 100, 2)
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user.get('lang', 'ua')
    await message.answer(MESSAGES[lang]['payment_confirm'].format(uah=uah, gold=gold), reply_markup=get_pay_kb())
    await state.clear()

@dp.message(lambda m: any(m.text == MESSAGES[l]['support'] for l in MESSAGES))
async def support(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user.get('lang', 'ua')
    await message.answer(f"🆘 {MESSAGES[lang]['support']}: {SUPPORT_LINK}")

# Адмін-команда: /pay ID СУМА
@dp.message(Command("pay"))
async def admin_pay(message: types.Message):
    if str(message.from_user.id) != ADMIN_ID: return
    try:
        _, uid, amount = message.text.split()
        await users_col.update_one({"user_id": int(uid)}, {"$inc": {"balance_uah": float(amount)}})
        await message.answer(f"✅ Баланс {uid} змінено на {amount}")
    except: await message.answer("❌ Формат: `/pay 12345 100`")

async def main():
    try:
        await cluster.admin.command('ping')
        print("MongoDB підключено!")
    except Exception as e:
        print(f"Помилка БД: {e}"); return
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
