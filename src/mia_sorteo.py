import asyncio
import glob
import threading
import time
import random
import hid  # 
import serial
import re
import sys

# ===============================
# MODO DE PRUEBA
# ===============================
# True  = Solo báscula NG
# False = Modo normal OK + NG
SOLO_NG = False

class BasculaAgente:
    """ Métodos y variables para leer pesos estables de la báscula. 
        Mediante incia() se conecta a una báscula por el puerto serial indicado y habilita un hilo 
        para muestrear pesos en un lazo infinito. 
        No toca widgets Tkinter directamente. Siempre notifica al handler,
        y el handler hace `gui.ui_call(...)`.
    """

    def __init__(self, cual, port, baud, sorteo):
        self.cual = cual  # "ok" o "ng"
        self.port = port
        self.baud = baud
        self.sorteo = sorteo

        self.ser = None     # El objeto que maneja el puerto serial
        self.activa = False # Bandera de báscula conectada y muestreando

        # Estado por báscula
        self.peso_bascula = 0.0     # Peso instantáneo leído, no necesariamente estable
        self.peso_anterior = 0.0    # Último peso utilizado para incrementar contadores. 
        self.peso_actual = 0.0      # Último peso válido durante el muestreo. Lo utiliza lee_bascula_serie() para retornar en caso de error
        self.tara = 0.0
        self.en_error = False

        # Parámetros de estabilidad
        self.num_lecturas_max = 10      # Número máximo de lecturas para evaluar estabilidad
        self.umbral_estabilidad = 2.0   # En gramos
        self.lecturas_consecutivas_estables = 3 # Número de lecturas consecutivas dentro del umbral para considerar estable

        # Detección de báscula apagada: adaptador conectado pero sin datos en el puerto
        self.empty_reads = 0
        self.max_empty_reads = 25  # ~2.5s con timeout=0.1

    def inicia(self):
        # Verifica si el puerto ya está abierto
        if self.ser and getattr(self.ser, "is_open", False):
            print(f"El puerto serial de báscula {self.cual.upper()} ya está abierto.")
            return
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            print(f"Puerto serial de báscula {self.cual.upper()} abierto en: {self.port}")
            self.activa = True
            threading.Thread(target=self.loop, daemon=True).start()
        except serial.SerialException as e:
            print(f"Error al abrir el puerto serial ({self.cual}): {e}")
            self.ser = None

    def loop(self):
        while self.activa:
            try:
                self.muestrea()
            except Exception as e:
                print(f"Error en el hilo de muestreo de la báscula {self.cual}: {e}")

    def muestrea(self):
        self.peso_bascula = self.lee_bascula()
        if self.peso_bascula is None:
            # Sin lectura válida (apagada o error de comunicación). Marca estado y avisa.
            if not self.en_error:
                self.en_error = True
                print(f"\n[{self.cual.upper()}] Báscula apagada / sin datos en el puerto {self.port}")
                self.sorteo._bascula_apagada(self.cual)
            time.sleep(0.5)
            return

        # Si veníamos de error, limpia el estado y avisa recuperación
        if self.en_error:
            self.en_error = False
            self.empty_reads = 0
            print(f"\n[{self.cual.upper()}] Báscula recuperada / datos recibidos en {self.port}")
            self.sorteo._bascula_recuperada(self.cual)

        # Se actualiza la última lectura válida
        self.peso_actual = self.peso_bascula
        self.sorteo._bascula_peso_actual(self.cual, self.peso_bascula)

        # Si no está activo conteo por peso, no evalua piezas
        if self.sorteo.gui.tipo_conteo_peso.get() is False:
            return

        # Evalúa si hay nueva pieza por peso según los parámetros de calibración
        es_valido, piezas = self.sorteo.es_nueva_pieza_por_peso(self.peso_anterior, self.peso_bascula)
        if es_valido:
            self.sorteo._bascula_pieza_valida(self.cual, piezas, self.peso_bascula, self.peso_anterior)
            self.peso_anterior = self.peso_bascula

    def lee_bascula_serie(self):
        try:
            linea = self.ser.readline().decode(errors="ignore").strip()

            # Caso 1: no llegó nada (timeout) => cuenta como lectura vacía
            if not linea:
                self.empty_reads += 1
                if self.empty_reads >= self.max_empty_reads:
                    return None
                return self.peso_actual

            # Caso 2: llegó texto pero puede no traer número
            coincidencias = re.search(r"([+-])?\s*(\d+(?:\.\d+)?)", linea)
            if not coincidencias:
                self.empty_reads += 1
                if self.empty_reads >= self.max_empty_reads:
                    return None
                return self.peso_actual

            # Caso 3: llegó número válido
            signo = coincidencias.group(1) or "+"
            numero = coincidencias.group(2)
            peso = round(float(f"{signo}{numero}"), 1)
            sys.stdout.write(
                f"\r[{self.cual.upper()}] Línea: {linea.strip()} // Peso: {peso:+6.1f}g //  "
            )
            sys.stdout.flush()
            self.empty_reads = 0
            return peso

        except serial.SerialException as e:
            print(f"Error del puerto serial ({self.cual}): {e}")
            self.empty_reads = self.max_empty_reads
            return None
        except Exception as e:
            print(f"Error en lee_bascula_serie ({self.cual}): {e}")
            return None

    def lee_bascula(self):
        lecturas = []
        contador_estables = 0

        for _ in range(self.num_lecturas_max):
            peso = self.lee_bascula_serie()
            if peso is None:
                return None

            lecturas.append(peso)
            if len(lecturas) > 1:
                diferencia = abs(lecturas[-1] - lecturas[-2])
                if diferencia <= self.umbral_estabilidad:
                    contador_estables += 1
                else:
                    contador_estables = 0

            if contador_estables >= self.lecturas_consecutivas_estables:
                ult = lecturas[-self.lecturas_consecutivas_estables:]
                return round(sum(ult) / len(ult), 1)

        # Si no se alcanzó estabilidad
        return 0.0


class ManejadorSorteo:
    def __init__(self, gui, es_rpi):
        self.gui = gui
        self.es_rpi = es_rpi
        self.loop = asyncio.get_event_loop()
        # Inicializa los contadores de las cajitas de sorteo
        self.contadores_cajitas = [0] * 7           # OK, NG-MIX, num_pieza, peso_anterior_ok, peso_anterior_ng
        self.estado_botones_inci = [False] * 5      # Estado de los botones de incidentes
        self.multiplicador = 1                      # Multiplicador de piezas: 1, 10, 100
        self.pieza_numero = 1
        self._conteo_iniciado = False
        self._conteo_detenido = False
        self._conteo_task = None
        self.folio = 1957

        # Variables de conteo integradas
        self.contador_ok = 0
        self.contador_ng = 0
        self.contador_activo = False
        
        # Pila para guardar el estado de los contadores
        self.stack_contadores = []

        # Protege estado compartido (básculas vs websocket vs GUI)
        self._state_lock = threading.Lock()

        # Variables de básculas (OK/NG)
        # Mantengo `peso_bascula` como alias de la báscula OK para no romper calibración existente.
        self.peso_bascula = 0.0
        self.peso_bascula_ng = 0.0

        self.bascula_ok = None
        self.bascula_ng = None
        # Peso y piezas anterior por báscula (para stack/cajitas)
        self.peso_anterior_ok = 0.0
        self.peso_anterior_ng = 0.0
        self.pieza_registrada_ng = 0
        self.pieza_registrada_ok = 0
       
    # Respuesta al botón INIC: limpia contadores
    def inicia_conteo(self):
        #self.inicia_folio()
        if not self._conteo_iniciado:
            self._conteo_iniciado = True
            self._conteo_detenido = False
            self.limpia_contadores()
            self.gui.limpia_cajitas()
            # Eliminar el comentario para habilitar la función de conteo periódico
            #self.gui.despliega_detener()
            #loop = asyncio.get_event_loop()
            #self._conteo_task = loop.create_task(self._conteo_periodico())
        else:
            self.limpia_contadores()
        
    # Inicializa todos los contadores: si el proceso automático está detenido, genera la tarea de muestrea_contadores
    def limpia_contadores(self):
        self.contador_ok = 0
        self.contador_ng = 0
        self.pieza_numero = 1
        self.contadores_cajitas = [0] * 7  # OK, NG-MIX, num_pieza, peso_anterior_ok, peso_anterior_ng
        # Reinicia la pila de deshacer para evitar estados viejos/incompatibles
        self.stack_contadores = []
        self.gui.ui_call(self.gui.limpia_cajitas)
        # Resetea lecturas de básculas
        self.peso_bascula = 0.0
        self.peso_bascula_ng = 0.0
        self.peso_anterior_ok = 0.0
        self.peso_anterior_ng = 0.0
        self.pieza_registrada_ng = 0
        self.pieza_registrada_ok = 0
        if self.bascula_ok:
            self.bascula_ok.peso_anterior = 0.0
            self.bascula_ok.peso_bascula = 0.0
            self.bascula_ok.peso_actual = 0.0
            self.bascula_ok.tara = 0.0
            self.bascula_ok.en_error = False
        if self.bascula_ng:
            self.bascula_ng.peso_anterior = 0.0
            self.bascula_ng.peso_bascula = 0.0
            self.bascula_ng.peso_actual = 0.0
            self.bascula_ng.tara = 0.0
            self.bascula_ng.en_error = False

        # Pone el "radiobutton" de multiplicador en X1
        self.gui.multiplicador_var.set(1)
        self.gui.limpia_pesos()
        
        # Eliminar el comentario para habilitar la función de conteo periódico
        # if self.contador_activo:
        #     self.contador_ng = 0
        #     self.contador_ok = 0
        #     self.gui.despliega_ok(f"{self.contador_ok:>10}")
        #     self.gui.despliega_ng(f"{self.contador_ng:>10}")
        # else:
        #     self.contador_activo = True
        #     threading.Thread(target=self.muestrea_contadores, daemon=True).start()
    
    def fin_conteo(self):
        return

    def muestrea_contadores(self):
        while self.contador_activo:
            if not self._conteo_detenido:
                self.contador_ok += 1
                self.contador_ng = self.contador_ok // 9
                self.gui.despliega_ok(f"{self.contador_ok:>10}")
                self.gui.despliega_ng(f"{self.contador_ng:>10}")
                time.sleep(1)

    def detiene_conteo(self):
        self._conteo_detenido = not self._conteo_detenido
        if self._conteo_detenido:
            self.gui.despliega_continuar()
        else:
            self.gui.despliega_detener()
        if not self._conteo_detenido:
            self._conteo_iniciado = True
            loop = asyncio.get_event_loop()
            self._conteo_task = loop.create_task(self._conteo_periodico())

    async def _conteo_periodico(self):
        while self._conteo_iniciado and not self._conteo_detenido:
            ok = self.lee_ok()
            ng = self.lee_ng()
            mesa_id = "MIA-" + str(self.gui.lee_mesa()).zfill(2)
            datos = {"mesa": mesa_id, "piezas_ok": ok, "piezas_ng": ng}
            await self.gui.websocket_mia.envia_mensaje(self.gui.sysqb_socket, mesa_id, datos)
            await asyncio.sleep(1)

    def lee_ok(self):
        return self.contador_ok

    def lee_ng(self):
        return self.contador_ng
    
    def push_contadores(self):
        # Guarda el estado actual de los contadores en la pila.
        self.stack_contadores.append(self.contadores_cajitas.copy())

    def pop_contadores(self):
        # Restaura el estado anterior de los contadores desde la pila.
        # IMPORTANT: también debe restaurar el `peso_anterior` interno de cada BasculaAgente,
        # porque es el que se usa para calcular incrementos (piezas) en el hilo de muestreo.
     
        if self.stack_contadores:
            self.contadores_cajitas = self.stack_contadores.pop()
            self.pieza_numero = self.contadores_cajitas[2]
            self.peso_anterior_ok = self.contadores_cajitas[3]
            self.peso_anterior_ng = self.contadores_cajitas[4]
            self.pieza_registrada_ok = self.contadores_cajitas[5]
            self.pieza_registrada_ng = self.contadores_cajitas[6]

            # Sincroniza el estado interno de las básculas con el peso anterior restaurado
            if self.bascula_ok is not None:
                self.bascula_ok.peso_anterior = self.peso_anterior_ok
            if self.bascula_ng is not None:
                self.bascula_ng.peso_anterior = self.peso_anterior_ng

        else:
            print("La pila de contadores está vacía. No se puede realizar pop.")
            return

        # Actualiza GUI fuera del lock (solo UI)
        for idx in range(2):
            self.gui.ui_call(
                self.gui.actualiza_cajitas,
                self.pieza_numero,
                self.peso_anterior_ok,
                self.peso_anterior_ng,
                idx,
            )
        self.gui.ui_call(
            self.gui.actualiza_piezas_registradas_okng,
            self.pieza_registrada_ok,
            self.pieza_registrada_ng,
        )

    def incrementa_contador(self, idx, piezas):
        with self._state_lock:
            self.contadores_cajitas[2] = self.pieza_numero
            self.contadores_cajitas[3] = self.peso_anterior_ok
            self.contadores_cajitas[4] = self.peso_anterior_ng
            self.contadores_cajitas[5] = self.pieza_registrada_ok
            self.contadores_cajitas[6] = self.pieza_registrada_ng
            self.push_contadores()  # Guarda el estado actual antes de modificarlo

            if self.gui.tipo_conteo_peso.get():
                self.multiplicador = piezas
            else:
                self.multiplicador = self.gui.multiplicador_var.get()

            self.contadores_cajitas[idx] += self.multiplicador
            ok = ng = 0
            if idx == 0:
                ok = self.multiplicador
            else:
                ng = self.multiplicador

            pieza_envio = self.pieza_numero
            mult_envio = self.multiplicador
            self.pieza_numero += self.multiplicador

        # Envía mensaje fuera del lock
        asyncio.run_coroutine_threadsafe(
            self._pieza_inspeccionada(pieza_envio, idx, ok, ng),
            self.loop,
        )

        # IMPORTANT: este método puede ser llamado desde el hilo de la báscula.
        # Toda actualización de Tkinter debe encolarse al hilo principal.
        self.gui.ui_call(self.gui.actualiza_cajitas, self.pieza_numero, self.peso_anterior_ok, self.peso_anterior_ng, idx)
       
    # Función del protocolo MIA-Proper 1.0: Envía el comando 'PIEZA_INSPEC'
    async def _pieza_inspeccionada(self, pieza, idx, ok, ng):
        incidentes = ["", "1", "2", "3", "4", "5"]
        inci = []
        mia_id = "MIA-" + str(self.gui.lee_mesa()).zfill(2)
        # Si los incidentes son múltiples, lee los botones activos:
        # if idx == 6:
        #     for i in range(5):
        #         if self.estado_botones_inci[i]:
        #             inci.append(incidentes[i+1])
          
        # else:
        #     inci.append(incidentes[idx])

        # Ya no existen las cajitas de incidentes, siempre se envía inci=[]. SysQB tomará los incidentes con palomita.
        pieza_inspec = {"pieza": pieza, "multiplicador": self.multiplicador, "piezas_ok": ok, "piezas_ng": ng, "incidentes": inci}
        datos = {"tipo": "comando", "accion": "PIEZA_INSPEC", "folio": self.folio, "mesa": mia_id, "pieza_inspec": pieza_inspec}
        await self.gui.websocket_mia.envia_mensaje(mia_id, datos)

    def inicia_folio(self):
        loop = asyncio.get_event_loop()
        self._conteo_task = loop.create_task(self._inicia_folio_async())
       
    # Función del protocolo MIA-Proper 1.0: Envía el comando 'INICIA_FOLIO'
    async def _inicia_folio_async(self):
        mia_id = "MIA-" + str(self.gui.lee_mesa()).zfill(2)
        datos = {"tipo": "comando", "accion": "INICIA_FOLIO", "folio":"1000"}
        await self.gui.websocket_mia.envia_mensaje(self.gui.sysqb_socket, mia_id, datos)

    #############################################################
    #
    # Funciones para el manejo de la báscula
    # 
    #############################################################

    def inicia_basculas(self):
        BAUD = 9600
        print(f"Modo SOLO_NG = {SOLO_NG}")  # Despliega la global de prueba

        # Puertos por plataforma (autodetección). Si solo hay 1 báscula, NO se inicia NG.
        port_ok = None
        port_ng = None

        if self.es_rpi:
            # RPi suele exponer /dev/ttyUSB*
            puertos = sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))
        else:
            # macOS suele exponer /dev/cu.usbserial* o /dev/cu.usbmodem*
            puertos = sorted(glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.usbmodem*"))

        if len(puertos) >= 1:
            port_ok = puertos[0]
        if len(puertos) >= 2:
            port_ng = puertos[1]

        if SOLO_NG:
            # Si solo hay 1 puerto conectado, úsalo como NG
            if port_ok and not port_ng:
                port_ng = port_ok
            # Desactiva OK
            port_ok = None

        print(f"Puertos detectados: {puertos}")
        print(f"Báscula OK  -> {port_ok}")
        print(f"Báscula NG  -> {port_ng if port_ng else 'NO CONECTADA'}")

        # OK: siempre que exista puerto
        if port_ok:
            if not self.bascula_ok:
                self.bascula_ok = BasculaAgente("ok", port_ok, BAUD, self)
            else:
                self.bascula_ok.port = port_ok
            self.bascula_ok.inicia()
        else:
            print("No se detectó puerto para báscula OK.")

        # NG: solo si existe segundo puerto
        if port_ng:
            if not self.bascula_ng:
                self.bascula_ng = BasculaAgente("ng", port_ng, BAUD, self)
            else:
                self.bascula_ng.port = port_ng
            self.bascula_ng.inicia()
        else:
            # Si no hay NG conectada, asegúrate de no arrancarla.
            self.bascula_ng = None

    def es_nueva_pieza_por_peso(self, anterior, actual):
        try:
            promedio = float(self.gui.peso_promedio_entry.get())
            tolerancia_pct = float(self.gui.tolerancia_var.get()) / 100.0
            incremento = actual - anterior

            # Si no hay incremento, no es una nueva pieza
            if incremento <= 0:
                return False, 0

            # Estima el número de piezas basado en el incremento
            piezas_estimadas = round(incremento / promedio)

            # Calcula los límites de tolerancia para el peso total
            limite_inferior = piezas_estimadas * promedio * (1.0 - tolerancia_pct)
            limite_superior = piezas_estimadas * promedio * (1.0 + tolerancia_pct)

            # Verifica si el peso total está dentro de la tolerancia
            if limite_inferior <= incremento <= limite_superior:
                return True, piezas_estimadas
            else:
                return False, 0
        except ValueError:
            return False, 0
    
    # Esta función lee la báscula HID Dymo M10/M25. Ya no se utiliza en el código actual.
    def lee_bascula_dymo(self):
        VENDOR_ID = 0x0922  # 2338 - 
        PRODUCT_ID = 0x8003  # 32771 - Dymo M10/M25

        try:
            dev = hid.Device(VENDOR_ID, PRODUCT_ID)
            data = dev.read(8, timeout=500)
            dev.close()
            if data:
                weight_raw = data[4] + (256 * data[5])
                return round(weight_raw, 1)
            else:
                print("No se recibió dato")
                return self.peso_actual
        except hid.HIDException as e:
            return -1.0  # Valor de error, no se pudo leer la báscula
        except Exception as e:
            print("Error al leer la báscula:", e)
            return self.peso_actual
        
    # ---------------------------------
    #   Manejadores del GUI (handlers thread-safe): Métodos seguros para enviar información 
    #   desde los hilos de las básculas hacia el hilo del GUI. Siempre usan gui.ui_call()
    #   como método de enlace.
    # ---------------------------------
    def _bascula_apagada(self, cual):
        self.gui.ui_call(self.gui.despliega_bascula_apagada, True, cual)

    def _bascula_recuperada(self, cual):
        self.gui.ui_call(self.gui.despliega_bascula_apagada, False, cual)

    def _bascula_peso_actual(self, cual, peso):
        # Si NG no está conectada, ignora cualquier update NG
        if cual == "ng" and self.bascula_ng is None:
            return

        if cual == "ng":
            self.peso_bascula_ng = peso
            if self.bascula_ok is None:
                self.peso_bascula = peso
        else:
            self.peso_bascula = peso

        self.gui.ui_call(self.gui.despliega_peso_actual, peso, cual)
        self.gui.ui_call(self.gui.despliega_titulo_peso)

    def _bascula_pieza_valida(self, cual, piezas, peso_actual, peso_anterior):
        # Si NG no está conectada, ignora cualquier evento NG
        if cual == "ng" and self.bascula_ng is None:
            return
        # Selección de contador y LED
        if cual == "ng":
            idx = 1
            self.gui.portal.prende_led_ng()
        else:
            idx = 0
            self.gui.portal.prende_led_ok()

        # Mantiene peso anterior por báscula (stack/cajitas)
        if cual == "ng":
            self.peso_anterior_ng = peso_anterior
        else:
            self.peso_anterior_ok = peso_anterior
        self.incrementa_contador(idx, piezas)

        # Actualiza GUI (thread-safe)
        self.gui.ui_call(self.gui.actualiza_pesos, peso_actual, piezas, cual)

        time.sleep(3.0)
        print(f"antes de actualiza_peso_anterior(): {cual}")
        self.gui.ui_call(self.gui.actualiza_peso_anterior, peso_actual, cual)
        self.gui.ui_call(self.gui.actualiza_pieza_registrada, piezas, cual)
        self.gui.ui_call(self.gui.borra_pieza_final, cual)

        if cual == "ng":
            self.pieza_registrada_ng = piezas
            self.gui.portal.apaga_led_ng()
        else:
            self.pieza_registrada_ok = piezas
            self.gui.portal.apaga_led_ok()