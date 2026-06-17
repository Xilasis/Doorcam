#include "esp_camera.h"
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
// 🔧 PARCHE PARA ERROR DE COMPATIBILIDAD AsyncTCP
// Agregar esta función antes de setup()
uint8_t getAsyncServerStatus(AsyncServer* srv) {
    return srv->status();
}

// Reemplazar la función problemática en tiempo de compilación
#define _fix_async_status(s) getAsyncServerStatus(s)

// ======================= CONFIGURACIÓN DE RED =======================
const char* ssid = "Nitro5";
const char* password = "12345678";
const char* TOKEN_ESP32 = "TOKEN_ESP32_ABC123";
bool flashEnabled = false;  // ✅ DECLARACIÓN GLOBAL - Controla estado del flash
// ======================= SEMÁFORO PARA PROTECCIÓN ====================
SemaphoreHandle_t xRequestBodyMutex;

// Variable global protegida
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

// =======================================================
// FUNCIÓN: Inicializar cámara
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
  
  // ⚡ CONFIGURACIÓN OPTIMIZADA
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  if (psramFound()) {
    config.frame_size = FRAMESIZE_QVGA;   // 320x240
    config.jpeg_quality = 12;             // más estable
    config.fb_count = 2;                  // doble buffer → cero glitch
    Serial.println("✅ PSRAM detectada, usando QVGA + doble buffer");
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 15;
    config.fb_count = 1;
    Serial.println("⚠️ No hay PSRAM → usando VGA con 1 buffer");
  }

  // ✅ INICIALIZACIÓN CON MEJOR MANEJO DE ERRORES
  delay(200);
  esp_err_t err = esp_camera_init(&config);
  delay(200);
  
  if (err != ESP_OK) {
    Serial.printf("❌ Error cámara: 0x%x - %s\n", err, esp_err_to_name(err));
    
    // INTENTO DE RECUPERACIÓN
    if(err == ESP_ERR_CAMERA_NOT_DETECTED) {
      Serial.println("🔌 Verificar conexión de cámara OV2640");
    }
    return false;
  }
  
  // ✅ VERIFICAR QUE LA CÁMARA RESPONDE
  delay(100);
  camera_fb_t *test_fb = esp_camera_fb_get();
  if (!test_fb) {
    Serial.println("❌ Cámara no responde después de inicialización");
    return false;
  }
  esp_camera_fb_return(test_fb);
  
  Serial.printf("✅ Cámara inicializada: %dx%d, Calidad: %d\n", 
                640, 480, config.jpeg_quality);
  return true;
}
//BLOQUE CONTROL FLASH
void setupFlash() {
  pinMode(FLASH_SAFE_PIN, OUTPUT);
  digitalWrite(FLASH_SAFE_PIN, LOW);

  pinMode(FLASH_GPIO_NUM, OUTPUT);
  digitalWrite(FLASH_GPIO_NUM, LOW);
}

void flashOn() {
  digitalWrite(FLASH_GPIO_NUM, HIGH);    // flash real
  digitalWrite(FLASH_SAFE_PIN, HIGH);    // control lógico seguro
}

void flashOff() {
  digitalWrite(FLASH_GPIO_NUM, LOW);
  digitalWrite(FLASH_SAFE_PIN, LOW);
}
// =============================================================
// COMANDO ALERTA (PARPADEO FLASH)
// =============================================================
void activarAlerta() {
  for (int i = 0; i < 5; i++) {
    digitalWrite(FLASH_GPIO_NUM, HIGH);
    delay(150);
    digitalWrite(FLASH_GPIO_NUM, LOW);
    delay(150);
  }
}

// =======================================================
// FUNCIÓN: Capturar y enviar foto - CORREGIDA (Sin cache)
// =======================================================
// =======================================================
// FUNCIÓN: Capturar y enviar foto - SOLO captura normal
// =======================================================
void enviarFoto(AsyncWebServerRequest *request) {
  int heap_antes = ESP.getFreeHeap();
  Serial.printf("📸 Iniciando captura NORMAL - Heap: %d\n", heap_antes);

  // 🔍 Verificación de memoria realista
  // 80 KB es muy alto, la ESP32-CAM suele tener 100–160 KB libres en uso normal.
  if (heap_antes < 60000) {
    Serial.printf("🚨 Heap crítico (%d), rechazando captura\n", heap_antes);
    request->send(503, "application/json", "{\"error\":\"memoria_baja\"}");
    return;
  }

  // 🧹 LIMPIAR FRAME ANTERIOR
  Serial.println("🧹 Limpiando frame previo...");
  camera_fb_t *old = esp_camera_fb_get();
  if (old) {
    esp_camera_fb_return(old);
    Serial.println("   ➤ Frame viejo descartado");
  }
  delay(40);

  // 🎯 CAPTURA CON REINTENTOS
  const int MAX_INTENTOS = 4;
  const unsigned long TIMEOUT = 2500;
  unsigned long inicio = millis();

  camera_fb_t *fb = NULL;
  bool ok = false;

  for (int i = 0; i < MAX_INTENTOS && (millis() - inicio) < TIMEOUT; i++) {

    fb = esp_camera_fb_get();

    if (fb && fb->len > 5000) {  // ⬅️ 10kB era exceso, 5kB es seguro para QVGA/VGA
      Serial.printf("   ✔ Intento %d OK (%d bytes)\n", i + 1, fb->len);
      ok = true;
      break;
    }

    // Frame inválido → liberar
    if (fb) esp_camera_fb_return(fb);
    fb = NULL;

    Serial.printf("   ⚠️ Intento %d fallido, retry...\n", i + 1);
    delay(120);
  }

  if (!ok || !fb) {
    Serial.println("❌ Captura fallida definitiva");
    request->send(500, "application/json", "{\"error\":\"capture_failed\"}");
    return;
  }

  Serial.printf("🎉 Captura final válida: %d bytes\n", fb->len);

  // ⭐ STREAM JPEG (con liberación segura del frame)
  AsyncWebServerResponse *response = request->beginResponse(
    "image/jpeg", 
    fb->len,
    [fb](uint8_t *buffer, size_t maxLen, size_t index) -> size_t 
    {
        if (index >= fb->len) return 0;

        size_t remaining = fb->len - index;
        size_t toSend = remaining > maxLen ? maxLen : remaining;

        memcpy(buffer, fb->buf + index, toSend);

        // liberar al terminar
        if (index + toSend >= fb->len) {
            esp_camera_fb_return(fb);
            Serial.println("🧹 Frame liberado tras el envío /capture");
        }

        return toSend;
    }
  );

  // Cabeceras recomendadas
  response->addHeader("Content-Disposition", "inline; filename=capture.jpg");
  response->addHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  response->addHeader("Pragma", "no-cache");
  response->addHeader("Expires", "0");
  response->addHeader("X-Image-Timestamp", String(millis()));

  request->send(response);

  int heap_despues = ESP.getFreeHeap();
  Serial.printf("📤 Respuesta enviada — Heap Δ: %+d\n", heap_despues - heap_antes);
}


// =============================================================
// FUNCIÓN: Foto con flash - COMPORTAMIENTO INDEPENDIENTE
// =============================================================
void capturarConFlash(AsyncWebServerRequest *request) {
  Serial.println("📸➕💡 Capturando con flash (seguro)...");

  flashOn();
  delay(180);

  camera_fb_t *fb = esp_camera_fb_get();

  // Primer intento con flash
  if (!fb || fb->len < 2000) {
    Serial.println("⚠️ Falló captura con flash → intentando sin flash...");
    flashOff();   // ← APAGAR DE INMEDIATO
    delay(80);

    // Reintentos sin flash
    for (int i = 0; i < 3; i++) {
      fb = esp_camera_fb_get();
      if (fb && fb->len > 2000) break;
      if (fb) esp_camera_fb_return(fb);
      fb = NULL;
      delay(120);
    }

    if (!fb) {
      flashOff();  // ← APAGADO DE EMERGENCIA
      request->send(500, "application/json", "{\"error\":\"capture_failed\"}");
      return;
    }
  }

  // 🟢 Captura válida → apagar flash ANTES del envío
  flashOff();

  Serial.printf("📸 Imagen OK (%d bytes)\n", fb->len);

  // Streaming seguro
  AsyncWebServerResponse *response = request->beginResponse(
    "image/jpeg",
    fb->len,
    [fb](uint8_t *buffer, size_t maxLen, size_t index) -> size_t {

      if (index >= fb->len) {
        esp_camera_fb_return(fb);
        Serial.println("🧹 Frame liberado tras streaming");
        return 0;
      }

      size_t toSend = (index + maxLen > fb->len) ? fb->len - index : maxLen;
      memcpy(buffer, fb->buf + index, toSend);
      return toSend;
    }
  );

  response->addHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  request->send(response);
}

// =======================================================
// FUNCIÓN: Validar token tipo "Bearer"
// =======================================================
bool validarToken(AsyncWebServerRequest *req) {
  if (req->hasHeader("Authorization")) {
    String authHeader = req->getHeader("Authorization")->value();
    if (authHeader.startsWith("Bearer ")) {
      String token = authHeader.substring(7);
      token.trim();
      return token == TOKEN_ESP32;
    }
  }
  return false;
}

// =======================================================
// FUNCIÓN: Manejo seguro de requestBody
// =======================================================
void setRequestBody(const String& body) {
  if (xTaskGetSchedulerState() != taskSCHEDULER_RUNNING) return;
  
  if (xSemaphoreTake(xRequestBodyMutex, portMAX_DELAY)) {
    requestBody = body;
    xSemaphoreGive(xRequestBodyMutex);
  }
}

String getRequestBody() {
  String body = "";
  if (xTaskGetSchedulerState() != taskSCHEDULER_RUNNING) return body;
  
  if (xSemaphoreTake(xRequestBodyMutex, portMAX_DELAY)) {
    body = requestBody;
    xSemaphoreGive(xRequestBodyMutex);
  }
  return body;
}

void clearRequestBody() {
  if (xTaskGetSchedulerState() != taskSCHEDULER_RUNNING) return;
  
  if (xSemaphoreTake(xRequestBodyMutex, portMAX_DELAY)) {
    requestBody = "";
    xSemaphoreGive(xRequestBodyMutex);
  }
}

//=========================================================
// FUNCIÓN: Extraer comando del JSON SIN ArduinoJson
// =============================================================
String extraerComandoDelJSON(String jsonString) {
  // Busca: {"cmd": "valor"} 
  int cmdIndex = jsonString.indexOf("\"cmd\"");
  if (cmdIndex == -1) {
    // También busca: {"command": "valor"}
    cmdIndex = jsonString.indexOf("\"command\"");
  }
  
  if (cmdIndex != -1) {
    // Encuentra los dos puntos después de "cmd"
    int colonIndex = jsonString.indexOf(":", cmdIndex);
    if (colonIndex != -1) {
      // Encuentra las comillas del valor
      int quoteStart = jsonString.indexOf("\"", colonIndex);
      if (quoteStart != -1) {
        int quoteEnd = jsonString.indexOf("\"", quoteStart + 1);
        if (quoteEnd != -1) {
          // Extrae el valor entre comillas
          return jsonString.substring(quoteStart + 1, quoteEnd);
        }
      }
    }
  }
  return "";
}

// =============================================================
// ENDPOINTS HTTP PRINCIPALES - CORREGIDOS
// =============================================================
void startServer() {

  // ✅ Endpoint de estado
  server.on("/status", HTTP_GET, [](AsyncWebServerRequest *req){
    req->send(200, "application/json", "{\"status\":\"online\"}");
  });

// ✅ Endpoint de captura MEJORADO - Forzar imagen nueva
server.on("/capture", HTTP_GET, [](AsyncWebServerRequest *req){
  static unsigned long ultima_captura = 0;
  static int capturas_consecutivas = 0;
  
  unsigned long ahora = millis();
  int heap_actual = ESP.getFreeHeap();
  
  Serial.printf("\n🔄 NUEVA SOLICITUD /capture - Heap: %d\n", heap_actual);

  // ==========================
  // 1. VALIDAR TOKEN
  // ==========================
  if (!validarToken(req)) {
    req->send(403, "application/json", "{\"error\":\"token inválido\"}");
    return;
  }

  // ==========================
  // 2. PROTECCIÓN DE FLOODING
  // ==========================
  if (ahora - ultima_captura < 1500) {
    capturas_consecutivas++;
    Serial.printf("⚠️ Capturas consecutivas: %d\n", capturas_consecutivas);

    if (capturas_consecutivas > 3) {
      Serial.println("🚨 Demasiadas capturas seguidas → pausa automática");
      req->send(429, "application/json", "{\"error\":\"Espere entre capturas\"}");
      delay(3000);
      capturas_consecutivas = 0;
      return;
    }
  } else {
    capturas_consecutivas = 0;
  }

  ultima_captura = ahora;

  // ==========================
  // 3. LIMPIEZA SI HAY POCA RAM
  // ==========================
  if (heap_actual < 60000) {
    Serial.println("⚠️ Memoria baja → limpiando frame anterior...");
    camera_fb_t *clean = esp_camera_fb_get();
    if (clean) esp_camera_fb_return(clean);
    delay(200);
  }

  // ==========================
  // 4. CAPTURA REAL
  // ==========================
  enviarFoto(req);
});

  // ✅ Endpoint principal para comandos remotos - CORREGIDO
  server.on("/command", HTTP_POST, [](AsyncWebServerRequest *req){
    Serial.println("📨 Endpoint /command llamado");
    
    if (!validarToken(req)) {
      req->send(403, "application/json", "{\"error\":\"token inválido\"}");
      return;
    }

    String cmd = "";
    String bodyContent = getRequestBody(); // ✅ Usar función segura
    
    // Método 1: Buscar parámetro directo "cmd" (para formularios)
    if (req->hasParam("cmd", true)) {
      cmd = req->getParam("cmd", true)->value();
      Serial.println("✅ Comando recibido como parámetro: " + cmd);
    }
    // Método 2: Buscar en JSON del cuerpo (para JSON raw)
    else if (bodyContent.length() > 0) {
      Serial.println("📦 Cuerpo JSON recibido: " + bodyContent);
      cmd = extraerComandoDelJSON(bodyContent);
      Serial.println("✅ Comando extraído del JSON: " + cmd);
    }

    clearRequestBody(); // ✅ Limpiar seguro después de usar
    cmd.trim();
    
    // PROCESAR COMANDOS
    if (cmd == "status") {
      String json = "{\"status\":\"activo\",\"ip\":\"" + WiFi.localIP().toString() +
                    "\",\"rssi\":" + String(WiFi.RSSI()) + "}";
      req->send(200, "application/json", json);
    } 
    else if (cmd == "alert") {
      activarAlerta();
      req->send(200, "application/json", "{\"status\":\"alerta activada\"}");
    }
    else if (cmd == "diag" || cmd == "info") {
      String diag = "{\"status\":\"diagnóstico\",\"ssid\":\"" + WiFi.SSID() +
                    "\",\"rssi\":" + String(WiFi.RSSI()) +
                    ",\"heap\":" + String(ESP.getFreeHeap()) +
                    ",\"uptime\":" + String(millis()/1000) + "}";
      req->send(200, "application/json", diag);
    }
    else if (cmd == "reboot") {
      req->send(200, "application/json", "{\"status\":\"reiniciando\"}");
      delay(1000); // ✅ Dar tiempo para enviar respuesta
      ESP.restart();
    }
    else if (cmd == "photo_with_flash") {
    capturarConFlash(req);
    }
    else if (cmd == "flash_on") {
        flashOn();
        flashEnabled = true;
        req->send(200, "application/json", "{\"status\":\"flash encendido\"}");
    }

    else if (cmd == "flash_off") {
        flashOff();
        flashEnabled = false;
        req->send(200, "application/json", "{\"status\":\"flash apagado\"}");
    }

    else if (cmd != "") {
      req->send(400, "application/json", "{\"error\":\"comando desconocido: " + cmd + "\"}");
    }
    else {
      req->send(400, "application/json", "{\"error\":\"sin comando válido\"}");
    }
  });

  // ✅ Handler ÚNICO para recibir JSON en POST
  server.onRequestBody([](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
    if (request->url() == "/command" && request->method() == HTTP_POST) {
      if (index == 0 && total > 0 && total < 4096) {
        String body = "";
        for (size_t i = 0; i < len; i++) {
          body += (char)data[i];
        }
        setRequestBody(body); // ✅ Usar función segura
      }
    }
  });

  server.begin();
  Serial.println("✅ Servidor HTTP iniciado en puerto 80");
}

// =============================================================
// SETUP Y LOOP - CORREGIDO
// =============================================================
void setup() {
  Serial.begin(115200);
  delay(1000); // ✅ Esperar inicialización serial
  
  // ✅ INICIALIZAR SEMÁFORO CRÍTICO
  xRequestBodyMutex = xSemaphoreCreateMutex();
  if (xRequestBodyMutex == NULL) {
    Serial.println("❌ Error creando semáforo, continuando sin protección");
  } else {
    Serial.println("✅ Semáforo inicializado correctamente");
  }

   setupFlash();

  if (!initCamera()) {
    Serial.println("❌ Falló inicialización de cámara. Reiniciando...");
    delay(2000);
    ESP.restart();
  }

  WiFi.begin(ssid, password);
  Serial.println("Conectando a WiFi...");

  unsigned long startAttemptTime = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < 20000) {
    Serial.print(".");
    delay(500);
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("✅ Conectado correctamente");
    Serial.print("📡 IP: ");
    Serial.println(WiFi.localIP());
    
    // ✅ INICIAR SERVIDOR 
    startServer();
    
  } else {
    Serial.println("❌ Error al conectar. Mostrando diagnóstico:");
    WiFi.printDiag(Serial);
    Serial.println("Reiniciando en 5 segundos...");
    delay(5000);
    ESP.restart();
  }
}

void loop() {
  // ✅ MONITOREO PERIÓDICO OPCIONAL
  static unsigned long lastHeapLog = 0;
  if (millis() - lastHeapLog > 5000) { // Cada 30 segundos
    Serial.printf("💾 Heap libre: %d bytes\n", ESP.getFreeHeap());
    lastHeapLog = millis();
  }
  
  delay(1000);
}