import serial
import re
import sys

# Detecta si es una Raspberry Pi
def es_raspberry_pi():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
        return 'Raspberry' in cpuinfo or 'BCM' in cpuinfo
    except Exception:
        return False

ES_RPI = es_raspberry_pi()
if ES_RPI:
    PORT = "/dev/ttyUSB0"
    print("\nRaspberry Pi detectada...\n")
else:
	PORT = "/dev/cu.usbserial-210"
	print("\nSe asigna puerto serial de Mac...\n")
BAUD = 9600

ser = serial.Serial(PORT, BAUD, timeout=1)
print("Leyendo US Solid")
try:
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if line:
            #print("US Solid ", line)
            match = re.search(r"(-?\d+\.\d+)", line)
            if match:
                weight = float(match.group(1))
                # Escribe en la misma línea y fuerza el flush
                sys.stdout.write(f"\rPeso detectado: {weight:6.1f} g")
                sys.stdout.flush()
except KeyboardInterrupt:
    # Deja el prompt en nueva línea al salir
    print()
finally:
    ser.close()