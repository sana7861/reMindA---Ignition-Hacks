#include <WebServer.h>
#include <WiFi.h>
#include <esp32cam.h>

const char* WIFI_SSID = "";      // Replace with your WiFi SSID
const char* WIFI_PASS = "";  // Replace with your WiFi password

WebServer server(80);

static auto loRes = esp32cam::Resolution::find(320, 240);
static auto midRes = esp32cam::Resolution::find(350, 530);
static auto hiRes = esp32cam::Resolution::find(800, 600);

void setup() {
  Serial.begin(115200);
  Serial.println();

  // Initialize the camera
  {
    using namespace esp32cam;
    Config cfg;
    cfg.setPins(pins::AiThinker);
    cfg.setResolution(hiRes);  // Set the initial resolution
    cfg.setBufferCount(2);
    cfg.setJpeg(80);

    bool ok = Camera.begin(cfg);
    Serial.println(ok ? "CAMERA OK" : "CAMERA FAIL");
    if (!ok) {
      // Restart ESP32 if the camera initialization fails
      ESP.restart();
    }
  }

  // Connect to WiFi
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  // Wait for the WiFi connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.print("Connected to WiFi. IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.println("Access camera streams:");
  Serial.println("  /cam-lo.jpg");
  Serial.println("  /cam-hi.jpg");
  Serial.println("  /cam-mid.jpg");

  // Set up HTTP server routes
  server.on("/cam-lo.jpg", []() {
    if (!esp32cam::Camera.changeResolution(loRes)) {
      Serial.println("SET-LO-RES FAIL");
    }
    serveJpg();
  });

  server.on("/cam-hi.jpg", []() {
    if (!esp32cam::Camera.changeResolution(hiRes)) {
      Serial.println("SET-HI-RES FAIL");
    }
    serveJpg();
  });

  server.on("/cam-mid.jpg", []() {
    if (!esp32cam::Camera.changeResolution(midRes)) {
      Serial.println("SET-MID-RES FAIL");
    }
    serveJpg();
  });

  server.begin();
}

void loop() {
  server.handleClient();
}

void serveJpg() {
  auto frame = esp32cam::capture();
  if (frame == nullptr) {
    Serial.println("CAPTURE FAIL");
    server.send(503, "", "");
    return;
  }
  Serial.printf("CAPTURE OK %dx%d %db\n", frame->getWidth(), frame->getHeight(),
                static_cast<int>(frame->size()));

  server.setContentLength(frame->size());
  server.send(200, "image/jpeg");
  WiFiClient client = server.client();
  frame->writeTo(client);
}
