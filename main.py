import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from motor.motor_asyncio import AsyncIOMotorClient

# --- НАЛАШТУВАННЯ ---
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
ADMIN_ID = os.getenv("ADMIN_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Підключення до БД
cluster = AsyncIOMotorClient(MONGO_URL)
db = cluster["standoff_bot"]
users_col = db["users"]

# Стани для купівлі
class BuyGold(StatesGroup):
    waiting_for_amount = State()

# --- ТЕКСТИ ---
MESSAGES = {
    'ua': {
        'buy_title': "Price💰:\n100 голди - 32грн\n\n✍️Введіть сумму в грн, на яку хочете поповнити",
        'payment_confirm': "✅Супер\n💴До оплати: {uah}грн\n🫰🏻Получиш: {gold}g\n\nВиберіть спосіб оплати:",
        'card': "💳 Карта",
        'crypto': "💎 Crypto Bot",
        # ... (інші тексти з минулих кроків залишаються)
    }
}
# Додай аналогічні ключі для 'ru' та 'en' у свій словник MESSAGES

# --- КЛАВІАТУРИ ---

def get_payment_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Карта", callback_data="pay_card")
    builder.button(text="💎 Crypto Bot", callback_data="pay_crypto")
    builder.adjust(1)
    return builder.as_markup()

# --- ХЕНДЛЕРИ КУПІВЛІ ---

# 1. Натискання на кнопку "Купити Голду"
@dp.message(F.text.in_(["💰 Купити Голду", "💰 Купить Голду", "💰 Buy Gold"]))
async def start_buy_gold(message: types.Message, state: FSMContext):
    await message.answer(MESSAGES['ua']['buy_title']) # Можна додати вибір мови з БД
    await state.set_state(BuyGold.waiting_for_amount)

# 2. Обробка введеної суми
@dp.message(BuyGold.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Будь ласка, введіть число (суму в грн).")
        return

    amount_uah = int(message.text)
    # Розрахунок голди: (сума / 32) * 100
    gold_to_receive = round((amount_uah / 32) * 100, 2)

    await state.update_data(amount=amount_uah, gold=gold_to_receive)
    
    text = MESSAGES['ua']['payment_confirm'].format(uah=amount_uah, gold=gold_to_receive)
    await message.answer(text, reply_markup=get_payment_keyboard())
    await state.clear() # Очищуємо стан, але дані можна було б зберегти для оплати

# --- ОБРОБКА КНОПОК ОПЛАТИ ---

@dp.callback_query(F.data == "pay_card")
async def pay_card(callback: types.CallbackQuery):
    # Тут зазвичай видаються реквізити карти адміна
    await callback.message.answer("Реквізити для оплати на карту:\n`4444 5555 6666 7777`\nПісля оплати надішліть чек підтримці.", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "pay_crypto")
async def pay_crypto(callback: types.CallbackQuery):
    await callback.message.answer("Оплата через Crypto Bot тимчасово недоступна. Скористайтеся картою.")
    await callback.answer()

# (Решта хендлерів: start, profile, тощо залишаються з минулого коду)

async def main():
    print("Бот запущений. Очікування оплати...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
