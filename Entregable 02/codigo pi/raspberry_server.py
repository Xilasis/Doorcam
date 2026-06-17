from flask import Flask
import requests

app = Flask(__name__)

ESP32_URL = "http://192.168.0.10"
FLASK_SERVER = "http://192.168.0.8:5000"
API_KEY = "123456"


@app.route("/capture", methods=["GET"])
def capture():
    print("📸 Pidiendo foto a ESP32...")

    r = requests.get(f"{ESP32_URL}/capture", stream=True)

    print("📤 Enviando a Flask...")

    files = {"image": ("image.jpg", r.raw, "image/jpeg")}

    requests.post(
        f"{FLASK_SERVER}/upload",
        files=files,
        headers={"X-API-KEY": API_KEY}
    )

    return "OK"


app.run(host="0.0.0.0", port=5001)