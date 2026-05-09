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
ADMIN_ID = int(os.getenv("ADMIN_ID"))
SUPPORT_LINK = "@YAKUZA_N3" 

# Реквізити
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
        'profile_text': (
            "ℹ️ <b>Інформація про вас:</b>\n\n"
            "🆔 <code>{id}</code>\n"
            "✨ <b>Баланс:</b> {balance} грн\n\n"
            "<b>Куплено всього:</b> {bought} грн\n"
            "<b>Виведено всього:</b> {withdrawn} G\n"
            "<b>Виводів:</b> {w_count}\n\n"
            "<b>Запрошено друзів:</b> {friends}\n\n"
            "🗓️ <b>Реєстрація:</b> {reg_date}"
        ),
        'calc_main': (
            "❗️<b>Курс: 0.32грн за 1G</b>\n\n"
            "100g — 32грн\n"
            "500g — 160грн\n"
            "1000g — 320грн\n\n"
            "Оберіть, що саме хочете порахувати: 👇"
        )
    }
}

# --- КЛАВІАТУРИ ---
def get_main_kb():
    b = ReplyKeyboardBuilder()
    b.row(types.KeyboardButton(text=MESSAGES['ua']['buy']), types.KeyboardButton(text=MESSAGES['ua']['sell']))
    b.row(types.KeyboardButton(text=MESSAGES['ua']['withdraw']), types.KeyboardButton(text=MESSAGES['ua']['calc']))
    b.row(types.KeyboardButton(text=MESSAGES['ua']['profile']), types.KeyboardButton(text=MESSAGES['ua']['support']))
    return b.as_markup(resize_keyboard=True)

# --- ГОЛОВНЕ МЕНЮ ---
@dp.message(F.text.in_([MESSAGES['ua'][k] for k in ['profile', 'support', 'withdraw', 'calc', 'buy', 'sell']]))
async def menu_router(message: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": message.from_user.id})
    txt = message.text

    if txt == MESSAGES['ua']['profile']:
        text = MESSAGES['ua']['profile_text'].format(
            id=user['user_id'], 
            balance=user.get('balance_uah', 0.0),
            bought=user.get('total_bought', 0.0), 
            withdrawn=user.get('total_withdrawn', 0.0),
            w_count=user.get('withdrawals_count', 0), 
            friends=user.get('friends_count', 0), 
            reg_date=user.get('reg_date', '--')
        )
        await message.answer(text, parse_mode="HTML")
        
    elif txt == MESSAGES['ua']['support']:
        await message.answer(f"🆘 Зв'язок з адміністратором: {SUPPORT_LINK}")
        
    elif txt == MESSAGES['ua']['calc']:
        b = InlineKeyboardBuilder()
        b.button(text="₴ Гривні ➡️ Gold G", callback_data="calc_u_g")
        b.button(text="Gold G ➡️ ₴ Гривні", callback_data="calc_g_u")
        await message.answer(MESSAGES['ua']['calc_main'], reply_markup=b.adjust(1).as_markup(), parse_mode="HTML")
        
    elif txt == MESSAGES['ua']['buy']:
        await message.answer(MESSAGES['ua']['buy_title'], parse_mode="HTML")
        await state.set_state(ShopStates.waiting_for_buy_amount)
        
    elif txt == MESSAGES['ua']['withdraw']:
        await message.answer("Ви бажаєте вивести голду.\nБудь ласка, напишіть кількість голди.\nМінімальна кількість 100G")
        await state.set_state(ShopStates.waiting_for_withdraw_amount)

# --- КУПІВЛЯ (КАРТА) ---
@dp.message(ShopStates.waiting_for_buy_amount)
async def process_buy_amt(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("⚠️ Введіть число!")
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
        f"<b>*обовʼязково кидайте квитанцію для підтвердження*</b>"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(ShopStates.waiting_for_receipt)

@dp.message(ShopStates.waiting_for_receipt, F.photo)
async def get_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    await message.answer("✅ <b>Квитанція прийнята!</b>\nОчікуйте підтвердження адміністратором.", parse_mode="HTML")
    
    b = InlineKeyboardBuilder()
    b.button(text="✅ Підтвердити", callback_data=f"adm_ok_{user_id}_{data['buy_uah']}")
    b.button(text="❌ Відхилити", callback_data=f"adm_no_{user_id}")
    
    await bot.send_photo(
        ADMIN_ID, message.photo[-1].file_id,
        caption=f"🔔 <b>Нова оплата!</b>\nЮзер: {user_id}\nСума: {data['buy_uah']} грн\nГолда: {data['gold']}g\nБанк: {data['bank']}",
        reply_markup=b.adjust(2).as_markup(), parse_mode="HTML"
    )
    await state.clear()

@dp.callback_query(F.data.startswith("adm_"))
async def admin_action(callback: types.CallbackQuery):
    act, _, user_id, *info = callback.data.split("_")
    user_id = int(user_id)
    if act == "ok":
        amt = float(info[0])
        await users_col.update_one({"user_id": user_id}, {"$inc": {"balance_uah": amt, "total_bought": amt}})
        await bot.send_message(user_id, f"✅ Оплата {amt} грн підтверджена! Баланс оновлено.")
    else:
        await bot.send_message(user_id, "❌ Вашу квитанцію було відхилено.")
    await callback.message.delete()
    await callback.answer("Готово!")

# --- ВИВЕДЕННЯ ---
@dp.message(ShopStates.waiting_for_withdraw_amount)
async def process_withdraw(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("⚠️ Число!")
    gold = int(message.text)
    if gold < 100: return await message.answer("❌ Мінімальна кількість 100G!")
    
    await message.answer(f"Кількість голди для виведення: {gold}G\nНапишіть {SUPPORT_LINK} для подальшої інструкції для виведення!")
    await bot.send_message(ADMIN_ID, f"📤 <b>Запит на вивід!</b>\nЮзер: <code>{message.from_user.id}</code>\nКількість: {gold}G")
    await state.clear()

# --- КАЛЬКУЛЯТОР ---
@dp.callback_query(F.data.startswith("calc_"))
async def calc_call(c: types.CallbackQuery, state: FSMContext):
    if c.data == "calc_u_g":
        await c.message.answer("✍️ Введіть суму в <b>гривнях ₴</b>:", parse_mode="HTML")
        await state.set_state(ShopStates.calc_uah_to_gold)
    else:
        await c.message.answer("✍️ Введіть кількість <b>голди G</b>:", parse_mode="HTML")
        await state.set_state(ShopStates.calc_gold_to_uah)
    await c.answer()

@dp.message(ShopStates.calc_uah_to_gold)
async def res_u_g(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return
    uah = int(m.text)
    gold = round(uah / 0.32, 2)
    await m.answer(f"✅ Результат підрахунку:\n<b>{uah} грн</b> ≈ <b>{gold} G</b>", parse_mode="HTML")
    await state.clear()

@dp.message(ShopStates.calc_gold_to_uah)
async def res_g_u(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return
    gold = int(m.text)
    uah = round(gold * 0.32, 2)
    await m.answer(f"✅ Результат підрахунку:\n<b>{gold} G</b> ≈ <b>{uah} грн</b>", parse_mode="HTML")
    await state.clear()

# --- СТАРТ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if not user:
        await users_col.insert_one({
            "user_id": message.from_user.id, "balance_uah": 0.0, "total_bought": 0.0, 
            "total_withdrawn": 0.0, "withdrawals_count": 0, "friends_count": 0,
            "reg_date": datetime.now().strftime("%d.%m.%Y")
        })
    await message.answer("👋 Ласкаво просимо до <b>Yakuza Bot</b>!", reply_markup=get_main_kb(), parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
