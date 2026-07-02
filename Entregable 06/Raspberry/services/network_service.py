"""
network_service.py
Diagnósticos del nodo Raspberry Pi.
"""

import socket
import platform
import psutil
from ping3 import ping
import config


class NetworkService:


    def get_ip_info(self):

        hostname = socket.gethostname()

        ip = socket.gethostbyname(hostname)

        return {
            "hostname": hostname,
            "ip": ip
        }


    def ping_flask(self):

        samples = []

        for _ in range(config.PING_COUNT):

            latency = ping(
                config.PING_TARGET,
                unit="ms"
            )

            if latency:
                samples.append(latency)


        if not samples:

            return {
                "status": "DOWN"
            }


        jitter = [
            abs(samples[i] - samples[i-1])
            for i in range(1, len(samples))
        ]


        return {

            "status": "UP",

            "min_ms": min(samples),

            "avg_ms": (
                sum(samples)
                / len(samples)
            ),

            "max_ms": max(samples),

            "jitter_ms": (
                sum(jitter)
                / len(jitter)
                if jitter else 0
            ),

            "packet_loss": (
                100 -
                (len(samples)
                / config.PING_COUNT)
                * 100
            )
        }


    def system_status(self):

        temp = None

        try:
            with open(
                "/sys/class/thermal/thermal_zone0/temp"
            ) as f:

                temp = (
                    int(f.read()) / 1000
                )

        except Exception:
            pass


        return {

            "system": platform.system(),

            "cpu_percent":
                psutil.cpu_percent(),

            "ram_percent":
                psutil.virtual_memory().percent,

            "disk_percent":
                psutil.disk_usage("/").percent,

            "temperature":
                temp
        }


    def health_check(self):

        return {

            "network":
                self.ping_flask(),

            "system":
                self.system_status()
        }
