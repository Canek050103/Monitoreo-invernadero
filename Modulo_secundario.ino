#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>
#include <Wire.h>
#include <Adafruit_HTU21DF.h>

#define CE_PIN 2
#define CSN_PIN 15
#define NODE_ID 1  //  CAMBIAR PARA CADA ESP32

RF24 radio(CE_PIN, CSN_PIN);
Adafruit_HTU21DF htu;

const byte address[6] = "1Node";  

bool antennaConnected = false;
bool htuConnected = false;

#pragma pack(1)
struct DataPacket {
    uint8_t id;
    float temperatura;
    float humedad;
    bool antenaEstado;
};
#pragma pack()

void setup() {
    Serial.begin(115200);
    SPI.begin(18, 19, 23);

    htuConnected = htu.begin();
    if (!htuConnected) {
        Serial.println("Error al iniciar el sensor HTU21.");
    }

    iniciarNRF24();
}

void iniciarNRF24() {
    antennaConnected = radio.begin();
    if (antennaConnected) {
        Serial.println("NRF24L01 iniciado correctamente.");
        radio.openWritingPipe(address);
        radio.setChannel(76);
        radio.setPALevel(RF24_PA_LOW);
        radio.setDataRate(RF24_250KBPS);
        radio.stopListening();
    } else {
        Serial.println("Error al iniciar NRF24L01.");
    }
}

void loop() {
    if (!radio.isChipConnected()) {
        Serial.println("NRF24L01 desconectado. Intentando reconectar...");
        iniciarNRF24();
    }

    float temperature = htuConnected ? htu.readTemperature() : 0.0;
    float humidity = htuConnected ? htu.readHumidity() : 0.0;

    DataPacket data;
    data.id = NODE_ID;
    data.temperatura = temperature;
    data.humedad = humidity;
    data.antenaEstado = antennaConnected;

    if (antennaConnected) {
        bool sent = radio.write(&data, sizeof(data));
        if (sent) {
            Serial.println("Datos enviados correctamente.");
        } else {
            Serial.println("Error al enviar los datos.");
            antennaConnected = false;
        }
    }

    Serial.print("Nodo: ");
    Serial.println(NODE_ID);
    Serial.print("Temperatura: ");
    Serial.print(temperature);
    Serial.println(" C");
    Serial.print("Humedad: ");
    Serial.print(humidity);
    Serial.println(" %");

    delay(2000);
}
