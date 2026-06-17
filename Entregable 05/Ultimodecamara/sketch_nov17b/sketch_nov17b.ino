#include "esp_camera.h"
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <HTTPClient.h>

// 🔧 PARCHE PARA ERROR DE COMPATIBILIDAD AsyncTCP
uint8_t getAsyncServerStatus(AsyncServer* srv) { return srv->status(); }
#define _fix_async_status(s) getAsyncServerStatus(s)

// ======================= CONFIGURACIÓN DE RED =======================
const char* ssid = "ISABEL_2.4Ghz";
const char* password = "25022002";
const char* TOKEN_ESP32 = "TOKEN_ESP32_ABC123";
bool flashEnabled = false;  // Controla estado del flash
const char* FLASK_URL = "http://192.168.0.5:8080/predict_pir"; // Endpoint Flask PIR

// ======================= SEMÁFORO ====================
SemaphoreHandle_t xRequestBodyMutex;
String requestBody = "";

// ======================= CONFIGURACIÓN DE CÁMARA ====================
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
#define FLASH_GPIO_NUM     4
#define FLASH_SAFE_PIN    33 

// ======================= SERVIDOR ======================
AsyncWebServer server(80);

// ======================= PIR SENSOR ====================
#define PIR_PIN 13            // PIN donde conectaste el PIR

// =======================================================
// FUNCIONES CÁMARA
// =======================================================
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 15;
    config.fb_count = 1;
  }

  delay(200);
  esp_err_t err = esp_camera_init(&config);
  delay(200);
  if (err != ESP_OK) {
    Serial.printf("❌ Error cámara: 0x%x - %s\n", err, esp_err_to_name(err));
    return false;
  }

  camera_fb_t *test_fb = esp_camera_fb_get();
  if (!test_fb) return false;
  esp_camera_fb_return(test_fb);
  return true;
}

// =======================================================
// CONTROL FLASH
// =======================================================
void setupFlash() {
  pinMode(FLASH_SAFE_PIN, OUTPUT);
  digitalWrite(FLASH_SAFE_PIN, LOW);
  pinMode(FLASH_GPIO_NUM, OUTPUT);
  digitalWrite(FLASH_GPIO_NUM, LOW);
}

void flashOn() { digitalWrite(FLASH_GPIO_NUM, HIGH); digitalWrite(FLASH_SAFE_PIN, HIGH); }
void flashOff() { digitalWrite(FLASH_GPIO_NUM, LOW); digitalWrite(FLASH_SAFE_PIN, LOW); }

// =======================================================
// ALERTA FLASH
// =======================================================
void activarAlerta() {
  for (int i = 0; i < 5; i++) {
    digitalWrite(FLASH_GPIO_NUM, HIGH); delay(150);
    digitalWrite(FLASH_GPIO_NUM, LOW);  delay(150);
  }
}

// =======================================================
// CAPTURA FOTO (BÁSICA)
// =======================================================
void enviarFoto(AsyncWebServerRequest *request) {
  int heap_antes = ESP.getFreeHeap();
  if (heap_antes < 60000) { request->send(503, "application/json", "{\"error\":\"memoria_baja\"}"); return; }

  camera_fb_t *old = esp_camera_fb_get();
  if (old) esp_camera_fb_return(old);
  delay(40);

  const int MAX_INTENTOS = 4;
  unsigned long inicio = millis();
  camera_fb_t *fb = NULL;
  bool ok = false;

  for (int i = 0; i < MAX_INTENTOS && (millis()-inicio) < 2500; i++) {
    fb = esp_camera_fb_get();
    if (fb && fb->len > 2000) { ok = true; break; }
    if (fb) esp_camera_fb_return(fb);
    fb = NULL;
    delay(120);
  }

  if (!ok || !fb) { request->send(500, "application/json", "{\"error\":\"capture_failed\"}"); return; }

  AsyncWebServerResponse *response = request->beginResponse(
    "image/jpeg", fb->len,
    [fb](uint8_t *buffer, size_t maxLen, size_t index) -> size_t {
      if (index >= fb->len) { esp_camera_fb_return(fb); return 0; }
      size_t toSend = (index + maxLen > fb->len) ? fb->len - index : maxLen;
      memcpy(buffer, fb->buf + index, toSend);
      if (index + toSend >= fb->len) esp_camera_fb_return(fb);
      return toSend;
    }
  );

  response->addHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  request->send(response);
}

// =======================================================
// CAPTURA FOTO CON FLASH / SIN FLASH
// =======================================================
void capturarFotoSeguro(AsyncWebServerRequest *request, bool usarFlash) {
  if (usarFlash) flashOn();
  delay(usarFlash ? 180 : 0);

  const int MAX_INTENTOS = 4;
  camera_fb_t *fb = NULL;
  bool ok = false;

  for (int i = 0; i < MAX_INTENTOS; i++) {
    fb = esp_camera_fb_get();
    if (fb && fb->len > 2000) { ok = true; break; }
    if (fb) esp_camera_fb_return(fb);
    fb = NULL;
    delay(120);
  }

  if (!ok || !fb) { if (usarFlash) flashOff(); request->send(500,"application/json","{\"error\":\"capture_failed\"}"); return; }
  if (usarFlash) flashOff();

  AsyncWebServerResponse *response = request->beginResponse(
    "image/jpeg", fb->len,
    [fb](uint8_t *buffer, size_t maxLen, size_t index) -> size_t {
      if (index >= fb->len) { esp_camera_fb_return(fb); return 0; }
      size_t toSend = (index + maxLen > fb->len) ? fb->len - index : maxLen;
      memcpy(buffer, fb->buf + index, toSend);
      if (index + toSend >= fb->len) esp_camera_fb_return(fb);
      return toSend;
    }
  );

  response->addHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  request->send(response);
}

// =======================================================
// TOKEN
// =======================================================
bool validarToken(AsyncWebServerRequest *req) {
  if (req->hasHeader("Authorization")) {
    String authHeader = req->getHeader("Authorization")->value();
    if (authHeader.startsWith("Bearer ")) {
      String token = authHeader.substring(7); token.trim();
      return token == TOKEN_ESP32;
    }
  }
  return false;
}

// =======================================================
// REQUEST BODY
// =======================================================
void setRequestBody(const String& body) { if (xSemaphoreTake(xRequestBodyMutex, portMAX_DELAY)) { requestBody = body; xSemaphoreGive(xRequestBodyMutex); } }
String getRequestBody() { String body=""; if (xSemaphoreTake(xRequestBodyMutex, portMAX_DELAY)) { body=requestBody; xSemaphoreGive(xRequestBodyMutex); } return body; }
void clearRequestBody() { if (xSemaphoreTake(xRequestBodyMutex, portMAX_DELAY)) { requestBody=""; xSemaphoreGive(xRequestBodyMutex); } }

// =======================================================
// EXTRAER COMANDO JSON
// =======================================================
String extraerComandoDelJSON(String jsonString) {
  int cmdIndex = jsonString.indexOf("\"cmd\"");
  if (cmdIndex == -1) cmdIndex = jsonString.indexOf("\"command\"");
  if (cmdIndex != -1) {
    int colonIndex = jsonString.indexOf(":", cmdIndex);
    int quoteStart = jsonString.indexOf("\"", colonIndex);
    int quoteEnd = jsonString.indexOf("\"", quoteStart+1);
    if (quoteEnd != -1) return jsonString.substring(quoteStart+1, quoteEnd);
  }
  return "";
}

// =======================================================
// FUNCION PARA ENVIAR FOTO AL FLASK CON PIR
// =======================================================
bool enviarFotoPIR(camera_fb_t *fb) {
  if (!fb) return false;

  WiFiClient client;
  HTTPClient http;
  http.begin(client, FLASK_URL);
  http.addHeader("Authorization", "Bearer " + String(TOKEN_ESP32));

  String boundary = "----ESP32CAM12345";
  String head = "--" + boundary + "\r\n"
                "Content-Disposition: form-data; name=\"image\"; filename=\"foto.jpg\"\r\n"
                "Content-Type: image/jpeg\r\n\r\n";
  String tail = "\r\n--" + boundary + "--\r\n";

  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

  int totalLength = head.length() + fb->len + tail.length();
  uint8_t *body = new uint8_t[totalLength];
  memcpy(body, head.c_str(), head.length());
  memcpy(body + head.length(), fb->buf, fb->len);
  memcpy(body + head.length() + fb->len, tail.c_str(), tail.length());
  Serial.print("Enviando token: "); Serial.println(TOKEN_ESP32);

  int httpCode = http.sendRequest("POST", body, totalLength);

  delete[] body;
  http.end();

  if (httpCode > 0) Serial.printf("⚡ Movimiento detectado! Foto enviada, respuesta: %d\n", httpCode);
  else Serial.println("❌ Error enviando foto PIR");

  return httpCode == 200 || httpCode == 201;
}

// =======================================================
// SERVIDOR HTTP
// =======================================================
void startServer() {
  server.on("/status", HTTP_GET, [](AsyncWebServerRequest *req){ req->send(200, "application/json", "{\"status\":\"online\"}"); });
  server.on("/capture", HTTP_GET, [](AsyncWebServerRequest *req){ enviarFoto(req); });

  server.on("/command", HTTP_POST, [](AsyncWebServerRequest *req){
    if (!validarToken(req)) { req->send(403,"application/json","{\"error\":\"token inválido\"}"); return; }

    String cmd = "";
    String bodyContent = getRequestBody();
    if (req->hasParam("cmd", true)) cmd = req->getParam("cmd", true)->value();
    else if (bodyContent.length()>0) cmd = extraerComandoDelJSON(bodyContent);
    clearRequestBody();
    cmd.trim();

    if (cmd=="status") req->send(200,"application/json","{\"status\":\"activo\"}");
    else if(cmd=="alert"){activarAlerta(); req->send(200,"application/json","{\"status\":\"alerta activada\"}");}
    else if(cmd=="reboot"){req->send(200,"application/json","{\"status\":\"reiniciando\"}"); delay(1000); ESP.restart();}
    else if(cmd=="photo_with_flash") capturarFotoSeguro(req,true);
    else if(cmd=="photo") capturarFotoSeguro(req,false);
    else if(cmd=="flash_on"){ flashOn(); flashEnabled=true; req->send(200,"application/json","{\"status\":\"flash encendido\"}"); }
    else if(cmd=="flash_off"){ flashOff(); flashEnabled=false; req->send(200,"application/json","{\"status\":\"flash apagado\"}"); }
    else req->send(400,"application/json","{\"error\":\"comando desconocido: "+cmd+"\"}");
  });

  server.onRequestBody([](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total){
    if(request->url()=="/command" && request->method()==HTTP_POST && index==0 && total>0 && total<4096){
      String body=""; for(size_t i=0;i<len;i++) body+=(char)data[i];
      setRequestBody(body);
    }
  });

  server.begin();
}

// =======================================================
// SETUP & LOOP
// =======================================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  xRequestBodyMutex = xSemaphoreCreateMutex();
  setupFlash();

  if(!initCamera()){ Serial.println("❌ Error inicialización cámara"); delay(2000); ESP.restart(); }

  WiFi.begin(ssid,password);
  unsigned long start = millis();
  while(WiFi.status()!=WL_CONNECTED && millis()-start<20000){ delay(500); Serial.print("."); }
  Serial.println(); Serial.print("IP: "); Serial.println(WiFi.localIP());

  pinMode(PIR_PIN, INPUT);  // Inicializamos PIR
  startServer();
}

void loop() {
  delay(1000);

  // ================= PIR SENSOR =================
  static unsigned long lastTrigger = 0;
  if (digitalRead(PIR_PIN) == HIGH && millis() - lastTrigger > 2000) { // evita envíos consecutivos
    camera_fb_t *fb = esp_camera_fb_get();
    if (fb) {
      enviarFotoPIR(fb);       // enviar foto al servidor Flask
      esp_camera_fb_return(fb); // liberar frame
      lastTrigger = millis();
    }
  }
}
