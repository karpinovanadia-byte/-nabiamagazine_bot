import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Твой токен от @BotFather
TOKEN = "ТВОЙ_TELEGRAM_BOT_TOKEN"

# Твой числовой Telegram ID для получения заказов
SELLER_CHAT_ID = 123456789

# Реквизиты твоей банковской карты
CARD_NUMBER = "4441 **** **** 1234"
CARD_HOLDER = "ИМЯ ФАМИЛИЯ"

# База данных товаров с фотографиями (ссылки на картинки)
CATALOG = {
    "cat_3d": {
        "title": "🖨 Изделия (3D-печать)",
        "items": {
            "item_1": {
                "name": "Ваза дизайнерская",
                "price": "350 грн",
                "photo": "https://picsum.photos/seed/vase3d/400/300",
            },
            "item_2": {
                "name": "Подставка для телефона",
                "price": "150 грн",
                "photo": "https://picsum.photos/seed/stand3d/400/300",
            },
        },
    },
    "cat_china": {
        "title": "📦 Товары из Китая",
        "items": {
            "item_3": {
                "name": "Светодиодная лента (5м)",
                "price": "280 грн",
                "photo": "https://picsum.photos/seed/ledstrip/400/300",
            },
            "item_4": {
                "name": "Беспроводной брелок",
                "price": "200 грн",
                "photo": "https://picsum.photos/seed/keychain/400/300",
            },
        },
    },
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()


# Состояния для оформления заказа
class OrderState(StatesGroup):
  waiting_for_name = State()
  waiting_for_phone = State()
  waiting_for_confirmation = State()


# 1. Главное меню — показ категорий
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
  keyboard_buttons = []
  for cat_key, cat_data in CATALOG.items():
    keyboard_buttons.append(
        [types.InlineKeyboardButton(text=cat_data["title"], callback_data=cat_key)]
    )

  keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
  await message.answer(
      "Привет! Добро пожаловать в наш магазин. Выбери категорию товаров:",
      reply_markup=keyboard,
  )


# 2. Показ товаров выбранной категории
@dp.callback_query(F.data.startswith("cat_"))
async def show_category_items(callback: types.CallbackQuery):
  cat_key = callback.data
  category = CATALOG.get(cat_key)

  if not category:
    await callback.answer("Категория не найдена.")
    return

  keyboard_buttons = []
  for item_key, item_data in category["items"].items():
    button_text = f"👁 {item_data['name']} — {item_data['price']}"
    keyboard_buttons.append([
        types.InlineKeyboardButton(
            text=button_text, callback_data=f"show_{item_key}"
        )
    ])

  keyboard_buttons.append(
      [types.InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="back_to_menu")]
  )

  keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
  await callback.message.edit_text(
      f"Выбрано: **{category['title']}**\nНажмите на товар, чтобы посмотреть фото и описание:",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer()


# Возврат в главное меню
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
  keyboard_buttons = []
  for cat_key, cat_data in CATALOG.items():
    keyboard_buttons.append(
        [types.InlineKeyboardButton(text=cat_data["title"], callback_data=cat_key)]
    )

  keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
  await callback.message.edit_text(
      "Выбери категорию товаров:", reply_markup=keyboard
  )
  await callback.answer()


# 3. Показ карточки товара с фото и кнопкой купить
@dp.callback_query(F.data.startswith("show_"))
async def show_item_card(callback: types.CallbackQuery):
  item_key = callback.data.replace("show_", "")

  selected_item = None
  for cat_data in CATALOG.values():
    if item_key in cat_data["items"]:
      selected_item = cat_data["items"][item_key]
      break

  if not selected_item:
    await callback.answer("Товар не найден.")
    return

  keyboard = types.InlineKeyboardMarkup(
      inline_keyboard=[
          [
              types.InlineKeyboardButton(
                  text=f"🛒 Купить за {selected_item['price']}",
                  callback_data=f"buy_{item_key}",
              )
          ],
          [types.InlineKeyboardButton(text="⬅️ К списку товаров", callback_data="cat_3d")],  # Можно настроить возврат
      ]
  )

  # Отправляем фото с описанием
  await callback.message.answer_photo(
      photo=selected_item["photo"],
      caption=f"📦 **{selected_item['name']}**\n💰 Цена: **{selected_item['price']}**",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer()


# 4. Начало оформления заказа
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy_item(callback: types.CallbackQuery, state: FSMContext):
  item_key = callback.data.replace("buy_", "")

  selected_item = None
  for cat_data in CATALOG.values():
    if item_key in cat_data["items"]:
      selected_item = cat_data["items"][item_key]
      break

  if not selected_item:
    await callback.answer("Товар не найден.")
    return

  await state.update_data(
      item_name=selected_item["name"], item_price=selected_item["price"]
  )

  await callback.message.answer(
      f"Отличный выбор! Вы оформляете заказ на: **{selected_item['name']}** ({selected_item['price']})\n\n"
      f"Пожалуйста, введите ваше **Имя**:"
  )
  await state.set_state(OrderState.waiting_for_name)
  await callback.answer()


# 5. Получение имени
@dp.message(OrderState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
  await state.update_data(name=message.text)
  await message.answer("Спасибо! Теперь отправьте ваш **номер телефона**:")
  await state.set_state(OrderState.waiting_for_phone)


# 6. Получение телефона и показ реквизитов карты
@dp.message(OrderState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
  await state.update_data(phone=message.text)
  data = await state.get_data()

  keyboard = types.InlineKeyboardMarkup(
      inline_keyboard=[[
          types.InlineKeyboardButton(
              text="✅ Я оплатил(а)", callback_data="confirm_payment"
          )
      ]]
  )

  text = (
      f"💳 **Реквизиты для оплаты:**\n\n"
      f"Товар: {data['item_name']}\n"
      f"Сумма к оплате: **{data['item_price']}**\n\n"
      f"Номер карты: `{CARD_NUMBER}`\n"
      f"Получатель: {CARD_HOLDER}\n\n"
      f"⚠️ Переведите сумму на карту, а затем нажмите кнопку **«Я оплатил(а)»**."
  )

  await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
  await state.set_state(OrderState.waiting_for_confirmation)


# 7. Подтверждение оплаты и отправка заказа продавцу
@dp.callback_query(
    OrderState.waiting_for_confirmation, F.data == "confirm_payment"
)
async def process_payment_confirmation(
    callback: types.CallbackQuery, state: FSMContext
):
  data = await state.get_data()
  user = callback.from_user
  username_str = f"@{user.username}" if user.username else "нет username"

  seller_text = (
      f"🎉 **Новый заказ из бота!**\n\n"
      f"📦 Товар: {data['item_name']} ({data['item_price']})\n"
      f"👤 Клиент: {data['name']}\n"
      f"📞 Телефон: {data['phone']}\n"
      f"💬 Профиль: {username_str} (ID: {user.id})\n\n"
      f"*Проверьте поступление денег на карту!*"
  )

  try:
    await bot.send_message(chat_id=SELLER_CHAT_ID, text=seller_text)
  except Exception as e:
    logging.error(f"Не удалось отправить уведомление: {e}")

  await callback.message.answer(
      "Спасибо! Заказ успешно оформлен. Мы проверяем оплату и скоро свяжемся с вами!"
  )
  await state.clear()
  await callback.answer()


# Запуск бота
async def main():
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
  import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Твой токен от @BotFather
TOKEN = "ТВОЙ_TELEGRAM_BOT_TOKEN"

# Твой числовой Telegram ID для получения заказов
SELLER_CHAT_ID = 123456789

# Реквизиты твоей банковской карты
CARD_NUMBER = "4441 **** **** 1234"
CARD_HOLDER = "ИМЯ ФАМИЛИЯ"

# База данных товаров с фотографиями (ссылки на картинки)
CATALOG = {
    "cat_3d": {
        "title": "🖨 Изделия (3D-печать)",
        "items": {
            "item_1": {
                "name": "Ваза дизайнерская",
                "price": "350 грн",
                "photo": "https://picsum.photos/seed/vase3d/400/300",
            },
            "item_2": {
                "name": "Подставка для телефона",
                "price": "150 грн",
                "photo": "https://picsum.photos/seed/stand3d/400/300",
            },
        },
    },
    "cat_china": {
        "title": "📦 Товары из Китая",
        "items": {
            "item_3": {
                "name": "Светодиодная лента (5м)",
                "price": "280 грн",
                "photo": "https://picsum.photos/seed/ledstrip/400/300",
            },
            "item_4": {
                "name": "Беспроводной брелок",
                "price": "200 грн",
                "photo": "https://picsum.photos/seed/keychain/400/300",
            },
        },
    },
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()


# Состояния для оформления заказа
class OrderState(StatesGroup):
  waiting_for_name = State()
  waiting_for_phone = State()
  waiting_for_confirmation = State()


# 1. Главное меню — показ категорий
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
  keyboard_buttons = []
  for cat_key, cat_data in CATALOG.items():
    keyboard_buttons.append(
        [types.InlineKeyboardButton(text=cat_data["title"], callback_data=cat_key)]
    )

  keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
  await message.answer(
      "Привет! Добро пожаловать в наш магазин. Выбери категорию товаров:",
      reply_markup=keyboard,
  )


# 2. Показ товаров выбранной категории
@dp.callback_query(F.data.startswith("cat_"))
async def show_category_items(callback: types.CallbackQuery):
  cat_key = callback.data
  category = CATALOG.get(cat_key)

  if not category:
    await callback.answer("Категория не найдена.")
    return

  keyboard_buttons = []
  for item_key, item_data in category["items"].items():
    button_text = f"👁 {item_data['name']} — {item_data['price']}"
    keyboard_buttons.append([
        types.InlineKeyboardButton(
            text=button_text, callback_data=f"show_{item_key}"
        )
    ])

  keyboard_buttons.append(
      [types.InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="back_to_menu")]
  )

  keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
  await callback.message.edit_text(
      f"Выбрано: **{category['title']}**\nНажмите на товар, чтобы посмотреть фото и описание:",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer()


# Возврат в главное меню
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
  keyboard_buttons = []
  for cat_key, cat_data in CATALOG.items():
    keyboard_buttons.append(
        [types.InlineKeyboardButton(text=cat_data["title"], callback_data=cat_key)]
    )

  keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
  await callback.message.edit_text(
      "Выбери категорию товаров:", reply_markup=keyboard
  )
  await callback.answer()


# 3. Показ карточки товара с фото и кнопкой купить
@dp.callback_query(F.data.startswith("show_"))
async def show_item_card(callback: types.CallbackQuery):
  item_key = callback.data.replace("show_", "")

  selected_item = None
  for cat_data in CATALOG.values():
    if item_key in cat_data["items"]:
      selected_item = cat_data["items"][item_key]
      break

  if not selected_item:
    await callback.answer("Товар не найден.")
    return

  keyboard = types.InlineKeyboardMarkup(
      inline_keyboard=[
          [
              types.InlineKeyboardButton(
                  text=f"🛒 Купить за {selected_item['price']}",
                  callback_data=f"buy_{item_key}",
              )
          ],
          [types.InlineKeyboardButton(text="⬅️ К списку товаров", callback_data="cat_3d")],  # Можно настроить возврат
      ]
  )

  # Отправляем фото с описанием
  await callback.message.answer_photo(
      photo=selected_item["photo"],
      caption=f"📦 **{selected_item['name']}**\n💰 Цена: **{selected_item['price']}**",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer()


# 4. Начало оформления заказа
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy_item(callback: types.CallbackQuery, state: FSMContext):
  item_key = callback.data.replace("buy_", "")

  selected_item = None
  for cat_data in CATALOG.values():
    if item_key in cat_data["items"]:
      selected_item = cat_data["items"][item_key]
      break

  if not selected_item:
    await callback.answer("Товар не найден.")
    return

  await state.update_data(
      item_name=selected_item["name"], item_price=selected_item["price"]
  )

  await callback.message.answer(
      f"Отличный выбор! Вы оформляете заказ на: **{selected_item['name']}** ({selected_item['price']})\n\n"
      f"Пожалуйста, введите ваше **Имя**:"
  )
  await state.set_state(OrderState.waiting_for_name)
  await callback.answer()


# 5. Получение имени
@dp.message(OrderState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
  await state.update_data(name=message.text)
  await message.answer("Спасибо! Теперь отправьте ваш **номер телефона**:")
  await state.set_state(OrderState.waiting_for_phone)


# 6. Получение телефона и показ реквизитов карты
@dp.message(OrderState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
  await state.update_data(phone=message.text)
  data = await state.get_data()

  keyboard = types.InlineKeyboardMarkup(
      inline_keyboard=[[
          types.InlineKeyboardButton(
              text="✅ Я оплатил(а)", callback_data="confirm_payment"
          )
      ]]
  )

  text = (
      f"💳 **Реквизиты для оплаты:**\n\n"
      f"Товар: {data['item_name']}\n"
      f"Сумма к оплате: **{data['item_price']}**\n\n"
      f"Номер карты: `{CARD_NUMBER}`\n"
      f"Получатель: {CARD_HOLDER}\n\n"
      f"⚠️ Переведите сумму на карту, а затем нажмите кнопку **«Я оплатил(а)»**."
  )

  await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
  await state.set_state(OrderState.waiting_for_confirmation)


# 7. Подтверждение оплаты и отправка заказа продавцу
@dp.callback_query(
    OrderState.waiting_for_confirmation, F.data == "confirm_payment"
)
async def process_payment_confirmation(
    callback: types.CallbackQuery, state: FSMContext
):
  data = await state.get_data()
  user = callback.from_user
  username_str = f"@{user.username}" if user.username else "нет username"

  seller_text = (
      f"🎉 **Новый заказ из бота!**\n\n"
      f"📦 Товар: {data['item_name']} ({data['item_price']})\n"
      f"👤 Клиент: {data['name']}\n"
      f"📞 Телефон: {data['phone']}\n"
      f"💬 Профиль: {username_str} (ID: {user.id})\n\n"
      f"*Проверьте поступление денег на карту!*"
  )

  try:
    await bot.send_message(chat_id=SELLER_CHAT_ID, text=seller_text)
  except Exception as e:
    logging.error(f"Не удалось отправить уведомление: {e}")

  await callback.message.answer(
      "Спасибо! Заказ успешно оформлен. Мы проверяем оплату и скоро свяжемся с вами!"
  )
  await state.clear()
  await callback.answer()


# Запуск бота
async def main():
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Твой токен от @BotFather
TOKEN = "ТВОЙ_TELEGRAM_BOT_TOKEN"

# Твой числовой Telegram ID для получения заказов
SELLER_CHAT_ID = 123456789

# Реквизиты твоей банковской карты
CARD_NUMBER = "4441 **** **** 1234"
CARD_HOLDER = "ИМЯ ФАМИЛИЯ"

# База данных товаров с фотографиями (ссылки на картинки)
CATALOG = {
    "cat_3d": {
        "title": "🖨 Изделия (3D-печать)",
        "items": {
            "item_1": {
                "name": "Ваза дизайнерская",
                "price": "350 грн",
                "photo": "https://picsum.photos/seed/vase3d/400/300",
            },
            "item_2": {
                "name": "Подставка для телефона",
                "price": "150 грн",
                "photo": "https://picsum.photos/seed/stand3d/400/300",
            },
        },
    },
    "cat_china": {
        "title": "📦 Товары из Китая",
        "items": {
            "item_3": {
                "name": "Светодиодная лента (5м)",
                "price": "280 грн",
                "photo": "https://picsum.photos/seed/ledstrip/400/300",
            },
            "item_4": {
                "name": "Беспроводной брелок",
                "price": "200 грн",
                "photo": "https://picsum.photos/seed/keychain/400/300",
            },
        },
    },
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()


# Состояния для оформления заказа
class OrderState(StatesGroup):
  waiting_for_name = State()
  waiting_for_phone = State()
  waiting_for_confirmation = State()


# 1. Главное меню — показ категорий
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
  keyboard_buttons = []
  for cat_key, cat_data in CATALOG.items():
    keyboard_buttons.append(
        [types.InlineKeyboardButton(text=cat_data["title"], callback_data=cat_key)]
    )

  keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
  await message.answer(
      "Привет! Добро пожаловать в наш магазин. Выбери категорию товаров:",
      reply_markup=keyboard,
  )


# 2. Показ товаров выбранной категории
@dp.callback_query(F.data.startswith("cat_"))
async def show_category_items(callback: types.CallbackQuery):
  cat_key = callback.data
  category = CATALOG.get(cat_key)

  if not category:
    await callback.answer("Категория не найдена.")
    return

  keyboard_buttons = []
  for item_key, item_data in category["items"].items():
    button_text = f"👁 {item_data['name']} — {item_data['price']}"
    keyboard_buttons.append([
        types.InlineKeyboardButton(
            text=button_text, callback_data=f"show_{item_key}"
        )
    ])

  keyboard_buttons.append(
      [types.InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="back_to_menu")]
  )

  keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
  await callback.message.edit_text(
      f"Выбрано: **{category['title']}**\nНажмите на товар, чтобы посмотреть фото и описание:",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer()


# Возврат в главное меню
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
  keyboard_buttons = []
  for cat_key, cat_data in CATALOG.items():
    keyboard_buttons.append(
        [types.InlineKeyboardButton(text=cat_data["title"], callback_data=cat_key)]
    )

  keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
  await callback.message.edit_text(
      "Выбери категорию товаров:", reply_markup=keyboard
  )
  await callback.answer()


# 3. Показ карточки товара с фото и кнопкой купить
@dp.callback_query(F.data.startswith("show_"))
async def show_item_card(callback: types.CallbackQuery):
  item_key = callback.data.replace("show_", "")

  selected_item = None
  for cat_data in CATALOG.values():
    if item_key in cat_data["items"]:
      selected_item = cat_data["items"][item_key]
      break

  if not selected_item:
    await callback.answer("Товар не найден.")
    return

  keyboard = types.InlineKeyboardMarkup(
      inline_keyboard=[
          [
              types.InlineKeyboardButton(
                  text=f"🛒 Купить за {selected_item['price']}",
                  callback_data=f"buy_{item_key}",
              )
          ],
          [types.InlineKeyboardButton(text="⬅️ К списку товаров", callback_data="cat_3d")],  # Можно настроить возврат
      ]
  )

  # Отправляем фото с описанием
  await callback.message.answer_photo(
      photo=selected_item["photo"],
      caption=f"📦 **{selected_item['name']}**\n💰 Цена: **{selected_item['price']}**",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer()


# 4. Начало оформления заказа
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy_item(callback: types.CallbackQuery, state: FSMContext):
  item_key = callback.data.replace("buy_", "")

  selected_item = None
  for cat_data in CATALOG.values():
    if item_key in cat_data["items"]:
      selected_item = cat_data["items"][item_key]
      break

  if not selected_item:
    await callback.answer("Товар не найден.")
    return

  await state.update_data(
      item_name=selected_item["name"], item_price=selected_item["price"]
  )

  await callback.message.answer(
      f"Отличный выбор! Вы оформляете заказ на: **{selected_item['name']}** ({selected_item['price']})\n\n"
      f"Пожалуйста, введите ваше **Имя**:"
  )
  await state.set_state(OrderState.waiting_for_name)
  await callback.answer()


# 5. Получение имени
@dp.message(OrderState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
  await state.update_data(name=message.text)
  await message.answer("Спасибо! Теперь отправьте ваш **номер телефона**:")
  await state.set_state(OrderState.waiting_for_phone)


# 6. Получение телефона и показ реквизитов карты
@dp.message(OrderState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
  await state.update_data(phone=message.text)
  data = await state.get_data()

  keyboard = types.InlineKeyboardMarkup(
      inline_keyboard=[[
          types.InlineKeyboardButton(
              text="✅ Я оплатил(а)", callback_data="confirm_payment"
          )
      ]]
  )

  text = (
      f"💳 **Реквизиты для оплаты:**\n\n"
      f"Товар: {data['item_name']}\n"
      f"Сумма к оплате: **{data['item_price']}**\n\n"
      f"Номер карты: `{CARD_NUMBER}`\n"
      f"Получатель: {CARD_HOLDER}\n\n"
      f"⚠️ Переведите сумму на карту, а затем нажмите кнопку **«Я оплатил(а)»**."
  )

  await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
  await state.set_state(OrderState.waiting_for_confirmation)


# 7. Подтверждение оплаты и отправка заказа продавцу
@dp.callback_query(
    OrderState.waiting_for_confirmation, F.data == "confirm_payment"
)
async def process_payment_confirmation(
    callback: types.CallbackQuery, state: FSMContext
):
  data = await state.get_data()
  user = callback.from_user
  username_str = f"@{user.username}" if user.username else "нет username"

  seller_text = (
      f"🎉 **Новый заказ из бота!**\n\n"
      f"📦 Товар: {data['item_name']} ({data['item_price']})\n"
      f"👤 Клиент: {data['name']}\n"
      f"📞 Телефон: {data['phone']}\n"
      f"💬 Профиль: {username_str} (ID: {user.id})\n\n"
      f"*Проверьте поступление денег на карту!*"
  )

  try:
    await bot.send_message(chat_id=SELLER_CHAT_ID, text=seller_text)
  except Exception as e:
    logging.error(f"Не удалось отправить уведомление: {e}")

  await callback.message.answer(
      "Спасибо! Заказ успешно оформлен. Мы проверяем оплату и скоро свяжемся с вами!"
  )
  await state.clear()
  await callback.answer()


# Запуск бота
async def main():
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
