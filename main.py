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
ADMIN_ID = os.getenv("ADMIN_ID")
CRYPTO_TOKEN = os.getenv("CRYPTO_PAY_TOKEN")
SUPPORT_LINK = "@YAKUZA_N3" 

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
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
        'sell_title': "💲 <b>Введіть кількість голди, яку ви хочете продати:</b>\n«Мінімум 100 голди»",
        'sell_confirm': "💰 За продажу ваших <b>{gold}</b> голди ви получите <b>{uah} грн</b> на протязі 15 хвилин!\n\nДля продажі пишіть: @YAKUZA_N3",
        'calc_main': "❗️0.32грн за 1G\n\n100g 32грн\n200g 64грн\n500g 160грн\n1000g 320грн\n\nБудь ласка, виберіть варіант нижче ⬇️",
        'calc_u_g': "Порахувати гривні в голду", 'calc_g_u': "Порахувати голду в гривні",
        'enter_uah': "Введіть суму в гривнях ₴:", 'enter_gold': "Введіть кількість голди G:",
        'in_dev': "🛠 В розробці",
        'profile_text': "ℹ️ <b>Інформація про вас:</b>\n\n🆔 <code>{id}</code>\n✨ <b>Баланс:</b> {balance} грн\n\n<b>Куплено всього:</b> {bought} грн\n<b>Виведено всього:</b> {withdrawn} G\n<b>Виводів:</b> {w_count}\n\n<b>Запрошено друзів:</b> {friends}\n\n🗓️ <b>Реєстрація:</b> {reg_date}"
    },
    'ru': {
        'buy': '💰 Купить Голду', 'sell': '📥 Продать Голду', 'profile': '👤 Профиль',
        'support': '🆘 Поддержка', 'withdraw': '📤 Вывести Голду', 'calc': '🧮 Подсчет',
        'welcome': '🇷🇺 Выберите язык:', 'main_menu': '🏠 Главное меню',
        'buy_title': "Price💰:\n100 голды - 32грн\n\n✍️ <b>Введите сумму в грн, на которую хотите пополнить</b>",
        'buy_min_error': "❌ Минимум для покупки должен быть 32грн!",
        'pay_confirm': "✅ <b>Супер</b>\n💴 <b>К оплате:</b> {uah}грн\n🫰🏻 <b>Получишь:</b> {gold}g\n\nВыберите способ оплаты:",
        'sell_title': "💲 <b>Введите количество голды:</b>\n«Минимум 100 голды»",
        'sell_confirm': "💰 За продажу <b>{gold}</b> голды вы получите <b>{uah} грн</b> в течении 15 минут!\n\nДля продажи пишите: @YAKUZA_N3",
        'calc_main': "❗️0.32грн за 1G\n\n100g 32грн\n200g 64грн\n500g 160грн\n1000g 320грн\n\nПожалуйста, выберите вариант ниже ⬇️",
        'calc_u_g': "Посчитать гривны в голду", 'calc_g_u': "Посчитать голду в гривны",
        'enter_uah': "Введите сумму в гривнах ₴:", 'enter_gold': "Введите количество голды G:",
        'in_dev': "🛠 В разработке",
        'profile_text': "ℹ️ <b>Информация о вас:</b>\n\n🆔 <code>{id}</code>\n✨ <b>Баланс:</b> {balance} грн\n\n<b>Куплено всего:</b> {bought} грн\n<b>Выведено всего:</b> {withdrawn} G\n<b>Выводов:</b> {w_count}\n\n<b>Запрошено друзей:</b> {friends}\n\n🗓️ <b>Регистрация:</b> {reg_date}"
    },
    'en': {
        'buy': '💰 Buy Gold', 'sell': '📥 Sell Gold', 'profile': '👤 Profile',
        'support': '🆘 Support', 'withdraw': '📤 Withdraw Gold', 'calc': '🧮 Calculator',
        'welcome': '🇬🇧 Choose language:', 'main_menu': '🏠 Main menu',
        'buy_title': "Price💰:\n100 gold - 32 UAH\n\n✍️ <b>Enter the amount in UAH</b>",
        'buy_min_error': "❌ Minimum purchase is 32 UAH!",
        'pay_confirm': "✅ <b>Great</b>\n💴 <b>To pay:</b> {uah} UAH\n🫰🏻 <b>You get:</b> {gold}g\n\nChoose payment method:",
        'sell_title': "💲 <b>Enter gold amount:</b>\n«Min 100 gold»",
        'sell_confirm': "💰 For <b>{gold}</b> gold you will get <b>{uah} UAH</b> within 15 minutes!\n\nTo sell write: @YAKUZA_N3",
        'calc_main': "❗️0.32 UAH for 1G\n\n100g 32UAH\n200g 64UAH\n500g 160UAH\n1000g 320UAH\n\nPlease choose an option ⬇️",
        'calc_u_g': "Calculate UAH to Gold", 'calc_g_u': "Calculate Gold to UAH",
        'enter_uah': "Enter amount in UAH ₴:", 'enter_gold': "Enter gold amount G:",
        'in_dev': "🛠 In development",
        'profile_text': "ℹ️ <b>Profile info:</b>\n\n🆔 <code>{id}</code>\n✨ <b>Balance:</b> {balance} UAH\n\n<b>Total bought:</b> {bought} UAH\n<b>Total withdrawn:</b> {withdrawn} G\n<b>Withdrawals:</b> {w_count}\n\n<b>Friends:</b> {friends}\n\n🗓️ <b>Registered:</b> {reg_date}"
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
    lang = user['lang']
    if not message.text.isdigit(): return await message.answer("⚠️ Число!")
    uah = int(message.text)
    if uah < 32: return await message.answer(MESSAGES[lang]['buy_min_error'])
    
    gold = round(uah / 0.32, 2)
    b = InlineKeyboardBuilder()
    b.button(text="💎 Crypto Bot", callback_data=f"crypto_{uah}")
    b.button(text="💳 Карта (Support)", url="https://t.me/YAKUZA_N3")
    await message.answer(MESSAGES[lang]['pay_confirm'].format(uah=uah, gold=gold), reply_markup=b.adjust(1).as_markup(), parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data.startswith("crypto_"))
async def create_invoice(callback: types.CallbackQuery):
    uah = float(callback.data.split("_")[1])
    try:
        invoice = await crypto.create_invoice(amount=uah, asset='USDT', currency_type='fiat', fiat='UAH')
        b = InlineKeyboardBuilder()
        b.button(text="💳 Оплатити", url=invoice.pay_url)
        b.button(text="✅ Перевірити оплату", callback_data=f"verify_{invoice.invoice_id}_{uah}")
        await callback.message.edit_text(f"🚀 <b>Рахунок створено!</b>\nСума: {uah} UAH\nОплатіть за посиланням нижче:", reply_markup=b.adjust(1).as_markup(), parse_mode="HTML")
    except:
        await callback.answer("❌ Помилка API Crypto Bot", show_alert=True)

@dp.callback_query(F.data.startswith("verify_"))
async def verify_pay(callback: types.CallbackQuery):
    _, inv_id, uah = callback.data.split("_")
    inv = await crypto.get_invoices(invoice_ids=int(inv_id))
    if inv and inv.status == 'paid':
        await users_col.update_one({"user_id": callback.from_user.id}, {"$inc": {"balance_uah": float(uah), "total_bought": float(uah)}})
        await callback.message.answer(f"✅ <b>Баланс поповнено на {uah} грн!</b>", parse_mode="HTML")
        await callback.message.delete()
    else:
        await callback.answer("⏳ Оплата не знайдена", show_alert=True)

# --- ПРОДАЖ ---
@dp.message(ShopStates.waiting_for_sell_gold)
async def sell_input(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("⚠️ Число!")
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
    await m.answer(f"✅ {m.text}грн ≈ {round(int(m.text)/0.32, 2)}G")
    await state.clear()

@dp.message(ShopStates.calc_gold_to_uah)
async def r_gu(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return
    await m.answer(f"✅ {m.text}G ≈ {round(int(m.text)*0.32, 2)}грн")
    await state.clear()

# --- СТАРТ ---
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": m.from_user.id})
    if not user:
        await users_col.insert_one({"user_id": m.from_user.id, "lang": "ua", "balance_uah": 0.0, "total_bought": 0.0, "total_withdrawn": 0.0, "withdrawals_count": 0, "friends_count": 0, "reg_date": datetime.now().strftime("%d.%m.%Y")})
    b = InlineKeyboardBuilder()
    for l in ['ua', 'ru', 'en']: b.button(text=l.upper(), callback_data=f"setlang_{l}")
    await m.answer("Мова / Язык / Language:", reply_markup=b.as_markup())

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
