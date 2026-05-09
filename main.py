import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from motor.motor_asyncio import AsyncIOMotorClient

# Логування для відстеження помилок
logging.basicConfig(level=logging.INFO)

# --- НАЛАШТУВАННЯ ---
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
SUPPORT_LINK = "@YAKUZA_N3" 

# Отримуємо список адмінів зі змінної оточення
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

# Тексти кнопок
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

# --- ГОЛОВНИЙ ОБРОБНИК МЕНЮ ---
@dp.message(F.text.in_([B_BUY, B_SELL, B_PROFILE, B_SUPPORT, B_WITHDRAW, B_CALC]))
async def main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": message.from_user.id})
    if not user:
        user = {"user_id": message.from_user.id, "balance_uah": 0.0, "total_bought": 0.0, "reg_date": datetime.now().strftime("%d.%m.%Y")}
        await users_col.insert_one(user)

    txt = message.text

    if txt == B_PROFILE:
        text = (
            f"ℹ️ <b>Інформація про вас:</b>\n\n"
            f"🆔 <code>{user['user_id']}</code>\n"
            f"✨ <b>Баланс:</b> {user.get('balance_uah', 0.0)} грн\n\n"
            f"<b>Куплено всього:</b> {user.get('total_bought', 0.0)} грн\n"
            f"<b>Виведено всього:</b> {user.get('total_withdrawn', 0.0)} G\n"
            f"<b>Виводів:</b> {user.get('withdrawals_count', 0)}\n\n"
            f"<b>Запрошено друзів:</b> {user.get('friends_count', 0)}\n\n"
            f"🗓️ <b>Реєстрація:</b> {user.get('reg_date', '--')}"
        )
        await message.answer(text, parse_mode="HTML")

    elif txt == B_SUPPORT:
        await message.answer(f"🆘 Зв'язок з адміністратором: {SUPPORT_LINK}")

    elif txt == B_CALC:
        b = InlineKeyboardBuilder()
        b.button(text="₴ Гривні ➡️ Gold G", callback_data="calc_u_g")
        b.button(text="Gold G ➡️ ₴ Гривні", callback_data="calc_g_u")
        await message.answer("❗️<b>Курс: 0.32грн за 1G</b>", reply_markup=b.adjust(1).as_markup(), parse_mode="HTML")

    elif txt == B_BUY:
        await message.answer("Price💰:\n100 голди - 32грн\n\n✍️ <b>Введіть сумму в грн</b>", parse_mode="HTML")
        await state.set_state(ShopStates.waiting_for_buy_amount)

    elif txt == B_WITHDRAW:
        await message.answer("Ви бажаєте вивести голду.\nМінімальна кількість 100G.\nВведіть кількість:")
        await state.set_state(ShopStates.waiting_for_withdraw_amount)

    elif txt == B_SELL:
        await message.answer(f"Для продажу голди пишіть: {SUPPORT_LINK}")

# --- КУПІВЛЯ ТА КВИТАНЦІЇ ---
@dp.message(ShopStates.waiting_for_buy_amount)
async def buy_input(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return
    uah = int(message.text)
    if uah < 32: return await message.answer("❌ Мінімум 32 грн!")
    await state.update_data(buy_uah=uah)
    b = InlineKeyboardBuilder()
    b.button(text="💳 Монобанк", callback_data="pay_mono")
    b.button(text="💳 Абанк", callback_data="pay_abank")
    await message.answer("Оберіть банк:", reply_markup=b.adjust(1).as_markup())

@dp.callback_query(F.data.startswith("pay_"))
async def pay_choice(callback: types.CallbackQuery, state: FSMContext):
    bank = callback.data.split("_")[1]
    data = await state.get_data()
    uah = data['buy_uah']
    card = CARDS['monobank'] if bank == "mono" else CARDS['abank']
    bank_name = "Monobank" if bank == "mono" else "Абанк"
    
    await state.update_data(bank=bank_name, gold=round(uah/0.32, 2))
    await callback.message.edit_text(
        f"<b>Заявка на покупку Голди💰</b>\n\nДо сплати: <b>{uah} грн</b>\nБанк: <b>{bank_name}</b>\n"
        f"<code>{card}</code>\n\n<b>*обовʼязково кидайте фото квитанції*</b>", parse_mode="HTML"
    )
    await state.set_state(ShopStates.waiting_for_receipt)

@dp.message(ShopStates.waiting_for_receipt, F.photo)
async def receipt_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await message.answer("✅ Квитанція відправлена на перевірку!")
    
    b = InlineKeyboardBuilder()
    b.button(text="✅ Підтвердити", callback_data=f"adm_ok_{message.from_user.id}_{data['buy_uah']}")
    b.button(text="❌ Відхилити", callback_data=f"adm_no_{message.from_user.id}")
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(admin_id, message.photo[-1].file_id, 
                                 caption=f"💰 Оплата: {data['buy_uah']} грн\nЮзер: {message.from_user.id}", 
                                 reply_markup=b.as_markup())
        except: pass
    await state.clear()

# --- ВИВЕДЕННЯ ---
@dp.message(ShopStates.waiting_for_withdraw_amount)
async def withdraw_input(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return
    gold = int(message.text)
    if gold < 100: return await message.answer("Мінімум 100G!")
    await message.answer(f"Кількість: {gold}G\nНапишіть {SUPPORT_LINK} для виводу.")
    
    for admin_id in ADMIN_IDS:
        try: await bot.send_message(admin_id, f"📤 Запит на вивід: {gold}G від {message.from_user.id}")
        except: pass
    await state.clear()

# --- КАЛЬКУЛЯТОР ---
@dp.callback_query(F.data.startswith("calc_"))
async def calc_process(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Введіть кількість:")
    await state.set_state(ShopStates.calc_uah_to_gold if c.data == "calc_u_g" else ShopStates.calc_gold_to_uah)
    await c.answer()

@dp.message(ShopStates.calc_uah_to_gold)
async def c1(m: types.Message, state: FSMContext):
    if m.text.isdigit(): await m.answer(f"✅ {m.text}грн ≈ {round(int(m.text)/0.32, 2)}G")
    await state.clear()

@dp.message(ShopStates.calc_gold_to_uah)
async def c2(m: types.Message, state: FSMContext):
    if m.text.isdigit(): await m.answer(f"✅ {m.text}G ≈ {round(int(m.text)*0.32, 2)}грн")
    await state.clear()

# --- АДМІН-ДІЇ ---
@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(c: types.CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return await c.answer("Ви не адмін!", show_alert=True)
    
    act, _, uid, *info = c.data.split("_")
    uid = int(uid)
    if act == "ok":
        amount = float(info[0])
        await users_col.update_one({"user_id": uid}, {"$inc": {"balance_uah": amount, "total_bought": amount}})
        await bot.send_message(uid, f"✅ Оплата {amount} грн підтверджена! Баланс поповнено.")
        await c.message.edit_caption(caption=c.message.caption + "\n\n✅ СХВАЛЕНО")
    else:
        await bot.send_message(uid, "❌ Оплата відхилена.")
        await c.message.edit_caption(caption=c.message.caption + "\n\n❌ ВІДХИЛЕНО")
    await c.answer()

@dp.message(Command("start"))
async def cmd_start(m: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": m.from_user.id})
    if not user:
        await users_col.insert_one({"user_id": m.from_user.id, "balance_uah": 0.0, "total_bought": 0.0, "reg_date": datetime.now().strftime("%d.%m.%Y")})
    await m.answer("🏠 Головне меню", reply_markup=get_main_kb())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
