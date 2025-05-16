import time
import sqlite3
import re
from RF24 import RF24, RF24_PA_LOW, RF24_1MBPS  

CE_PIN = 22  
CSN_PIN = 0  
db_file = "datos_sensores.db"


radio = RF24(CE_PIN, CSN_PIN)

if not radio.begin():
    exit()

radio.setPALevel(RF24_PA_LOW)
radio.setDataRate(RF24_1MBPS)
radio.setChannel(100)  
radio.openReadingPipe(1, b"00001")
radio.startListening()

def inicializar_bd():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute('''CREATE TABLE IF NOT EXISTS sensores (
                        marca_tiempo TEXT,
                        nodo INTEGER,
                        temperatura REAL,
                        humedad REAL,
                        PRIMARY KEY (marca_tiempo, nodo))''')
    conn.commit()
    conn.close()

def guardar_datos(marca_tiempo, datos_nodos, ultimos_datos):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    for nodo in range(0, 5):  
        if datos_nodos.get(nodo):  
            temperatura, humedad = datos_nodos[nodo]
            ultimos_datos[nodo] = (temperatura, humedad)  
        elif ultimos_datos.get(nodo):  
            temperatura, humedad = ultimos_datos[nodo]
        else:  
            print(f"No hay datos para el nodo {nodo} en la marca de tiempo {marca_tiempo}")
            continue

        cursor.execute("""
            INSERT INTO sensores (marca_tiempo, nodo, temperatura, humedad)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(marca_tiempo, nodo) DO UPDATE SET
            temperatura = excluded.temperatura,
            humedad = excluded.humedad
        """, (marca_tiempo, nodo, temperatura, humedad))

    conn.commit()
    conn.close()
    print(f"Datos guardados en BD para la marca de tiempo: {marca_tiempo}")

inicializar_bd()

datos_nodos = {}  
ultimos_datos = {}  

try:
    while True:
        if radio.available():
            received_text = radio.read(32).decode('utf-8', errors='ignore').strip()
            print(f"Mensaje recibido: {received_text}")

            match = re.search(r"NODO (\d+)\s+T:\s*([\d.]+)\s*C\s+H:\s*([\d.]+)%", received_text)
            if match:
                nodo = int(match.group(1))
                temperatura = float(match.group(2))
                humedad = float(match.group(3))
                datos_nodos[nodo] = (temperatura, humedad)

        tiempo_actual = time.localtime()
        minutos = tiempo_actual.tm_min
        segundos = tiempo_actual.tm_sec

        if minutos % 1 == 0 and segundos == 0:
            marca_tiempo = time.strftime("%Y-%m-%d %H:%M:%S", tiempo_actual)
            guardar_datos(marca_tiempo, datos_nodos, ultimos_datos)
            datos_nodos = {}
            print(f"Esperando datos para el nuevo intervalo...")

        time.sleep(1)

except KeyboardInterrupt:
    print("Finalizando receptor.")
