import os
import asyncio
import logging
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)

# --- НАЛАШТУВАННЯ ---
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
SUPPORT_LINK = "@YAKUZA_N3" 
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]

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

B_BUY = '💰 Купити Голду'
B_SELL = '📥 Продати Голду'
B_PROFILE = '👤 Профіль'
B_SUPPORT = '🆘 Підтримка'
B_WITHDRAW = '📤 Вивести Голду'
B_CALC = '🧮 Підрахунок'

def get_main_kb():
    b = ReplyKeyboardBuilder()
    b.row(types.KeyboardButton(text=B_BUY), types.KeyboardButton(text=B_SELL))
    b.row(types.KeyboardButton(text=B_WITHDRAW), types.KeyboardButton(text=B_CALC))
    b.row(types.KeyboardButton(text=B_PROFILE), types.KeyboardButton(text=B_SUPPORT))
    return b.as_markup(resize_keyboard=True)

# --- ПРОФІЛЬ ТА МЕНЮ ---
@dp.message(F.text.in_([B_BUY, B_SELL, B_PROFILE, B_SUPPORT, B_WITHDRAW, B_CALC]))
async def main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": message.from_user.id})
    if not user:
        user = {"user_id": message.from_user.id, "balance_gold": 0.0, "total_bought_uah": 0.0, "total_withdrawn_gold": 0.0, "reg_date": datetime.now().strftime("%d.%m.%Y")}
        await users_col.insert_one(user)

    txt = message.text
    if txt == B_PROFILE:
        text = (
            f"👤 <b>Ваш профіль YAKUZA:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{user['user_id']}</code>\n"
            f"💰 <b>Баланс:</b> <code>{user.get('balance_gold', 0.0)} G</code>\n"
            f"📊 <b>Всього поповнено:</b> {user.get('total_bought_uah', 0.0)} грн\n"
            f"📤 <b>Всього виведено:</b> {user.get('total_withdrawn_gold', 0.0)} G\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🗓 <b>Реєстрація:</b> {user.get('reg_date', '--')}"
        )
        await message.answer(text, parse_mode="HTML")
    elif txt == B_WITHDRAW:
        await message.answer("Ви бажаєте вивести голду.\nБудь ласка, напишіть кількість голди для виведення.\nМінімальна кількість 100G")
        await state.set_state(ShopStates.waiting_for_withdraw_amount)
    elif txt == B_BUY:
        await message.answer("✍️ <b>Введіть сумму в грн для поповнення:</b>", parse_mode="HTML")
        await state.set_state(ShopStates.waiting_for_buy_amount)
    elif txt == B_SUPPORT:
        await message.answer(f"🆘 Підтримка: {SUPPORT_LINK}")
    elif txt == B_CALC:
        b = InlineKeyboardBuilder()
        b.button(text="₴ Грн ➡️ Gold G", callback_data="calc_u_g")
        b.button(text="Gold G ➡️ ₴ Грн", callback_data="calc_g_u")
        await message.answer("🧮 Калькулятор курсу 0.32", reply_markup=b.adjust(1).as_markup())
    elif txt == B_SELL:
        await message.answer(f"Продати голду: {SUPPORT_LINK}")

# --- ВИВЕДЕННЯ (НОВА ЛОГІКА) ---
@dp.message(ShopStates.waiting_for_withdraw_amount)
async def withdraw_request(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("⚠️ Введіть число!")
    amount = int(message.text)
    if amount < 100: return await message.answer("❌ Мінімальний вивід — 100 G!")
    
    user = await users_col.find_one({"user_id": message.from_user.id})
    if user.get('balance_gold', 0) < amount:
        return await message.answer(f"❌ Недостатньо голди! Ваш баланс: {user.get('balance_gold', 0)} G")

    # Списуємо голду відразу (резервуємо)
    await users_col.update_one({"user_id": message.from_user.id}, {"$inc": {"balance_gold": -amount}})
    
    order_id = random.randint(1000, 9999)
    nickname = message.from_user.username if message.from_user.username else message.from_user.full_name
    
    # Повідомлення гравцю
    await message.answer(f"Заявка #{order_id} на виведення {amount}G прийнята!\nНапишіть {SUPPORT_LINK} для отримання.")

    # Повідомлення адмінам
    b = InlineKeyboardBuilder()
    b.button(text="✅ Виконано", callback_data=f"wd_ok_{message.from_user.id}_{amount}_{order_id}")
    b.button(text="❌ Відмінити", callback_data=f"wd_no_{message.from_user.id}_{amount}_{order_id}")
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id, 
                f"📤 <b>Заявка на вивід #{order_id}</b>\n\n"
                f"👤 <b>Нік:</b> @{nickname}\n"
                f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
                f"💰 <b>Кількість:</b> <b>{amount} G</b>",
                reply_markup=b.as_markup(),
                parse_mode="HTML"
            )
        except: pass
    await state.clear()

# --- ОБРОБКА КНОПОК ВИВОДУ АДМІНОМ ---
@dp.callback_query(F.data.startswith("wd_"))
async def admin_withdraw_decision(c: types.CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    
    data = c.data.split("_")
    action = data[1]
    u_id = int(data[2])
    amt = float(data[3])
    ord_id = data[4]

    if action == "ok":
        # Просто додаємо в статистику виведеного
        await users_col.update_one({"user_id": u_id}, {"$inc": {"total_withdrawn_gold": amt}})
        await bot.send_message(u_id, f"✅ Ваша заявка #{ord_id} на вивід {amt} G схвалена!")
        await c.message.edit_text(f"✅ Заявка #{ord_id} ВИКОНАНА (Гравцю @{c.message.chat.username})")
    else:
        # Повертаємо голду гравцю
        await users_col.update_one({"user_id": u_id}, {"$inc": {"balance_gold": amt}})
        await bot.send_message(u_id, f"❌ Ваша заявка #{ord_id} на вивід {amt} G відхилена. Голда повернута на баланс.")
        await c.message.edit_text(f"❌ Заявка #{ord_id} ВІДХИЛЕНА (Голда повернута)")
    await c.answer()

# --- КУПІВЛЯ ТА АДМІН-ОК ---
@dp.message(ShopStates.waiting_for_buy_amount)
async def buy_input(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return
    uah = int(message.text)
    if uah < 32: return await message.answer("Мінімум 32 грн!")
    gold = round(uah / 0.32, 2)
    await state.update_data(buy_uah=uah, buy_gold=gold)
    b = InlineKeyboardBuilder()
    b.button(text="💳 Моно", callback_data="pay_mono")
    b.button(text="💳 Абанк", callback_data="pay_abank")
    await message.answer(f"Сума: {uah} грн ({gold} G)\nОберіть банк:", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("pay_"))
async def pay_choice(c: types.CallbackQuery, state: FSMContext):
    bank = c.data.split("_")[1]
    data = await state.get_data()
    card = CARDS['monobank'] if bank == "mono" else CARDS['abank']
    await c.message.edit_text(f"До сплати: {data['buy_uah']} грн\nКарта: <code>{card}</code>\nЧекаємо фото квитанції.", parse_mode="HTML")
    await state.set_state(ShopStates.waiting_for_receipt)

@dp.message(ShopStates.waiting_for_receipt, F.photo)
async def receipt_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await message.answer("✅ Квитанція на перевірці!")
    b = InlineKeyboardBuilder()
    b.button(text="✅ Схвалити", callback_data=f"adm_ok_{message.from_user.id}_{data['buy_uah']}_{data['buy_gold']}")
    b.button(text="❌ Відхилити", callback_data=f"adm_no_{message.from_user.id}")
    for a_id in ADMIN_IDS:
        try: await bot.send_photo(a_id, message.photo[-1].file_id, caption=f"Покупка: {data['buy_uah']} грн ({data['buy_gold']}G)\nЮзер: {message.from_user.id}", reply_markup=b.as_markup())
        except: pass
    await state.clear()

@dp.callback_query(F.data.startswith("adm_"))
async def admin_buy_decision(c: types.CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    d = c.data.split("_")
    u_id = int(d[2])
    if d[1] == "ok":
        uah, gold = float(d[3]), float(d[4])
        await users_col.update_one({"user_id": u_id}, {"$inc": {"balance_gold": gold, "total_bought_uah": uah}})
        await bot.send_message(u_id, f"✅ Зараховано {gold} G!")
        await c.message.edit_caption(caption="✅ ПІДТВЕРДЖЕНО")
    else:
        await bot.send_message(u_id, "❌ Відхилено.")
        await c.message.edit_caption(caption="❌ ВІДХИЛЕНО")
    await c.answer()

# --- СТАРТ ТА КАЛЬКУЛЯТОР ---
@dp.callback_query(F.data.startswith("calc_"))
async def calc(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Введіть число:")
    await state.set_state(ShopStates.calc_uah_to_gold if c.data == "calc_u_g" else ShopStates.calc_gold_to_uah)
    await c.answer()

@dp.message(ShopStates.calc_uah_to_gold)
async def c1(m: types.Message, state: FSMContext):
    if m.text.isdigit(): await m.answer(f"✅ {m.text} грн ≈ {round(int(m.text)/0.32, 2)} G")
    await state.clear()

@dp.message(ShopStates.calc_gold_to_uah)
async def c2(m: types.Message, state: FSMContext):
    if m.text.isdigit(): await m.answer(f"✅ {m.text} G ≈ {round(int(m.text)*0.32, 2)} грн")
    await state.clear()

@dp.message(Command("start"))
async def cmd_start(m: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": m.from_user.id})
    if not user:
        await users_col.insert_one({"user_id": m.from_user.id, "balance_gold": 0.0, "total_bought_uah": 0.0, "total_withdrawn_gold": 0.0, "reg_date": datetime.now().strftime("%d.%m.%Y")})
    await m.answer("🏠 Головне меню", reply_markup=get_main_kb())

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
