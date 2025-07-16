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
            if valor == 0:   # Si el GPIO3 está en estado bajo, se considera un evento de conteo
                print("🔔 Evento de conteo detectado en el portal\n" )
                #self.sorteo.incrementa_contador(self.ok)
            time.sleep(0.1)  # Ajusta el tiempo de muestreo según necesida
