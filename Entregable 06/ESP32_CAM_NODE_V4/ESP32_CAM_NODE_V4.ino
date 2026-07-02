/************************************************************
 * ESP32-CAM NODE V3
 *
 * Arquitectura IoT distribuida
 *
 * CONTROL (JSON)
 * --------------------------
 * POST /control
 *  - flash_on
 *  - flash_off
 *  - alert
 *
 *
 * CAPTURA (JPEG)
 * --------------------------
 * GET /capture
 * GET /capture_flash
 *
 *
 * EVENTOS AUTÓNOMOS
 * --------------------------
 * PIR GPIO14
 *
 * POST /api/v1/events/image
 *
 * Headers:
 * Authorization
 * X-Node-ID
 * X-Event
 * X-Processing
 *
 ************************************************************/


/************************************************************
 * LIBRERÍAS
 ************************************************************/

#include <WiFi.h>
#include <WebServer.h>
#include <WiFiClient.h>
#include <HTTPClient.h>

#include "esp_camera.h"

#include <ArduinoJson.h>


/************************************************************
 * IDENTIDAD DEL NODO
 ************************************************************/

#define NODE_ID "esp32-01"

#define DEVICE_TYPE "ESP32-CAM"


/************************************************************
 * CONFIGURACIÓN WIFI
 ************************************************************/

const char* WIFI_SSID =
    "ISABEL_2.4Ghz";


const char* WIFI_PASSWORD =
    "25022002";


/************************************************************
 * AUTENTICACIÓN
 ************************************************************/

const char* AUTH_TOKEN =
    "TOKEN_ESP32";


/************************************************************
 * FLASK GATEWAY CENTRAL
 ************************************************************/

const char* FLASK_HOST =
    "192.168.1.3";


const int FLASK_PORT = 8080;


const char* FLASK_ENDPOINT =
    "/api/v1/events/image";


/************************************************************
 * HARDWARE ESP32-CAM AI THINKER
 ************************************************************/


/*
 * Sensor PIR HC-SR501
 *
 * OUT ---- GPIO14
 */
#define PIR_PIN 13


/*
 * Flash integrado
 *
 * LED blanco AI Thinker
 */
#define FLASH_PIN 4



/************************************************************
 * CONFIGURACIÓN EVENTOS PIR
 ************************************************************/


/*
 * Tiempo mínimo entre eventos
 * de movimiento.
 */
#define PIR_COOLDOWN_MS 5000



/************************************************************
 * PINOUT CÁMARA OV2640
 ************************************************************/

#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1

#define XCLK_GPIO_NUM      0

#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27


#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34

#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36

#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19

#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5


#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23

#define PCLK_GPIO_NUM     22



/************************************************************
 * SERVIDOR HTTP REST
 ************************************************************/

WebServer server(80);



/************************************************************
 * ESTADOS DEL SISTEMA
 ************************************************************/


/*
 * Estado actual del LED flash.
 */
bool flashEnabled = false;


/*
 * Exclusión mutua de cámara.
 *
 * Evita:
 *
 * /foto
 * /foto_flash
 * PIR
 *
 * accediendo al OV2640
 * simultáneamente.
 */
volatile bool cameraBusy = false;


/*
 * Estado anterior del PIR.
 */
bool pirLastState = LOW;


/*
 * Evita múltiples eventos mientras
 * el PIR permanezca en HIGH.
 */
bool waitingPirReset = false;


/*
 * Tiempo del último evento PIR.
 */
unsigned long lastMotionTime = 0;


/************************************************************
 * MONITOR WIFI
 ************************************************************/


unsigned long lastWiFiCheck = 0;


const unsigned long WIFI_CHECK_INTERVAL =
    10000;



/************************************************************
 * CONFIGURACIÓN DE CÁMARA
 ************************************************************/

camera_config_t cameraConfig;



/************************************************************
 * DECLARACIÓN DE SERVICIOS
 ************************************************************/


/**************** Camera Service ****************/

bool lockCamera();


void unlockCamera();


/*
 * Captura un frame reciente.
 *
 * El consumidor es responsable de:
 *
 * esp_camera_fb_return(fb);
 */
camera_fb_t* captureFreshFrame();



/**************** Flash Service ****************/

void setFlash(bool state);


void flashAlert();



/**************** Network Service ****************/

void connectWiFi();


void maintainWiFi();



/**************** Security Service ****************/

bool authenticate();



/**************** REST Handlers ****************/

void handleStatus();


void handleNetwork();


void handleCapture();


/*
 * Nueva captura con iluminación.
 *
 * GET /capture_flash
 */
void handleCaptureFlash();


void handleControl();


void registerRoutes();



/**************** Event Service ****************/

void checkPIR();


bool sendMotionEvent();

/************************************************************
 * FIN PARTE 1
 *
 * Continúa:
 *
 * PARTE 2
 *
 * - WiFi Service
 * - Reconexión automática
 * - Inicialización OV2640
 * - Camera Lock
 * - captureFreshFrame()
 * - Flash Service
 *
 ************************************************************/
/************************************************************
 * PARTE 2
 *
 * WiFi Service
 * Camera Service
 * Flash Service
 *
 ************************************************************/


/************************************************************
 * WIFI SERVICE
 ************************************************************/


void connectWiFi()
{
    Serial.println();
    Serial.println("[WiFi] Connecting...");


    WiFi.mode(WIFI_STA);


    WiFi.begin(
        WIFI_SSID,
        WIFI_PASSWORD
    );


    unsigned long startTime =
        millis();


    while(
        WiFi.status() != WL_CONNECTED &&
        millis() - startTime < 15000
    )
    {
        Serial.print(".");
        delay(500);
    }


    Serial.println();


    if(WiFi.status() == WL_CONNECTED)
    {
        Serial.println(
            "[WiFi] Connected"
        );

        Serial.print(
            "[WiFi] IP: "
        );

        Serial.println(
            WiFi.localIP()
        );
    }
    else
    {
        Serial.println(
            "[WiFi] Connection timeout"
        );
    }
}


/************************************************************
 * Verificación periódica de WiFi
 *
 * No bloquea el funcionamiento del nodo.
 ************************************************************/

void maintainWiFi()
{
    unsigned long now =
        millis();


    if(
        now - lastWiFiCheck <
        WIFI_CHECK_INTERVAL
    )
    {
        return;
    }


    lastWiFiCheck = now;


    if(WiFi.status() != WL_CONNECTED)
    {
        Serial.println(
            "[WiFi] Reconnecting..."
        );


        WiFi.disconnect();


        WiFi.begin(
            WIFI_SSID,
            WIFI_PASSWORD
        );
    }
}



/************************************************************
 * CAMERA LOCK
 *
 * Protege el acceso concurrente
 * al periférico OV2640.
 ************************************************************/


bool lockCamera()
{
    if(cameraBusy)
    {
        Serial.println(
            "[Camera] Busy"
        );

        return false;
    }


    cameraBusy = true;


    return true;
}



void unlockCamera()
{
    cameraBusy = false;
}



/************************************************************
 * INICIALIZACIÓN OV2640
 ************************************************************/

bool initCamera()
{

    cameraConfig.ledc_channel =
        LEDC_CHANNEL_0;


    cameraConfig.ledc_timer =
        LEDC_TIMER_0;


    cameraConfig.pin_d0 = Y2_GPIO_NUM;
    cameraConfig.pin_d1 = Y3_GPIO_NUM;
    cameraConfig.pin_d2 = Y4_GPIO_NUM;
    cameraConfig.pin_d3 = Y5_GPIO_NUM;
    cameraConfig.pin_d4 = Y6_GPIO_NUM;
    cameraConfig.pin_d5 = Y7_GPIO_NUM;
    cameraConfig.pin_d6 = Y8_GPIO_NUM;
    cameraConfig.pin_d7 = Y9_GPIO_NUM;


    cameraConfig.pin_xclk =
        XCLK_GPIO_NUM;


    cameraConfig.pin_pclk =
        PCLK_GPIO_NUM;


    cameraConfig.pin_vsync =
        VSYNC_GPIO_NUM;


    cameraConfig.pin_href =
        HREF_GPIO_NUM;


    cameraConfig.pin_sscb_sda =
        SIOD_GPIO_NUM;


    cameraConfig.pin_sscb_scl =
        SIOC_GPIO_NUM;


    cameraConfig.pin_pwdn =
        PWDN_GPIO_NUM;


    cameraConfig.pin_reset =
        RESET_GPIO_NUM;


    cameraConfig.xclk_freq_hz =
        20000000;


    cameraConfig.pixel_format =
        PIXFORMAT_JPEG;


    if(psramFound())
    {
        Serial.println(
            "[Camera] PSRAM detected"
        );


        /*
         * VGA es un equilibrio entre
         * calidad y consumo.
         */

        cameraConfig.frame_size =
            FRAMESIZE_VGA;


        cameraConfig.jpeg_quality =
            10;


        /*
         * Doble buffer:
         * mayor rendimiento y menor latencia.
         */
        cameraConfig.fb_count =
            2;
    }
    else
    {
        Serial.println(
            "[Camera] No PSRAM"
        );


        cameraConfig.frame_size =
            FRAMESIZE_QVGA;


        cameraConfig.jpeg_quality =
            12;


        cameraConfig.fb_count =
            1;
    }


    esp_err_t result =
        esp_camera_init(
            &cameraConfig
        );


    if(result != ESP_OK)
    {
        Serial.printf(
            "[Camera] Init error 0x%x\n",
            result
        );

        return false;
    }


    Serial.println(
        "[Camera] Ready"
    );


    return true;
}



/************************************************************
 * CAPTURA SINCRONIZADA
 *
 * Objetivo:
 *
 * /foto
 * /foto_flash
 * PIR
 *
 * Deben obtener un frame actual.
 ************************************************************/

camera_fb_t* captureFreshFrame()
{

    /*
     * Con fb_count = 2 puede existir
     * un frame previo en cola.
     *
     * Se descarta para reducir la
     * latencia temporal.
     */

    camera_fb_t* oldFrame =
        esp_camera_fb_get();


    if(oldFrame)
    {
        esp_camera_fb_return(
            oldFrame
        );
    }


    /*
     * Captura efectiva del momento.
     */

    camera_fb_t* frame =
        esp_camera_fb_get();


    if(!frame)
    {
        Serial.println(
            "[Camera] Capture failed"
        );

        return nullptr;
    }


    Serial.printf(
        "[Camera] New frame: %u bytes\n",
        frame->len
    );


    return frame;
}



/************************************************************
 * FLASH SERVICE
 ************************************************************/


void setFlash(bool state)
{

    flashEnabled = state;


    digitalWrite(
        FLASH_PIN,
        state ? HIGH : LOW
    );


    Serial.printf(
        "[Flash] %s\n",
        state ? "ON" : "OFF"
    );
}



/************************************************************
 * Alerta visual
 *
 * Parpadeo del flash:
 * ON 250 ms
 * OFF 250 ms
 * Repetir 3 veces
 ************************************************************/

void flashAlert()
{

    for(int i = 0; i < 3; i++)
    {

        digitalWrite(
            FLASH_PIN,
            HIGH
        );

        delay(250);


        digitalWrite(
            FLASH_PIN,
            LOW
        );

        delay(250);
    }


    flashEnabled = false;


    Serial.println(
        "[Flash] Alert completed"
    );
}
/************************************************************
 * PARTE 3
 *
 * REST API
 *
 ************************************************************/


/************************************************************
 * AUTENTICACIÓN
 *
 * Se valida el Bearer Token enviado por Flask.
 ************************************************************/

bool authenticate()
{
    String auth =
        server.header("Authorization");


    String expected =
        "Bearer " + String(AUTH_TOKEN);


    if(auth != expected)
    {
        server.send(
            401,
            "application/json",
            "{\"error\":\"Unauthorized\"}"
        );


        Serial.println(
            "[AUTH] Unauthorized"
        );


        return false;
    }


    return true;
}


/************************************************************
 * UTILIDAD PARA RESPUESTAS JSON
 ************************************************************/

void sendJSON(JsonDocument &doc)
{
    String response;


    serializeJson(
        doc,
        response
    );


    server.send(
        200,
        "application/json",
        response
    );
}



/************************************************************
 * GET /status
 *
 * Estado general del nodo.
 ************************************************************/

void handleStatus()
{
    if(!authenticate())
        return;


    JsonDocument doc;


    doc["node_id"] = NODE_ID;

    doc["device"] = DEVICE_TYPE;

    doc["status"] = "online";

    doc["wifi"] =
        WiFi.status() == WL_CONNECTED;


    doc["ip"] =
        WiFi.localIP().toString();


    doc["free_heap"] =
        ESP.getFreeHeap();


    doc["flash"] =
        flashEnabled;


    doc["camera_busy"] =
        cameraBusy;


    sendJSON(doc);
}



/************************************************************
 * GET /network
 *
 * Información de red.
 ************************************************************/

void handleNetwork()
{
    if(!authenticate())
        return;


    JsonDocument doc;


    doc["ssid"] =
        WiFi.SSID();


    doc["ip"] =
        WiFi.localIP().toString();


    doc["rssi"] =
        WiFi.RSSI();


    doc["mac"] =
        WiFi.macAddress();


    sendJSON(doc);
}



/************************************************************
 * GET /capture
 *
 * Captura normal sin flash.
 *
 * Garantiza:
 * - Frame reciente.
 * - Acceso exclusivo a cámara.
 ************************************************************/

void handleCapture()
{
    if(!authenticate())
        return;


    if(!lockCamera())
    {
        server.send(
            503,
            "text/plain",
            "Camera busy"
        );

        return;
    }


    camera_fb_t* fb =
        captureFreshFrame();


    if(!fb)
    {
        unlockCamera();


        server.send(
            500,
            "text/plain",
            "Capture failed"
        );

        return;
    }


    server.send_P(
        200,
        "image/jpeg",
        (const char*) fb->buf,
        fb->len
    );


    esp_camera_fb_return(fb);


    unlockCamera();


    Serial.println(
        "[CAPTURE] Image delivered"
    );
}



/************************************************************
 * GET /capture_flash
 *
 * Captura con iluminación.
 *
 * Flujo:
 *
 * Flash ON
 *     |
 * Espera 150 ms
 *     |
 * Captura frame fresco
 *     |
 * Flash OFF
 *
 ************************************************************/

void handleCaptureFlash()
{
    if(!authenticate())
        return;


    if(!lockCamera())
    {
        server.send(
            503,
            "text/plain",
            "Camera busy"
        );

        return;
    }


    setFlash(true);


    delay(150);


    camera_fb_t* fb =
        captureFreshFrame();


    if(!fb)
    {
        setFlash(false);


        unlockCamera();


        server.send(
            500,
            "text/plain",
            "Capture failed"
        );

        return;
    }


    server.send_P(
        200,
        "image/jpeg",
        (const char*) fb->buf,
        fb->len
    );


    /*
     * Liberación segura del framebuffer
     */
    esp_camera_fb_return(fb);


    setFlash(false);


    unlockCamera();


    Serial.println(
        "[CAPTURE_FLASH] Image delivered"
    );
}



/************************************************************
 * POST /control
 *
 * Solo comandos de control.
 *
 * Respuesta:
 * JSON
 *
 * Comandos:
 *
 * flash_on
 * flash_off
 * alert
 *
 ************************************************************/

void handleControl()
{
    if(!authenticate())
        return;


    JsonDocument doc;


    DeserializationError error =
        deserializeJson(
            doc,
            server.arg("plain")
        );


    if(error)
    {
        server.send(
            400,
            "application/json",
            "{\"error\":\"Invalid JSON\"}"
        );

        return;
    }


    String command =
        doc["command"] | "";


    Serial.print(
        "[CONTROL] Command: "
    );

    Serial.println(command);


    if(command == "flash_on")
    {
        setFlash(true);
    }


    else if(command == "flash_off")
    {
        setFlash(false);
    }


    else if(command == "alert")
    {
        flashAlert();
    }


    else
    {
        server.send(
            400,
            "application/json",
            "{\"error\":\"Unknown command\"}"
        );

        return;
    }


    JsonDocument response;


    response["status"] =
        "ok";


    response["command"] =
        command;


    sendJSON(response);
}



/************************************************************
 * REGISTRO DE ENDPOINTS
 ************************************************************/

void registerRoutes()
{
    server.on(
        "/status",
        HTTP_GET,
        handleStatus
    );


    server.on(
        "/network",
        HTTP_GET,
        handleNetwork
    );


    server.on(
        "/capture",
        HTTP_GET,
        handleCapture
    );


    server.on(
        "/capture_flash",
        HTTP_GET,
        handleCaptureFlash
    );


    server.on(
        "/control",
        HTTP_POST,
        handleControl
    );
}
/************************************************************
 * PARTE 4
 *
 * PIR SERVICE
 * EVENT MANAGER
 *
 ************************************************************/


/************************************************************
 * checkPIR()
 *
 * Se ejecuta continuamente desde loop().
 *
 * No utiliza interrupciones porque el HC-SR501 mantiene
 * la salida HIGH durante un tiempo configurable.
 *
 ************************************************************/

void checkPIR()
{
    bool currentState =
        digitalRead(PIR_PIN);


    /********************************************************
     * Estado WAIT_RESET
     *
     * Ya ocurrió un evento y se espera que el PIR vuelva
     * a LOW antes de aceptar otro movimiento.
     ********************************************************/

    if(waitingPirReset)
    {
        if(currentState == LOW)
        {
            waitingPirReset = false;

            Serial.println(
                "[PIR] Sensor rearmed"
            );
        }


        pirLastState = currentState;

        return;
    }


    /********************************************************
     * Detección de flanco LOW -> HIGH
     ********************************************************/

    bool risingEdge =
        (
            pirLastState == LOW &&
            currentState == HIGH
        );


    pirLastState = currentState;


    if(!risingEdge)
    {
        return;
    }


    Serial.println(
        "[PIR] Motion detected"
    );


    /********************************************************
     * Control de cooldown
     ********************************************************/

    unsigned long now =
        millis();


    if(now - lastMotionTime < PIR_COOLDOWN_MS)
    {
        Serial.println(
            "[PIR] Ignored: cooldown active"
        );

        return;
    }


    /********************************************************
     * Protección contra conflicto con:
     *
     * - /capture
     * - /capture_flash
     * - otro evento PIR
     *
     * Prioridad:
     * El usuario tiene prioridad sobre eventos automáticos.
     ********************************************************/

    if(cameraBusy)
    {
        Serial.println(
            "[PIR] Ignored: camera busy"
        );

        return;
    }


    /********************************************************
     * Registrar el momento del evento.
     ********************************************************/

    lastMotionTime = now;


    /*
     * Se bloquean nuevos eventos hasta que el PIR
     * vuelva a LOW.
     */
    waitingPirReset = true;


    Serial.println(
        "[PIR] Starting event"
    );


    /********************************************************
     * Envío al Flask Gateway.
     *
     * La función se implementa en la Parte 5.
     ********************************************************/

    bool result =
        sendMotionEvent();


    if(result)
    {
        Serial.println(
            "[PIR] Event completed"
        );
    }
    else
    {
        Serial.println(
            "[PIR] Event failed"
        );
    }
}
/************************************************************
 * PARTE 5
 *
 * HTTP EVENT CLIENT
 *
 * ESP32
 *   |
 *   | multipart/form-data
 *   v
 * Flask Gateway
 *
 ************************************************************/


bool sendMotionEvent()
{
    Serial.println(
        "[EVENT] Starting motion event"
    );


    /********************************************************
     * Obtener acceso exclusivo a la cámara
     ********************************************************/

    if(!lockCamera())
    {
        Serial.println(
            "[EVENT] Camera busy"
        );

        return false;
    }


    /********************************************************
     * Capturar imagen sincronizada con el movimiento
     ********************************************************/

    camera_fb_t* fb =
        captureFreshFrame();


    if(!fb)
    {
        Serial.println(
            "[EVENT] Capture failed"
        );

        unlockCamera();

        return false;
    }


    /********************************************************
     * Verificar conectividad WiFi
     ********************************************************/

    if(WiFi.status() != WL_CONNECTED)
    {
        Serial.println(
            "[EVENT] WiFi disconnected"
        );

        esp_camera_fb_return(fb);

        unlockCamera();

        return false;
    }


    /********************************************************
     * Conexión TCP hacia Flask
     ********************************************************/

    WiFiClient client;


    if(
        !client.connect(
            FLASK_HOST,
            FLASK_PORT
        )
    )
    {
        Serial.println(
            "[EVENT] Flask connection failed"
        );


        esp_camera_fb_return(fb);

        unlockCamera();

        return false;
    }


    Serial.println(
        "[EVENT] Connected to Flask"
    );


    /********************************************************
     * Construcción multipart/form-data
     ********************************************************/

    String boundary =
        "ESP32CAMBoundary";


    String partHeader =
        "--" + boundary + "\r\n"
        "Content-Disposition: form-data; "
        "name=\"image\"; "
        "filename=\"motion.jpg\"\r\n"
        "Content-Type: image/jpeg\r\n\r\n";


    String partFooter =
        "\r\n--" + boundary + "--\r\n";


    size_t contentLength =
        partHeader.length() +
        fb->len +
        partFooter.length();


    /********************************************************
     * HTTP Request Header
     ********************************************************/

    client.printf(
        "POST %s HTTP/1.1\r\n",
        FLASK_ENDPOINT
    );


    client.printf(
        "Host: %s:%d\r\n",
        FLASK_HOST,
        FLASK_PORT
    );


    client.println(
        "Connection: close"
    );


    client.printf(
        "Authorization: Bearer %s\r\n",
        AUTH_TOKEN
    );


    client.printf(
        "X-Node-ID: %s\r\n",
        NODE_ID
    );


    client.println(
        "X-Event: motion"
    );


    /*
     * En futuras versiones puede cambiarse
     * dinámicamente a AI según configuración.
     */

    client.println(
        "X-Processing: RAW"
    );


    client.printf(
        "Content-Type: multipart/form-data; boundary=%s\r\n",
        boundary.c_str()
    );


    client.printf(
        "Content-Length: %u\r\n",
        contentLength
    );


    client.println();


    /********************************************************
     * Envío del cuerpo multipart
     *
     * No se realiza:
     *
     * malloc()
     * memcpy()
     *
     * El JPEG se transmite directamente
     * desde PSRAM.
     ********************************************************/

    client.print(
        partHeader
    );


    size_t sentBytes =
        client.write(
            fb->buf,
            fb->len
        );


    client.print(
        partFooter
    );


    Serial.printf(
        "[EVENT] JPEG sent %u/%u bytes\n",
        sentBytes,
        fb->len
    );


    /********************************************************
     * Leer respuesta HTTP de Flask
     ********************************************************/

    unsigned long start =
        millis();


    while(
        client.connected() &&
        millis() - start < 5000
    )
    {
        while(client.available())
        {
            String line =
                client.readStringUntil('\n');

            Serial.println(line);

            /*
             * Reinicia timeout mientras
             * exista tráfico.
             */
            start = millis();
        }
    }


    client.stop();


    /********************************************************
     * Liberación segura del framebuffer
     *
     * IMPORTANTE:
     * Se libera únicamente después de que
     * la transmisión termina.
     ********************************************************/

    esp_camera_fb_return(
        fb
    );


    unlockCamera();


    Serial.println(
        "[EVENT] Motion completed"
    );


    return true;
}
/************************************************************
 * PARTE 6
 *
 * INICIALIZACIÓN FINAL DEL SISTEMA
 *
 ************************************************************/


/************************************************************
 * SETUP
 ************************************************************/

void setup()
{
    /********************************************************
     * Monitor Serial
     ********************************************************/

    Serial.begin(115200);

    delay(1000);


    Serial.println();
    Serial.println(
        "=================================="
    );

    Serial.println(
        "ESP32-CAM NODE V3 STARTING"
    );

    Serial.println(
        "=================================="
    );


    /********************************************************
     * Configuración GPIO
     ********************************************************/


    /*
     * PIR HC-SR501
     */
    pinMode(
        PIR_PIN,
        INPUT
    );


    /*
     * Flash integrado
     */
    pinMode(
        FLASH_PIN,
        OUTPUT
    );


    /*
     * Estado seguro inicial:
     * flash apagado.
     */
    digitalWrite(
        FLASH_PIN,
        LOW
    );


    flashEnabled = false;


    Serial.println(
        "[INIT] GPIO configured"
    );


    /********************************************************
     * Conexión WiFi
     ********************************************************/

    connectWiFi();


    if(WiFi.status() != WL_CONNECTED)
    {
        Serial.println(
            "[WARNING] WiFi not connected"
        );
    }


    /********************************************************
     * Inicialización de cámara OV2640
     ********************************************************/

    if(!initCamera())
    {
        Serial.println(
            "[FATAL] Camera initialization failed"
        );


        /*
         * Sin cámara no tiene sentido
         * continuar la ejecución.
         */
        while(true)
        {
            delay(1000);
        }
    }


    /********************************************************
     * Registro de rutas REST
     ********************************************************/

    registerRoutes();


    /********************************************************
     * Inicio del servidor HTTP
     ********************************************************/

    server.begin();


    Serial.println(
        "[REST] HTTP server started"
    );


    /********************************************************
     * Inicialización del estado PIR
     *
     * Evita detectar un falso flanco
     * al momento del arranque.
     ********************************************************/

    pirLastState =
        digitalRead(PIR_PIN);


    waitingPirReset = false;


    Serial.println(
        "[PIR] Sensor armed"
    );


    /********************************************************
     * Información del sistema
     ********************************************************/

    Serial.println();
    Serial.println(
        "=========== SYSTEM READY ==========="
    );


    Serial.print(
        "Node ID: "
    );

    Serial.println(
        NODE_ID
    );


    Serial.print(
        "IP Address: "
    );

    Serial.println(
        WiFi.localIP()
    );


    Serial.println(
        "REST API Endpoints:"
    );


    Serial.println(
        "GET  /status"
    );


    Serial.println(
        "GET  /network"
    );


    Serial.println(
        "GET  /capture"
    );


    Serial.println(
        "GET  /capture_flash"
    );


    Serial.println(
        "POST /control"
    );


    Serial.println(
        "==================================="
    );
}



/************************************************************
 * LOOP PRINCIPAL
 *
 * Filosofía:
 *
 * El nodo nunca debe bloquearse esperando eventos.
 *
 * Mantiene:
 *
 * - Control remoto desde Flask.
 * - Captura bajo demanda.
 * - Eventos automáticos PIR.
 * - Supervisión WiFi.
 *
 ************************************************************/


void loop()
{

    /********************************************************
     * Servidor REST
     *
     * Atender:
     *
     * Flask Gateway
     *        |
     *    NodeClient
     *        |
     * /status
     * /network
     * /capture
     * /capture_flash
     * /control
     *
     ********************************************************/

    server.handleClient();


    /********************************************************
     * Mantener conectividad WiFi
     ********************************************************/

    maintainWiFi();


    /********************************************************
     * Gestión de eventos PIR
     ********************************************************/

    checkPIR();


    /********************************************************
     * Pequeño retardo de estabilidad.
     *
     * Reduce carga de CPU sin afectar
     * la capacidad de respuesta.
     ********************************************************/

    delay(5);
}


/************************************************************
 * FIN DEL FIRMWARE
 *
 * ESP32-CAM NODE V3
 *
 * Arquitectura final:
 *
 * Control:
 * POST /control
 *      |
 *      |-- flash_on
 *      |-- flash_off
 *      |-- alert
 *
 * Captura:
 * GET /capture
 * GET /capture_flash
 *
 * Eventos:
 * PIR GPIO14
 *      |
 * POST /api/v1/events/image
 *      |
 * Flask Gateway
 *
 ************************************************************/


 /************************************************************/