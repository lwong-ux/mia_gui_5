import asyncio
import threading
import time
import sys
import os

OK_SENSOR = 2   # Número del pin BCM para sensar ok
OK_LED = 17     # Número del pin BCM para led ok
OK_INDICE = 0   # Índice en el arreglo de cajitas para ok
NG_SENSOR = 3   # Número del pin GPIO según BCM para sensar ng
NG_LED = 27     # Número del pin GPIO según BCM para led ng
NG_INDICE = 6   # Índice en el arreglo de cajitas para ng mix

class ManejadorPortal:
    def __init__(self, sorteo, es_rpi):
        self.sorteo = sorteo
        self.es_pi = es_rpi

        if self.es_pi:
            import RPi.GPIO as GPIO  # Importar RPi.GPIO dentro del constructor
            self.GPIO = GPIO
            # Configuración de los GPIOs
            self.GPIO.cleanup()
            self.GPIO.setmode(self.GPIO.BCM)
            self.GPIO.setup(OK_SENSOR, self.GPIO.IN, pull_up_down=self.GPIO.PUD_UP)
            self.GPIO.setup(NG_SENSOR, self.GPIO.IN, pull_up_down=self.GPIO.PUD_UP)
            self.GPIO.setup(OK_LED, self.GPIO.OUT)
            self.GPIO.setup(NG_LED, self.GPIO.OUT)
            self.GPIO.output(OK_LED, True)
            self.GPIO.output(NG_LED, True)
            print("🔔 Manejador de portal inicializado, esperando eventos...\n")
            time.sleep(1)  # Espera un poco para estabilizar los GPIOs

            # Registra las interrupciones por flanco de bajada
            self.GPIO.add_event_detect(OK_SENSOR, self.GPIO.FALLING, callback=self._callback_ok, bouncetime=200)
            self.GPIO.add_event_detect(NG_SENSOR, self.GPIO.FALLING, callback=self._callback_ng, bouncetime=200)
        else:
            print("⚠️  No es Raspberry Pi: ManejadorPortal se inicializa sin GPIO.")

    def _callback_ok(self, channel):
        if self.sorteo.gui.tipo_conteo_ir.get() == 1:
            if self._confirma_evento(OK_SENSOR, OK_LED):
                self.sorteo.incrementa_contador(OK_INDICE,1)

    def _callback_ng(self, channel):
        if self.sorteo.gui.tipo_conteo_ir.get() == 1:
            if self._confirma_evento(NG_SENSOR, NG_LED):
                self.sorteo.incrementa_contador(NG_INDICE,1)

    def _confirma_evento(self, sensor, led):
        # Prende el LED
        self.GPIO.output(led, False)

        # Espera a que el valor suba a 1
        while self.GPIO.input(sensor) == 0:
            time.sleep(0.005)

        # Verifica que se mantenga estable en 1 durante al menos x segundos
        t0 = time.time()
        while time.time() - t0 < 1.0:
            if self.GPIO.input(sensor) != 1:
                return False
            time.sleep(0.005)

        self.GPIO.output(led, True)
        return True

    def muestrea_portal(self):
        while True:
            val = self.muestrea_sensor(OK_SENSOR, OK_LED, OK_INDICE)
            if (val == True):
                self.sorteo.incrementa_contador(OK_INDICE)	# Regitra el evento en  la cajita correspondiente
               
            val = self.muestrea_sensor(NG_SENSOR, NG_LED, NG_INDICE)
            if (val == True):
                self.sorteo.incrementa_contador(NG_INDICE)
            
            time.sleep(0.02)  # Espera un poco antes de volver para no saturar el hilo
    
    def muestrea_sensor(self, sensor, led, indice):
        valor = self.GPIO.input(sensor)
        if valor == 0:
            self.GPIO.output(led, False) # Prende el led del sensor correspondiente
            print("🔔 Evento de conteo detectado en el portal\n")

            # Espera hasta que el valor regrese a 1
            while self.GPIO.input(sensor) == 0:
                time.sleep(0.02)

            # Verifica que se mantenga en 1 durante al menos x segundos
            tiempo_estable = time.time()
            while self.GPIO.input(sensor) == 1:	    
                if time.time() - tiempo_estable >= 1.0:
                    self.GPIO.output(led, True)
                    return True
                time.sleep(0.02)  # Espera un poco antes de volver a verificar
            else:
                # Si salió del ciclo sin cumplir los x segundos, no cuenta como evento válido
                return False
        return False

    def prende_led_ok(self):
        if self.es_pi:
            self.GPIO.output(OK_LED, False)
        else:
            print("⚠️  No es Raspberry Pi: no se puede prender el LED OK.")

    def apaga_led_ok(self):
        if self.es_pi:
            self.GPIO.output(OK_LED, True)
        else:
            print("⚠️  No es Raspberry Pi: no se puede apagar el LED OK.")

    def prende_led_ng(self):
        if self.es_pi:
            self.GPIO.output(NG_LED, False)
        else:
            print("⚠️  No es Raspberry Pi: no se puede prender el LED NG.")

    def apaga_led_ng(self):
        if self.es_pi:
            self.GPIO.output(NG_LED, True)
        else:
            print("⚠️  No es Raspberry Pi: no se puede apagar el LED NG.")

    def cleanup(self):
        if self.es_pi:
            self.GPIO.cleanup()
            print("🔔 Manejador de portal limpiado y GPIOs liberados.")
        else:
            print("⚠️  No es Raspberry Pi: no se requiere limpieza de GPIOs.")


