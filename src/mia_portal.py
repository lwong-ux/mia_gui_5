import asyncio
import threading
import time
import RPi.GPIO as GPIO

class ManejadorPortal:
    def __init__(self, sorteo):
        self.sorteo = sorteo
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(4, GPIO.IN)  # Configura el GPIO3 como entrada
        self.ok = 0 # Es el índice del arreglo de cajitas para OK

        print("🔔 Manejador de portal inicializado, esperando eventos...\n")
        # Inicia la tarea para muestrear el portal en un hilo separado
        threading.Thread(target=self.muestrea_portal, daemon=True).start()

    def muestrea_portal(self):
        while True:
            valor = GPIO.input(4)
            if valor == 0:
                print("🔔 Evento de conteo detectado en el portal\n")
                # Espera hasta que el valor regrese a 1
                while GPIO.input(4) == 0:
                    time.sleep(0.05)
                # Verifica que se mantenga en 1 durante al menos 2 segundos
                tiempo_estable = time.time()
                while GPIO.input(4) == 1:
                    if time.time() - tiempo_estable >= 2:
                        break
                    time.sleep(0.1)
                else:
                    # Si salió del ciclo sin cumplir los 2 segundos, no cuenta como evento válido
                    continue
                self.sorteo.incrementa_contador(self.ok)
            time.sleep(0.1)
