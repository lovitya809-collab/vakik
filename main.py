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

cluster = AsyncIOMotorClient(MONGO_URL)
db = cluster["standoff_bot"]
users_col = db["users"]

class ShopStates(StatesGroup):
    waiting_for_buy_amount = State()
    waiting_for_sell_gold = State()
    calc_uah_to_gold = State()
    calc_gold_to_uah = State()

# --- МОВНА ПАНЕЛЬ ---
MESSAGES = {
    'ua': {
        'buy': '💰 Купити Голду', 'sell': '📥 Продати Голду', 'profile': '👤 Профіль',
        'support': '🆘 Підтримка', 'withdraw': '📤 Вивести Голду', 'calc': '🧮 Підрахунок',
        'welcome': '🇺🇦 Оберіть мову:', 'main_menu': '🏠 Головне меню',
        'buy_title': "Price💰:\n100 голди - 32грн\n\n✍️ <b>Введіть сумму в грн, на яку хочете поповнити</b>",
        'sell_title': "💲 <b>Введіть кількість голди:</b>\n«Мінімум 100 голди»",
        'calc_main': "❗️0.32грн за 1G\n\n100g 32грн\n200g 64грн\n500g 160грн\n1000g 320грн\n\nБудь ласка, виберіть варіант нижче ⬇️",
        'calc_u_g': "Порахувати гривні в голду", 'calc_g_u': "Порахувати голду в гривні",
        'enter_uah': "Введіть суму в гривнях ₴:", 'enter_gold': "Введіть кількість голди G:",
        'profile_text': "🆔 <code>{id}</code>\n✨ <b>Баланс:</b> {balance} грн\n🗓️ Реєстрація: {reg_date}"
    },
    'ru': {
        'buy': '💰 Купить Голду', 'sell': '📥 Продать Голду', 'profile': '👤 Профиль',
        'support': '🆘 Поддержка', 'withdraw': '📤 Вывести Голду', 'calc': '🧮 Подсчет',
        'welcome': '🇷🇺 Выберите язык:', 'main_menu': '🏠 Главное меню',
        'buy_title': "Price💰:\n100 голды - 32грн\n\n✍️ <b>Введите сумму в грн, на которую хотите пополнить</b>",
        'sell_title': "💲 <b>Введите количество голды:</b>\n«Минимум 100 голды»",
        'calc_main': "❗️0.32грн за 1G\n\n100g 32грн\n200g 64грн\n500g 160грн\n1000g 320грн\n\nПожалуйста, выберите вариант ниже ⬇️",
        'calc_u_g': "Посчитать гривны в голду", 'calc_g_u': "Посчитать голду в гривны",
        'enter_uah': "Введите сумму в гривнах ₴:", 'enter_gold': "Введите количество голды G:",
        'profile_text': "🆔 <code>{id}</code>\n✨ <b>Баланс:</b> {balance} грн\n🗓️ Регистрация: {reg_date}"
    },
    'en': {
        'buy': '💰 Buy Gold', 'sell': '📥 Sell Gold', 'profile': '👤 Profile',
        'support': '🆘 Support', 'withdraw': '📤 Withdraw Gold', 'calc': '🧮 Calculator',
        'welcome': '🇬🇧 Choose language:', 'main_menu': '🏠 Main menu',
        'buy_title': "Price💰:\n100 gold - 32 UAH\n\n✍️ <b>Enter the amount in UAH</b>",
        'sell_title': "💲 <b>Enter gold amount:</b>\n«Min 100 gold»",
        'calc_main': "❗️0.32 UAH for 1G\n\n100g 32UAH\n200g 64UAH\n500g 160UAH\n1000g 320UAH\n\nPlease choose an option ⬇️",
        'calc_u_g': "Calculate UAH to Gold", 'calc_g_u': "Calculate Gold to UAH",
        'enter_uah': "Enter amount in UAH ₴:", 'enter_gold': "Enter gold amount G:",
        'profile_text': "🆔 <code>{id}</code>\n✨ <b>Balance:</b> {balance} UAH\n🗓️ Reg date: {reg_date}"
    }
}

# --- КЛАВІАТУРИ ---
def get_main_kb(lang):
    b = ReplyKeyboardBuilder()
    b.row(types.KeyboardButton(text=MESSAGES[lang]['buy']), types.KeyboardButton(text=MESSAGES[lang]['sell']))
    b.row(types.KeyboardButton(text=MESSAGES[lang]['withdraw']), types.KeyboardButton(text=MESSAGES[lang]['calc']))
    b.row(types.KeyboardButton(text=MESSAGES[lang]['profile']), types.KeyboardButton(text=MESSAGES[lang]['support']))
    return b.as_markup(resize_keyboard=True)

def get_calc_kb(lang):
    b = InlineKeyboardBuilder()
    b.button(text=MESSAGES[lang]['calc_u_g'], callback_data="calc_u_g")
    b.button(text=MESSAGES[lang]['calc_g_u'], callback_data="calc_g_u")
    return b.adjust(1).as_markup()

# --- ФУНКЦІЯ ПЕРЕВІРКИ КНОПОК МЕНЮ ---
async def check_menu_click(message: types.Message, state: FSMContext, lang: str):
    menu_texts = [MESSAGES[lang][k] for k in ['buy', 'sell', 'profile', 'support', 'withdraw', 'calc']]
    if message.text in menu_texts:
        await state.clear()
        return True
    return False

# --- ХЕНДЛЕРИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": message.from_user.id})
    if not user:
        await users_col.insert_one({"user_id": message.from_user.id, "lang": "ua", "balance_uah": 0.0, "reg_date": datetime.now().strftime("%d.%m.%Y")})
    
    b = InlineKeyboardBuilder()
    for l in ['ua', 'ru', 'en']: b.button(text=l.upper(), callback_data=f"setlang_{l}")
    await message.answer("Оберіть мову / Выберите язык / Choose language:", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("setlang_"))
async def set_lang(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    await users_col.update_one({"user_id": callback.from_user.id}, {"$set": {"lang": lang}})
    await callback.message.delete()
    await callback.message.answer(MESSAGES[lang]['main_menu'], reply_markup=get_main_kb(lang))

# Підрахунок (Калькулятор)
@dp.message(F.text.contains("Підрахунок") | F.text.contains("Подсчет") | F.text.contains("Calculator"))
async def calc_start(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user['lang']
    await message.answer(MESSAGES[lang]['calc_main'], reply_markup=get_calc_kb(lang), parse_mode="HTML")

@dp.callback_query(F.data == "calc_u_g")
async def calc_ug(callback: types.CallbackQuery, state: FSMContext):
    user = await users_col.find_one({"user_id": callback.from_user.id})
    await callback.message.answer(MESSAGES[user['lang']]['enter_uah'])
    await state.set_state(ShopStates.calc_uah_to_gold)

@dp.callback_query(F.data == "calc_g_u")
async def calc_gu(callback: types.CallbackQuery, state: FSMContext):
    user = await users_col.find_one({"user_id": callback.from_user.id})
    await callback.message.answer(MESSAGES[user['lang']]['enter_gold'])
    await state.set_state(ShopStates.calc_gold_to_uah)

@dp.message(ShopStates.calc_uah_to_gold)
async def res_ug(message: types.Message, state: FSMContext):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if await check_menu_click(message, state, user['lang']): return
    if not message.text.isdigit(): return await message.answer("⚠️ Число!")
    res = round(int(message.text) / 0.32, 2)
    await message.answer(f"✅ {message.text}.00грн ≈ {res}G")
    await state.clear()

@dp.message(ShopStates.calc_gold_to_uah)
async def res_gu(message: types.Message, state: FSMContext):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if await check_menu_click(message, state, user['lang']): return
    if not message.text.isdigit(): return await message.answer("⚠️ Число!")
    res = round(int(message.text) * 0.32, 2)
    await message.answer(f"✅ {message.text}G ≈ {res}грн")
    await state.clear()

# Решта функцій (Купівля/Продаж/Профіль) з виправленням скидання стану
@dp.message(F.text.contains("Купити") | F.text.contains("Buy") | F.text.contains("Купить"))
async def buy_s(message: types.Message, state: FSMContext):
    user = await users_col.find_one({"user_id": message.from_user.id}); lang = user['lang']
    await message.answer(MESSAGES[lang]['buy_title'], parse_mode="HTML")
    await state.set_state(ShopStates.waiting_for_buy_amount)

@dp.message(ShopStates.waiting_for_buy_amount)
async def buy_p(message: types.Message, state: FSMContext):
    user = await users_col.find_one({"user_id": message.from_user.id}); lang = user['lang']
    if await check_menu_click(message, state, lang): return
    if not message.text.isdigit(): return await message.answer("⚠️ Введіть число!")
    uah = int(message.text); gold = round(uah / 0.32, 2)
    b = InlineKeyboardBuilder()
    b.button(text="💳 Карта", callback_data="m_c"); b.button(text="💎 Crypto Bot", callback_data="m_cr")
    await message.answer(MESSAGES[lang]['pay_confirm'].format(uah=uah, gold=gold), reply_markup=b.adjust(1).as_markup(), parse_mode="HTML")
    await state.clear()

@dp.message(F.text.contains("Профіль") | F.text.contains("Profile"))
async def profile(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id}); lang = user['lang']
    text = MESSAGES[lang]['profile_text'].format(id=user['user_id'], balance=user['balance_uah'], reg_date=user['reg_date'])
    await message.answer(text, parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
