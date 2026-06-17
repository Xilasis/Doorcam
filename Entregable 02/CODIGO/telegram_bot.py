import requests
import time
from config import TELEGRAM_TOKEN

LAST_UPDATE_ID = None


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })


def run_bot():
    global LAST_UPDATE_ID

    print("🤖 Bot iniciado dentro de Flask...")

    while True:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"

        params = {"timeout": 100}
        if LAST_UPDATE_ID:
            params["offset"] = LAST_UPDATE_ID + 1

        r = requests.get(url, params=params).json()

        for u in r.get("result", []):
            LAST_UPDATE_ID = u["update_id"]

            if "message" in u:
                chat_id = u["message"]["chat"]["id"]
                text = u["message"].get("text", "")

                print("Mensaje:", text)

                if text == "/foto":
                    send_message(chat_id, "📸 Tomando foto...")

                    try:
                        requests.post("http://127.0.0.1:5000/request_photo")
                    except Exception as e:
                        send_message(chat_id, f"Error: {e}")

        time.sleep(1)