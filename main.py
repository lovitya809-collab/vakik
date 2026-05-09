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

# Логування
logging.basicConfig(level=logging.INFO)

# --- НАЛАШТУВАННЯ ---
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
SUPPORT_LINK = "@YAKUZA_N3" 

# Список адмінів (ID через кому в Railway)
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

# --- ГОЛОВНЕ МЕНЮ ---
@dp.message(F.text.in_([B_BUY, B_SELL, B_PROFILE, B_SUPPORT, B_WITHDRAW, B_CALC]))
async def main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": message.from_user.id})
    if not user:
        user = {
            "user_id": message.from_user.id, 
            "balance_gold": 0.0, 
            "total_bought_uah": 0.0, 
            "total_withdrawn_gold": 0.0,
            "reg_date": datetime.now().strftime("%d.%m.%Y")
        }
        await users_col.insert_one(user)

    txt = message.text
    if txt == B_PROFILE:
        text = (
            f"👤 <b>Ваш профіль YAKUZA:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{user['user_id']}</code>\n"
            f"💰 <b>Баланс:</b> <code>{user.get('balance_gold', 0.0)} G</code>\n"
            f"📊 <b>Всього поповнено:</b> <code>{user.get('total_bought_uah', 0.0)} грн</code>\n"
            f"📤 <b>Всього виведено:</b> <code>{user.get('total_withdrawn_gold', 0.0)} G</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🗓 <b>Дата реєстрації:</b> {user.get('reg_date', '--')}"
        )
        await message.answer(text, parse_mode="HTML")
        
    elif txt == B_SUPPORT:
        await message.answer(f"🆘 Зв'язок з адміністратором: {SUPPORT_LINK}")
        
    elif txt == B_BUY:
        await message.answer("Price💰:\n100 голди - 32грн\n\n✍️ <b>Введіть сумму в грн, яку хочете оплатити:</b>", parse_mode="HTML")
        await state.set_state(ShopStates.waiting_for_buy_amount)
        
    elif txt == B_WITHDRAW:
        await message.answer("Ви бажаєте вивести голду.\nБудь ласка, напишіть кількість голди для виведення.\nМінімальна кількість 100G")
        await state.set_state(ShopStates.waiting_for_withdraw_amount)
        
    elif txt == B_CALC:
        b = InlineKeyboardBuilder()
        b.button(text="₴ Грн ➡️ Gold G", callback_data="calc_u_g")
        b.button(text="Gold G ➡️ ₴ Грн", callback_data="calc_g_u")
        await message.answer("🧮 <b>Калькулятор курсу: 0.32</b>", reply_markup=b.adjust(1).as_markup(), parse_mode="HTML")
        
    elif txt == B_SELL:
        await message.answer(f"Для продажу голди пишіть: {SUPPORT_LINK}")

# --- КУПІВЛЯ ---
@dp.message(ShopStates.waiting_for_buy_amount)
async def buy_input(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return
    uah = int(message.text)
    if uah < 32: return await message.answer("❌ Мінімальна сума поповнення — 32 грн!")
    gold = round(uah / 0.32, 2)
    await state.update_data(buy_uah=uah, buy_gold=gold)
    
    b = InlineKeyboardBuilder()
    b.button(text="💳 Монобанк", callback_data="pay_mono")
    b.button(text="💳 Абанк", callback_data="pay_abank")
    await message.answer(f"Заявка на <b>{gold} G</b>\nДо сплати: <b>{uah} грн</b>\n\nОберіть банк:", reply_markup=b.adjust(1).as_markup(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("pay_"))
async def pay_choice(callback: types.CallbackQuery, state: FSMContext):
    bank = callback.data.split("_")[1]
    data = await state.get_data()
    card = CARDS['monobank'] if bank == "mono" else CARDS['abank']
    bank_name = "Monobank" if bank == "mono" else "Абанк"
    
    await state.update_data(bank_name=bank_name)
    await callback.message.edit_text(
        f"<b>Заявка на покупку Голди💰</b>\n\n"
        f"До сплати: <b>{data['buy_uah']} грн</b>\n"
        f"Отримаєте: <b>{data['buy_gold']} G</b>\n\n"
        f"Банк: <b>{bank_name}</b>\n"
        f"Карта: <code>{card}</code>\n\n"
        f"<b>*Обовʼязково надішліть фото квитанції!*</b>", parse_mode="HTML"
    )
    await state.set_state(ShopStates.waiting_for_receipt)

@dp.message(ShopStates.waiting_for_receipt, F.photo)
async def receipt_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await message.answer("✅ Квитанція прийнята, очікуйте підтвердження адміністратором.")
    
    b = InlineKeyboardBuilder()
    b.button(text="✅ Підтвердити", callback_data=f"adm_ok_{message.from_user.id}_{data['buy_uah']}_{data['buy_gold']}")
    b.button(text="❌ Відхилити", callback_data=f"adm_no_{message.from_user.id}")
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id, 
                message.photo[-1].file_id, 
                caption=f"🔔 <b>Нова покупка!</b>\nЮзер: <code>{message.from_user.id}</code>\nСума: <b>{data['buy_uah']} грн</b>\nГолда до зарахування: <b>{data['buy_gold']} G</b>\nБанк: {data.get('bank_name')}",
                reply_markup=b.as_markup(),
                parse_mode="HTML"
            )
        except: pass
    await state.clear()

# --- АДМІН-ДІЇ (НАРАХУВАННЯ ГОЛДИ) ---
@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(c: types.CallbackQuery):
    if c.from_user.id not in ADMIN_IDS:
        return await c.answer("Ви не адмін!", show_alert=True)
    
    data = c.data.split("_")
    action = data[1]
    user_id = int(data[2])
    
    if action == "ok":
        amount_uah = float(data[3])
        amount_gold = float(data[4])
        
        # Нараховуємо саме ГОЛДУ та записуємо статистику в грн
        await users_col.update_one(
            {"user_id": user_id}, 
            {
                "$inc": {
                    "balance_gold": amount_gold, 
                    "total_bought_uah": amount_uah
                }
            }
        )
        try:
            await bot.send_message(user_id, f"✅ Ваша оплата підтверджена!\nНа баланс зараховано: <b>{amount_gold} G</b>", parse_mode="HTML")
        except: pass
        await c.message.edit_caption(caption=c.message.caption + "\n\n✅ <b>ЗАРАХОВАНО</b>", parse_mode="HTML")
    else:
        try:
            await bot.send_message(user_id, "❌ Ваша квитанція була відхилена адміністратором.")
        except: pass
        await c.message.edit_caption(caption=c.message.caption + "\n\n❌ <b>ВІДХИЛЕНО</b>", parse_mode="HTML")
    
    await c.answer()

# --- ВИВЕДЕННЯ ---
@dp.message(ShopStates.waiting_for_withdraw_amount)
async def withdraw_process(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return
    gold = int(message.text)
    if gold < 100: return await message.answer("❌ Мінімальна кількість 100G!")
    
    await message.answer(f"Кількість голди для виведення: {gold}G\nНапишіть {SUPPORT_LINK} для подальшої інструкції для виведення!")
    
    for admin_id in ADMIN_IDS:
        try: await bot.send_message(admin_id, f"📤 <b>Запит на вивід!</b>\nЮзер: <code>{message.from_user.id}</code>\nКількість: <b>{gold} G</b>", parse_mode="HTML")
        except: pass
    await state.clear()

# --- КАЛЬКУЛЯТОР ---
@dp.callback_query(F.data.startswith("calc_"))
async def calc_process(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Введіть число для підрахунку:")
    await state.set_state(ShopStates.calc_uah_to_gold if c.data == "calc_u_g" else ShopStates.calc_gold_to_uah)
    await c.answer()

@dp.message(ShopStates.calc_uah_to_gold)
async def c1(m: types.Message, state: FSMContext):
    if m.text.isdigit(): await m.answer(f"✅ {m.text} грн ≈ <b>{round(int(m.text)/0.32, 2)} G</b>", parse_mode="HTML")
    await state.clear()

@dp.message(ShopStates.calc_gold_to_uah)
async def c2(m: types.Message, state: FSMContext):
    if m.text.isdigit(): await m.answer(f"✅ {m.text} G ≈ <b>{round(int(m.text)*0.32, 2)} грн</b>", parse_mode="HTML")
    await state.clear()

@dp.message(Command("start"))
async def cmd_start(m: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": m.from_user.id})
    if not user:
        await users_col.insert_one({
            "user_id": m.from_user.id, 
            "balance_gold": 0.0, 
            "total_bought_uah": 0.0, 
            "total_withdrawn_gold": 0.0,
            "reg_date": datetime.now().strftime("%d.%m.%Y")
        })
    await m.answer("👋 Ласкаво просимо до <b>YAKUZA BOT</b>!", reply_markup=get_main_kb(), parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
