import telebot

from config import BOT_TOKEN

from raspberry_client import (
    get_photo,
    get_status
)

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def start(message):

    bot.reply_to(
        message,
        "Bot conectado a Raspberry"
    )


@bot.message_handler(commands=['status'])
def status(message):

    try:

        data = get_status()

        texto = (
            f"Camara: {data['camera']}\n"
            f"Servidor: {data['server']}"
        )

        bot.send_message(
            message.chat.id,
            texto
        )

    except Exception as e:

        bot.send_message(
            message.chat.id,
            str(e)
        )


@bot.message_handler(commands=['foto'])
def foto(message):

    try:

        image = get_photo()

        bot.send_photo(
            message.chat.id,
            image
        )

    except Exception as e:

        bot.send_message(
            message.chat.id,
            str(e)
        )


print("Bot iniciado")

bot.infinity_polling()