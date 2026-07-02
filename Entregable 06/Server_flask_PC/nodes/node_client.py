"""
Cliente HTTP universal para nodos IoT.
"""

import requests

from config.nodes import NODES


class NodeClient:


    def __init__(self, timeout=5):

        self.timeout = timeout

        self.session = requests.Session()


    def get_node_info(self, node_id):
        """
        Devuelve información del nodo.
        """

        node = NODES.get(node_id)

        if not node:

            raise ValueError(
                f"Nodo no registrado: {node_id}"
            )

        return node


    def _url(self, node_id, endpoint):
        """
        Construye URL del nodo.
        """

        node = self.get_node_info(node_id)

        return (
            f"http://{node['ip']}"
            f":{node['port']}"
            f"{endpoint}"
        )


    def _headers(self, node_id):
        """
        Headers de autenticación.
        """

        node = self.get_node_info(node_id)

        return {

            "Authorization":
                f"Bearer {node['token']}",

            "X-Node-ID":
                node_id
        }


    def _request(
        self,
        method,
        node_id,
        endpoint,
        json=None
    ):
        """
        Petición HTTP genérica.
        """

        response = self.session.request(

            method=method,

            url=self._url(
                node_id,
                endpoint
            ),

            headers=self._headers(
                node_id
            ),

            json=json,

            timeout=self.timeout
        )


        response.raise_for_status()


        return response


    # ==========================
    # API pública
    # ==========================


    def capture(self, node_id):
        """
        Captura una imagen.
        """

        response = self._request(
            "GET",
            node_id,
            "/capture"
        )

        return response.content
    
    def capture_flash(self, node_id):
        """ Captura una imagen utilizando el flash.
            """

        response = self._request(
            "GET",
            node_id,
            "/capture_flash"
        )

        return response.content


    def status(self, node_id):
        """
        Estado general.
        """

        response = self._request(
            "GET",
            node_id,
            "/status"
        )

        return response.json()


    def network(self, node_id):
        """
        Información de red.
        """

        response = self._request(
            "GET",
            node_id,
            "/network"
        )

        return response.json()


    def control(self, node_id, command):
        """
        Envía comando remoto.
        """

        payload = {

            "command": command
        }


        response = self._request(

            "POST",

            node_id,

            "/control",

            json=payload
        )


        return response.json()


    def close(self):
        """
        Libera recursos HTTP.
        """

        self.session.close()