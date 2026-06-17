import requests
from config import TELEGRAM_TOKEN, CHAT_ID


def send_message(text):
    """
    Envía un mensaje de texto a Telegram
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        response = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text
        })

        if response.status_code != 200:
            print("❌ Error enviando mensaje:", response.text)

    except Exception as e:
        print("❌ Excepción en send_message:", e)


def send_photo(path, caption=""):
    """
    Envía una imagen a Telegram
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"

    try:
        with open(path, "rb") as photo:
            response = requests.post(
                url,
                files={"photo": photo},
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption
                }
            )

        if response.status_code != 200:
            print("❌ Error enviando foto:", response.text)

    except Exception as e:
        print("❌ Excepción en send_photo:", e)