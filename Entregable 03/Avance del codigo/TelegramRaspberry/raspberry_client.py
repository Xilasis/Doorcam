import requests

from config import (
    RASPBERRY_IP,
    RASPBERRY_TOKEN
)


def get_photo():

    url = (
        f"http://{RASPBERRY_IP}:5000/capture"
        f"?token={RASPBERRY_TOKEN}"
    )

    response = requests.get(url)

    return response.content


def get_status():

    url = (
        f"http://{RASPBERRY_IP}:5000/status"
        f"?token={RASPBERRY_TOKEN}"
    )

    response = requests.get(url)

    return response.json()