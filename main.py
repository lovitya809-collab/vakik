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
ADMIN_ID = int(os.getenv("ADMIN_ID")) # ID адміна для заявок
SUPPORT_LINK = "@YAKUZA_N3" 

# Карти
CARDS = {
    "monobank": "4874100038378298",
    "abank": "4323345041637175"
}

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

cluster = AsyncIOMotorClient(MONGO_URL)
db = cluster["standoff_bot"]
users_col = db["users"]

class ShopStates(StatesGroup):
    waiting_for_buy_amount = State()
    waiting_for_receipt = State()
    waiting_for_withdraw_amount = State()
    calc_uah_to_gold = State()
    calc_gold_to_uah = State()

# --- ТЕКСТИ ---
MESSAGES = {
    'ua': {
        'buy': '💰 Купити Голду', 'sell': '📥 Продати Голду', 'profile': '👤 Профіль',
        'support': '🆘 Підтримка', 'withdraw': '📤 Вивести Голду', 'calc': '🧮 Підрахунок',
        'main_menu': '🏠 Головне меню',
        'buy_title': "Price💰:\n100 голди - 32грн\n\n✍️ <b>Введіть сумму в грн, на яку хочете поповнити</b>",
        'buy_min_error': "❌ Мінімум для покупки має бути 32грн!",
        'withdraw_info': "Ви бажаєте вивести голду.\nБудь ласка, напишіть кількість голди для виведення.\nМінімальна кількість 100G",
        'withdraw_next': "Кількість голди для виведення: {gold}G\nНапишіть {support} для подальшої інструкції для виведення!"
    },
    # Додайте аналогічні переклади для ru/en за потреби
}

# --- КЛАВІАТУРИ ---
def get_main_kb(lang):
    b = ReplyKeyboardBuilder()
    b.row(types.KeyboardButton(text=MESSAGES[lang]['buy']), types.KeyboardButton(text=MESSAGES[lang]['sell']))
    b.row(types.KeyboardButton(text=MESSAGES[lang]['withdraw']), types.KeyboardButton(text=MESSAGES[lang]['calc']))
    b.row(types.KeyboardButton(text=MESSAGES[lang]['profile']), types.KeyboardButton(text=MESSAGES[lang]['support']))
    return b.as_markup(resize_keyboard=True)

# --- ГРУПА ХЕНДЛЕРІВ МЕНЮ ---
@dp.message(F.text.in_([MESSAGES['ua'][k] for k in ['profile', 'support', 'withdraw', 'calc', 'buy', 'sell']]))
async def menu_router(message: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": message.from_user.id})
    lang = user.get('lang', 'ua')
    txt = message.text

    if txt == MESSAGES[lang]['profile']:
        text = f"ℹ️ <b>Профіль:</b>\n🆔 <code>{user['user_id']}</code>\n✨ <b>Баланс:</b> {user.get('balance_uah', 0.0)} грн\n🗓️ <b>Реєстрація:</b> {user.get('reg_date', '--')}"
        await message.answer(text, parse_mode="HTML")
    elif txt == MESSAGES[lang]['support']:
        await message.answer(f"🆘 Підтримка: {SUPPORT_LINK}")
    elif txt == MESSAGES[lang]['calc']:
        b = InlineKeyboardBuilder()
        b.button(text="Гривні в голду", callback_data="calc_u_g")
        b.button(text="Голда в гривні", callback_data="calc_g_u")
        await message.answer("🧮 Калькулятор:", reply_markup=b.adjust(1).as_markup())
    elif txt == MESSAGES[lang]['buy']:
        await message.answer(MESSAGES[lang]['buy_title'], parse_mode="HTML")
        await state.set_state(ShopStates.waiting_for_buy_amount)
    elif txt == MESSAGES[lang]['withdraw']:
        await message.answer(MESSAGES[lang]['withdraw_info'])
        await state.set_state(ShopStates.waiting_for_withdraw_amount)

# --- ПРОЦЕС КУПІВЛІ (КАРТА) ---
@dp.message(ShopStates.waiting_for_buy_amount)
async def process_buy_amt(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("⚠️ Число!")
    uah = int(message.text)
    if uah < 32: return await message.answer("❌ Мінімум 32 грн!")
    
    await state.update_data(buy_uah=uah)
    b = InlineKeyboardBuilder()
    b.button(text="💳 Монобанк", callback_data="pay_mono")
    b.button(text="💳 Абанк", callback_data="pay_abank")
    await message.answer("Оберіть банк для оплати:", reply_markup=b.adjust(1).as_markup())

@dp.callback_query(F.data.startswith("pay_"))
async def choose_bank(callback: types.CallbackQuery, state: FSMContext):
    bank_type = callback.data.split("_")[1]
    data = await state.get_data()
    uah = data['buy_uah']
    gold = round(uah / 0.32, 2)
    bank_name = "Monobank" if bank_type == "mono" else "Абанк"
    card_num = CARDS['monobank'] if bank_type == "mono" else CARDS['abank']
    
    await state.update_data(bank=bank_name, gold=gold)
    
    text = (
        f"<b>Заявка на покупку Голди💰</b>\n\n"
        f"До сплати: <b>{uah} грн</b>\n"
        f"Получиш: <b>{gold}g</b>\n\n"
        f"Банк: <b>{bank_name}</b>\n"
        f"<code>{card_num}</code>\n\n"
        f"*обовʼязково кидайте квитанцію для підтвердження*"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(ShopStates.waiting_for_receipt)

# --- ПРИЙОМ КВИТАНЦІЇ ---
@dp.message(ShopStates.waiting_for_receipt, F.photo)
async def get_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    
    # Повідомлення користувачу
    await message.answer("✅ <b>Квитанція прийнята!</b>\nОчікуйте підтвердження адміністратором.", parse_mode="HTML")
    
    # Повідомлення адміну
    b = InlineKeyboardBuilder()
    b.button(text="✅ Підтвердити", callback_data=f"adm_ok_{user_id}_{data['buy_uah']}")
    b.button(text="❌ Відхилити", callback_data=f"adm_no_{user_id}")
    
    await bot.send_photo(
        ADMIN_ID, 
        message.photo[-1].file_id,
        caption=f"🔔 <b>Нова заявка!</b>\nЮзер: {user_id}\nСума: {data['buy_uah']} грн\nГолда: {data['gold']}g\nБанк: {data['bank']}",
        reply_markup=b.adjust(2).as_markup(),
        parse_mode="HTML"
    )
    await state.clear()

# --- ОБРОБКА АДМІНОМ ---
@dp.callback_query(F.data.startswith("adm_"))
async def admin_action(callback: types.CallbackQuery):
    action, _, user_id, *info = callback.data.split("_")
    user_id = int(user_id)
    
    if action == "ok":
        amount = float(info[0])
        # Нараховуємо в баланс (баланс у грн, бо покупка в грн)
        await users_col.update_one({"user_id": user_id}, {"$inc": {"balance_uah": amount, "total_bought": amount}})
        await bot.send_message(user_id, f"✅ Вашу оплату на {amount} грн підтверджено! Кошти зараховані на баланс.")
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ <b>ПІДТВЕРДЖЕНО</b>", parse_mode="HTML")
    else:
        await bot.send_message(user_id, "❌ Вашу заявку на оплату було відхилено адміністратором.")
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ <b>ВІДХИЛЕНО</b>", parse_mode="HTML")
    await callback.answer()

# --- ВИВЕДЕННЯ ГОЛДИ ---
@dp.message(ShopStates.waiting_for_withdraw_amount)
async def process_withdraw(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("⚠️ Введіть число!")
    gold = int(message.text)
    if gold < 100: return await message.answer("❌ Мінімальна кількість 100G!")
    
    await message.answer(MESSAGES['ua']['withdraw_next'].format(gold=gold, support=SUPPORT_LINK))
    
    # Сповіщення адміну про намір виводу
    await bot.send_message(ADMIN_ID, f"📤 <b>Запит на вивід!</b>\nЮзер: {message.from_user.id}\nКількість: {gold}G")
    await state.clear()

# --- КАЛЬКУЛЯТОР ---
@dp.callback_query(F.data.startswith("calc_"))
async def calc_call(c: types.CallbackQuery, state: FSMContext):
    if c.data == "calc_u_g":
        await c.message.answer("Введіть суму в гривнях ₴:")
        await state.set_state(ShopStates.calc_uah_to_gold)
    else:
        await c.message.answer("Введіть кількість голди G:")
        await state.set_state(ShopStates.calc_gold_to_uah)
    await c.answer()

@dp.message(ShopStates.calc_uah_to_gold)
async def res_u_g(m: types.Message, state: FSMContext):
    if m.text.isdigit():
        await m.answer(f"✅ {m.text}грн ≈ {round(int(m.text)/0.32, 2)}G")
    await state.clear()

@dp.message(ShopStates.calc_gold_to_uah)
async def res_g_u(m: types.Message, state: FSMContext):
    if m.text.isdigit():
        await m.answer(f"✅ {m.text}G ≈ {round(int(m.text)*0.32, 2)}грн")
    await state.clear()

# --- СТАРТ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if not user:
        await users_col.insert_one({
            "user_id": message.from_user.id, "lang": "ua", "balance_uah": 0.0, 
            "total_bought": 0.0, "reg_date": datetime.now().strftime("%d.%m.%Y")
        })
    await message.answer("Вітаємо у Yakuza Bot!", reply_markup=get_main_kb("ua"))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
