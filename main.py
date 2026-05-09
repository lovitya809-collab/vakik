import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from motor.motor_asyncio import AsyncIOMotorClient

# --- НАЛАШТУВАННЯ ---
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
ADMIN_ID = os.getenv("ADMIN_ID")
SUPPORT_LINK = "@YAKUZA_N3" 

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Підключення до БД
cluster = AsyncIOMotorClient(MONGO_URL)
db = cluster["standoff_bot"]
users_col = db["users"]

# Стани для діалогів
class ShopStates(StatesGroup):
    waiting_for_buy_amount = State()
    waiting_for_sell_gold = State()

# --- ТЕКСТИ ---
MESSAGES = {
    'ua': {
        'welcome': '🇺🇦 Оберіть мову / Choose language:',
        'main_menu': '🏠 Головне меню',
        'profile': '👤 Профіль',
        'buy': '💰 Купити Голду',
        'sell': '📥 Продати Голду',
        'withdraw': '📤 Вивести Голду',
        'support': '🆘 Підтримка',
        'buy_title': "Price💰:\n100 голди - 32грн\n\n✍️ Введіть сумму в грн, на яку хочете поповнити",
        'pay_confirm': "✅ Супер\n💴 До оплати: {uah}грн\n🫰🏻 Получиш: {gold}g\n\nВиберіть спосіб оплати:",
        'sell_title': "💲 Введіть кількість голди, яку ви хочете продати:\n«Мінімум 100 голди»",
        'sell_confirm': "💰 За продажу ваших {gold} голди ви получите {uah} грн на протязі 15 хвилин!\n\nДля продажі пишіть: @YAKUZA_N3",
        'profile_text': "ℹ️ **Інформація про вас:**\n\n🆔 `{id}`\n✨ **Баланс:** {balance} грн\n\n**Куплено всього:** {bought} грн\n**Виведено всього:** {withdrawn} G\n**Виводів:** {w_count}\n\n**Запрошено друзів:** {friends}\n\n🗓️ **Реєстрація:** {reg_date}"
    }
}
# Дублюємо для RU/EN, щоб бот не падав, якщо мова не UA
MESSAGES['ru'] = MESSAGES['ua']
MESSAGES['en'] = MESSAGES['ua']

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

def get_pay_methods_kb():
    b = InlineKeyboardBuilder()
    b.button(text="💳 Карта", callback_data="method_card")
    b.button(text="💎 Crypto Bot", callback_data="method_crypto")
    return b.adjust(1).as_markup()

# --- ХЕНДЛЕРИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear() # Скидаємо стани при старті
    user = await users_col.find_one({"user_id": message.from_user.id})
    if not user:
        await users_col.insert_one({
            "user_id": message.from_user.id, "lang": "ua", "balance_uah": 0.0,
            "total_bought": 0.0, "total_withdrawn": 0.0, "withdrawals_count": 0,
            "friends_count": 0, "reg_date": datetime.now().strftime("%d.%m.%Y")
        })
    await message.answer(MESSAGES['ua']['welcome'], reply_markup=get_lang_kb())

@dp.callback_query(F.data.startswith("setlang_"))
async def set_lang(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    await users_col.update_one({"user_id": callback.from_user.id}, {"$set": {"lang": lang}})
    await callback.message.delete()
    await callback.message.answer(MESSAGES[lang]['main_menu'], reply_markup=get_main_kb(lang))

# --- КУПІВЛЯ (BUY) ---
@dp.message(F.text.contains("Купити") | F.text.contains("Buy") | F.text.contains("Купить"))
async def buy_start(message: types.Message, state: FSMContext):
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user.get('lang', 'ua') if user else 'ua'
    await message.answer(MESSAGES[lang]['buy_title'])
    await state.set_state(ShopStates.waiting_for_buy_amount)

@dp.message(ShopStates.waiting_for_buy_amount)
async def buy_process(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Будь ласка, введіть суму числом!")
        return
    uah = int(message.text)
    gold = round((uah / 32) * 100, 2)
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user.get('lang', 'ua') if user else 'ua'
    await message.answer(MESSAGES[lang]['pay_confirm'].format(uah=uah, gold=gold), reply_markup=get_pay_methods_kb())
    await state.clear()

# --- ПРОДАЖ (SELL) ---
@dp.message(F.text.contains("Продати") | F.text.contains("Sell") | F.text.contains("Продать"))
async def sell_start(message: types.Message, state: FSMContext):
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user.get('lang', 'ua') if user else 'ua'
    await message.answer(MESSAGES[lang]['sell_title'], parse_mode="Markdown")
    await state.set_state(ShopStates.waiting_for_sell_gold)

@dp.message(ShopStates.waiting_for_sell_gold)
async def sell_process(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Введіть кількість голди числом!")
        return
    gold = int(message.text)
    if gold < 100:
        await message.answer("❌ Мінімум 100 голди! Спробуйте ще раз або натисніть /start")
        return
    
    uah = round(gold * 0.22, 2)
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user.get('lang', 'ua') if user else 'ua'
    
    await message.answer(MESSAGES[lang]['sell_confirm'].format(gold=gold, uah=uah), parse_mode="Markdown")
    await state.clear()

# --- ПРОФІЛЬ ТА ПІДТРИМКА ---
@dp.message(F.text.contains("Профіль") | F.text.contains("Profile") | F.text.contains("Профиль"))
async def profile(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if not user: return
    lang = user.get('lang', 'ua')
    text = MESSAGES[lang]['profile_text'].format(
        id=user['user_id'], balance=user['balance_uah'], 
        bought=user['total_bought'], withdrawn=user['total_withdrawn'],
        w_count=user['withdrawals_count'], friends=user['friends_count'], reg_date=user['reg_date']
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text.contains("Підтримка") | F.text.contains("Support") | F.text.contains("Поддержка"))
async def support(message: types.Message):
    await message.answer(f"🆘 Зв'язок з адміністратором: {SUPPORT_LINK}")

# Адмін-команда: /pay ID СУМА
@dp.message(Command("pay"))
async def admin_pay(message: types.Message):
    if str(message.from_user.id) != ADMIN_ID: return
    try:
        _, uid, amount = message.text.split()
        await users_col.update_one({"user_id": int(uid)}, {"$inc": {"balance_uah": float(amount)}})
        await message.answer(f"✅ Користувачу {uid} нараховано {amount} грн")
    except: await message.answer("Формат: `/pay 12345 100`", parse_mode="Markdown")

async def main():
    try:
        await cluster.admin.command('ping')
        print("MongoDB успішно підключено!")
    except Exception as e:
        print(f"Помилка БД: {e}"); return
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
