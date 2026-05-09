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
from aiocryptopay import AioCryptoPay, Networks

# --- НАЛАШТУВАННЯ ---
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
CRYPTO_TOKEN = os.getenv("CRYPTO_PAY_TOKEN")
SUPPORT_LINK = "@YAKUZA_N3" 

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Переключено на MAIN_NET для реальних грошей
crypto = AioCryptoPay(token=CRYPTO_TOKEN, network=Networks.MAIN_NET)

cluster = AsyncIOMotorClient(MONGO_URL)
db = cluster["standoff_bot"]
users_col = db["users"]

class ShopStates(StatesGroup):
    waiting_for_buy_amount = State()
    waiting_for_sell_gold = State()
    calc_uah_to_gold = State()
    calc_gold_to_uah = State()

# --- ТЕКСТИ ---
MESSAGES = {
    'ua': {
        'buy': '💰 Купити Голду', 'sell': '📥 Продати Голду', 'profile': '👤 Профіль',
        'support': '🆘 Підтримка', 'withdraw': '📤 Вивести Голду', 'calc': '🧮 Підрахунок',
        'welcome': '🇺🇦 Оберіть мову:', 'main_menu': '🏠 Головне меню',
        'buy_title': "Price💰:\n100 голди - 32грн\n\n✍️ <b>Введіть сумму в грн, на яку хочете поповнити</b>",
        'buy_min_error': "❌ Мінімум для покупки має бути 32грн!",
        'pay_confirm': "✅ <b>Супер</b>\n💴 <b>До оплати:</b> {uah}грн\n🫰🏻 <b>Получиш:</b> {gold}g\n\nВиберіть спосіб оплати:",
        'sell_title': "💲 <b>Введіть кількість голди:</b>\n«Мінімум 100 голди»",
        'sell_confirm': "💰 За продажу <b>{gold}</b> голди ви отримаєте <b>{uah} грн</b> протягом 15 хвилин!\n\nДля продажу пишіть: @YAKUZA_N3",
        'calc_main': "❗️0.32грн за 1G\n\n100g 32грн\n200g 64грн\n500g 160грн\n1000g 320грн\n\nОберіть варіант нижче ⬇️",
        'calc_u_g': "Гривні в голду", 'calc_g_u': "Голда в гривні",
        'enter_uah': "Введіть суму в гривнях ₴:", 'enter_gold': "Введіть кількість голди G:",
        'in_dev': "🛠 В розробці",
        'profile_text': "ℹ️ <b>Інформація про вас:</b>\n\n🆔 <code>{id}</code>\n✨ <b>Баланс:</b> {balance} грн\n\n<b>Куплено всього:</b> {bought} грн\n<b>Виведено всього:</b> {withdrawn} G\n<b>Виводів:</b> {w_count}\n\n<b>Друзі:</b> {friends}\n\n🗓️ <b>Реєстрація:</b> {reg_date}"
    },
    'ru': {
        'buy': '💰 Купить Голду', 'sell': '📥 Продать Голду', 'profile': '👤 Профиль',
        'support': '🆘 Поддержка', 'withdraw': '📤 Вывести Голду', 'calc': '🧮 Подсчет',
        'welcome': '🇷🇺 Выберите язык:', 'main_menu': '🏠 Главное меню',
        'buy_title': "Price💰:\n100 голды - 32грн\n\n✍️ <b>Введите сумму в грн</b>",
        'buy_min_error': "❌ Минимум для покупки — 32грн!",
        'pay_confirm': "✅ <b>Супер</b>\n💴 <b>К оплате:</b> {uah}грн\n🫰🏻 <b>Получишь:</b> {gold}g\n\nВыберите способ оплаты:",
        'sell_title': "💲 <b>Введите количество голды:</b>",
        'sell_confirm': "💰 За продажу <b>{gold}</b> голды вы получите <b>{uah} грн</b>!\n\nПисать сюда: @YAKUZA_N3",
        'calc_main': "❗️0.32грн за 1G\n\nВыберите вариант ⬇️",
        'calc_u_g': "Гривны в голду", 'calc_g_u': "Голда в гривны",
        'enter_uah': "Введите сумму в гривнах ₴:", 'enter_gold': "Введите количество голды G:",
        'in_dev': "🛠 В разработке",
        'profile_text': "ℹ️ <b>Информация:</b>\n\n🆔 <code>{id}</code>\n✨ <b>Баланс:</b> {balance} грн\n🗓️ <b>Регистрация:</b> {reg_date}"
    },
    'en': {
        'buy': '💰 Buy Gold', 'sell': '📥 Sell Gold', 'profile': '👤 Profile',
        'support': '🆘 Support', 'withdraw': '📤 Withdraw Gold', 'calc': '🧮 Calculator',
        'welcome': '🇬🇧 Choose language:', 'main_menu': '🏠 Main menu',
        'buy_title': "Price💰:\n100 gold - 32 UAH\n\n✍️ <b>Enter UAH amount</b>",
        'buy_min_error': "❌ Minimum purchase is 32 UAH!",
        'pay_confirm': "✅ <b>Great</b>\n💴 <b>Total:</b> {uah} UAH\n🫰🏻 <b>You get:</b> {gold}g\n\nChoose payment:",
        'sell_title': "💲 <b>Enter gold amount:</b>",
        'sell_confirm': "💰 You will get <b>{uah} UAH</b> for <b>{gold} gold</b>!\n\nContact: @YAKUZA_N3",
        'calc_main': "❗️0.32 UAH per 1G\n\nChoose an option ⬇️",
        'calc_u_g': "UAH to Gold", 'calc_g_u': "Gold to UAH",
        'enter_uah': "Enter amount in UAH ₴:", 'enter_gold': "Enter gold amount G:",
        'in_dev': "🛠 In development",
        'profile_text': "ℹ️ <b>Profile:</b>\n\n🆔 <code>{id}</code>\n✨ <b>Balance:</b> {balance} UAH\n🗓️ <b>Registered:</b> {reg_date}"
    }
}

# --- КЛАВІАТУРИ ---
def get_main_kb(lang):
    b = ReplyKeyboardBuilder()
    b.row(types.KeyboardButton(text=MESSAGES[lang]['buy']), types.KeyboardButton(text=MESSAGES[lang]['sell']))
    b.row(types.KeyboardButton(text=MESSAGES[lang]['withdraw']), types.KeyboardButton(text=MESSAGES[lang]['calc']))
    b.row(types.KeyboardButton(text=MESSAGES[lang]['profile']), types.KeyboardButton(text=MESSAGES[lang]['support']))
    return b.as_markup(resize_keyboard=True)

# --- РОУТЕР МЕНЮ ---
@dp.message(F.text.in_([MESSAGES[l][k] for l in MESSAGES for k in ['profile', 'support', 'withdraw', 'calc', 'buy', 'sell']]))
async def menu_handler(message: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user.get('lang', 'ua')
    txt = message.text

    if txt == MESSAGES[lang]['profile']:
        text = MESSAGES[lang]['profile_text'].format(
            id=user['user_id'], balance=user.get('balance_uah', 0.0),
            bought=user.get('total_bought', 0.0), withdrawn=user.get('total_withdrawn', 0.0),
            w_count=user.get('withdrawals_count', 0), friends=user.get('friends_count', 0), reg_date=user.get('reg_date', '--')
        )
        await message.answer(text, parse_mode="HTML")
    elif txt == MESSAGES[lang]['support']:
        await message.answer(f"🆘 Зв'язок з адміністратором: {SUPPORT_LINK}")
    elif txt == MESSAGES[lang]['withdraw']:
        await message.answer(MESSAGES[lang]['in_dev'])
    elif txt == MESSAGES[lang]['calc']:
        b = InlineKeyboardBuilder()
        b.button(text=MESSAGES[lang]['calc_u_g'], callback_data="calc_u_g")
        b.button(text=MESSAGES[lang]['calc_g_u'], callback_data="calc_g_u")
        await message.answer(MESSAGES[lang]['calc_main'], reply_markup=b.adjust(1).as_markup(), parse_mode="HTML")
    elif txt == MESSAGES[lang]['buy']:
        await message.answer(MESSAGES[lang]['buy_title'], parse_mode="HTML")
        await state.set_state(ShopStates.waiting_for_buy_amount)
    elif txt == MESSAGES[lang]['sell']:
        await message.answer(MESSAGES[lang]['sell_title'], parse_mode="HTML")
        await state.set_state(ShopStates.waiting_for_sell_gold)

# --- КУПІВЛЯ ТА CRYPTO PAY ---
@dp.message(ShopStates.waiting_for_buy_amount)
async def buy_input(message: types.Message, state: FSMContext):
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user.get('lang', 'ua')
    if not message.text.isdigit(): 
        return await message.answer("⚠️ Будь ласка, введіть число!")
    uah = int(message.text)
    if uah < 32: 
        return await message.answer(MESSAGES[lang]['buy_min_error'])
    
    gold = round(uah / 0.32, 2)
    b = InlineKeyboardBuilder()
    b.button(text="💎 Crypto Bot", callback_data=f"mainpay_{uah}")
    b.button(text="💳 Карта (Support)", url=f"https://t.me/{SUPPORT_LINK.replace('@', '')}")
    await message.answer(MESSAGES[lang]['pay_confirm'].format(uah=uah, gold=gold), reply_markup=b.adjust(1).as_markup(), parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data.startswith("mainpay_"))
async def create_invoice(callback: types.CallbackQuery):
    uah = float(callback.data.split("_")[1])
    try:
        # Рахунок у справжній мережі
        invoice = await crypto.create_invoice(amount=uah, asset='USDT', currency_type='fiat', fiat='UAH')
        b = InlineKeyboardBuilder()
        b.button(text="🔗 Оплатити", url=invoice.pay_url)
        b.button(text="✅ Перевірити", callback_data=f"final_{invoice.invoice_id}_{uah}")
        await callback.message.edit_text(f"🚀 <b>Рахунок створено!</b>\nСума: {uah} UAH\n\n<i>Натисніть кнопку 'Оплатити' для переходу в Crypto Bot.</i>", reply_markup=b.adjust(1).as_markup(), parse_mode="HTML")
    except Exception as e:
        print(f"MAIN_NET Error: {e}")
        await callback.answer("❌ Помилка Crypto Pay. Перевірте токен додатку.", show_alert=True)

@dp.callback_query(F.data.startswith("final_"))
async def verify_pay(callback: types.CallbackQuery):
    _, inv_id, uah = callback.data.split("_")
    inv = await crypto.get_invoices(invoice_ids=int(inv_id))
    
    if inv and inv.status == 'paid':
        await users_col.update_one({"user_id": callback.from_user.id}, {"$inc": {"balance_uah": float(uah), "total_bought": float(uah)}})
        await callback.message.answer(f"✅ <b>Оплата підтверджена!</b>\nНа ваш баланс зараховано {uah} грн.")
        await callback.message.delete()
    else:
        await callback.answer("⏳ Оплата не знайдена.", show_alert=True)

# --- ПРОДАЖ ---
@dp.message(ShopStates.waiting_for_sell_gold)
async def sell_input(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("⚠️ Введіть число!")
    gold = int(message.text)
    if gold < 100: return await message.answer("❌ Мінімум 100 голди!")
    user = await users_col.find_one({"user_id": message.from_user.id})
    uah = round(gold * 0.22, 2)
    await message.answer(MESSAGES[user['lang']]['sell_confirm'].format(gold=gold, uah=uah), parse_mode="HTML")
    await state.clear()

# --- КАЛЬКУЛЯТОР ---
@dp.callback_query(F.data == "calc_u_g")
async def c_ug(c: types.CallbackQuery, state: FSMContext):
    user = await users_col.find_one({"user_id": c.from_user.id})
    await c.message.answer(MESSAGES[user['lang']]['enter_uah'])
    await state.set_state(ShopStates.calc_uah_to_gold)
    await c.answer()

@dp.callback_query(F.data == "calc_g_u")
async def c_gu(c: types.CallbackQuery, state: FSMContext):
    user = await users_col.find_one({"user_id": c.from_user.id})
    await c.message.answer(MESSAGES[user['lang']]['enter_gold'])
    await state.set_state(ShopStates.calc_gold_to_uah)
    await c.answer()

@dp.message(ShopStates.calc_uah_to_gold)
async def r_ug(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return
    await m.answer(f"✅ <b>{m.text}грн</b> ≈ <b>{round(int(m.text)/0.32, 2)}G</b>", parse_mode="HTML")
    await state.clear()

@dp.message(ShopStates.calc_gold_to_uah)
async def r_gu(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return
    await m.answer(f"✅ <b>{m.text}G</b> ≈ <b>{round(int(m.text)*0.32, 2)}грн</b>", parse_mode="HTML")
    await state.clear()

# --- СТАРТ ТА МОВИ ---
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": m.from_user.id})
    if not user:
        await users_col.insert_one({"user_id": m.from_user.id, "lang": "ua", "balance_uah": 0.0, "total_bought": 0.0, "total_withdrawn": 0.0, "withdrawals_count": 0, "friends_count": 0, "reg_date": datetime.now().strftime("%d.%m.%Y")})
    
    b = InlineKeyboardBuilder()
    b.button(text="Українська 🇺🇦", callback_data="setlang_ua")
    b.button(text="Русский 🇷🇺", callback_data="setlang_ru")
    b.button(text="English 🇬🇧", callback_data="setlang_en")
    await m.answer("Оберіть мову / Выберите язык / Choose language:", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("setlang_"))
async def set_l(c: types.CallbackQuery):
    lang = c.data.split("_")[1]
    await users_col.update_one({"user_id": c.from_user.id}, {"$set": {"lang": lang}})
    await c.message.delete()
    await c.message.answer(MESSAGES[lang]['main_menu'], reply_markup=get_main_kb(lang))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
