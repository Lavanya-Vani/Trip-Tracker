#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <Servo.h>


// Gas sensor analog pin
#define MQ5_SENSOR_PIN A0
// Threshold value for gas detection
#define THRESHOLD_VALUE 500 // Adjust as needed
// Servo pin
#define SERVO_PIN D1

/* Put IP Address details */
IPAddress local_ip(192,168,1,1);
IPAddress gateway(192,168,1,1);
IPAddress subnet(255,255,255,0);

// WiFi credentials for AP mode
const char* apSSID = "GasDetector_AP";
const char* apPassword = "12345678";

ESP8266WebServer server(80);

// Create servo object
Servo gasValveServo;

bool is_gas_detected = false;

void setup() {
  Serial.begin(9600);

  gasValveServo.attach(SERVO_PIN);
  pinMode(D0, OUTPUT);
  digitalWrite(D0, HIGH);
  delay(1000);
  digitalWrite(D0, LOW);
  // Set up ESP8266 in AP mode
  WiFi.softAP(apSSID, apPassword);
  WiFi.softAPConfig(local_ip, gateway, subnet);
  //IPAddress apIP = WiFi.softAPIP();
  //Serial.print("Access Point IP address: ");
  //Serial.println(apIP);

  // Set up server routes
  server.on("/", HTTP_GET, []() {
    server.send(200, "text/html", gpage());
  });

  // Start server
  server.begin();
}

void loop() {
  server.handleClient();
}

void close_regulator(){
  gasValveServo.write(0);
}
String gpage(){
  
    if(analogRead(MQ5_SENSOR_PIN)>THRESHOLD_VALUE){
    gasValveServo.attach(D1);
    digitalWrite(D0, HIGH);
    close_regulator();
    is_gas_detected = true;
  }
  else{
    gasValveServo.detach();
    digitalWrite(D0, LOW);
    is_gas_detected = false;
  }
  String page = "<!DOCTYPE html>";
  page += "<html><head><title>Gas Sensor Status</title>";
  page += "<style>";
  page += "body { font-family: Arial, sans-serif; text-align: center; }";
  page += "h1 { color: #333; font-size: 36; }";
  page += "p { font-size: 24px; color: #666; }";
  page += ".lpg-detected { color: red; }";
  page += "</style>";
  page += "</head><body>";
  page += "<h1>Gas Sensor Status</h1>";
  page += "<p>Gas Concentration: " + String(analogRead(MQ5_SENSOR_PIN)) + "</p>\n";
  page += "<script>setTimeout(function(){location.reload();}, 1000);</script>"; // Refresh the page every second
  if(is_gas_detected){
    page+="<p class = 'lpg-detected'>LPG detected. Hurry soon!!</p>";
  }
  else{
    page+="<p>Dont worry. Everything's under control!!</p>";
  }
  page += "</body></html>";
  return page;

}