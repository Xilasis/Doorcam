from flask import Flask, request
import requests
import threading

from utils.send_telegram import send_photo
from config import API_KEY, RASPBERRY_URL
import telegram_bot 

app = Flask(__name__)


# 🔐 seguridad simple
def check_api(req):
    return req.headers.get("X-API-KEY") == API_KEY


# 📸 recibir imagen desde Raspberry
@app.route("/upload", methods=["POST"])
def upload():
    if not check_api(request):
        return "No autorizado", 403

    file = request.files["image"]
    file.save("temp.jpg")

    send_photo("temp.jpg", "📸 Foto desde ESP32")

    return "OK"


# 📷 pedir foto
@app.route("/request_photo", methods=["POST"])
def request_photo():
    requests.get(f"{RASPBERRY_URL}/capture")
    return "OK"


# 🚀 INICIAR BOT EN SEGUNDO PLANO
def start_bot():
    telegram_bot.run_bot()


if __name__ == "__main__":
    print("🚀 Iniciando sistema completo...")

    # hilo para bot
    t = threading.Thread(target=start_bot)
    t.daemon = True
    t.start()

    # flask
    app.run(host="0.0.0.0", port=5000)