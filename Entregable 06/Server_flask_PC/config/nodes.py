"""
Catálogo de nodos IoT autorizados.
"""

NODES = {


    "rpi-01": {

        "name": "Raspberry Pi Zero 2W",

        "type": "RPI_ZERO_2W",

        "ip": "192.168.0.12",

        "port": 5001,

        "token": "TOKEN_RPI",

        "capabilities": {

            "status": True,

            "network": True,

            "capture": True,

            "controls": [
                "reboot",
                "restart_camera"
            ],
# Endpoints de captura
            "captures": {
                "photo": "/capture"
            }
        }
    },


    "esp32-01": {

        "name": "ESP32-CAM",

        "type": "ESP32_CAM",

        "ip": "192.168.0.16",

        "port": 80,

        "token": "TOKEN_ESP32",

        "capabilities": {

            "status": True,

            "network": True,

            "capture": True,

            "controls": [
                "flash_on",
                "flash_off",
                "alert",
            ]
            ,"captures": [
                "photo",
                "photo_with_flash"
            ]         
        }
    }
}
#photo, photo_with_flash -> FASE2