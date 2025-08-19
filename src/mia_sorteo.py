import asyncio
import threading
import time
import random
import hid  # 

class ManejadorSorteo:
    def __init__(self, gui):
        self.gui = gui
        self.loop = asyncio.get_event_loop()
        # Inicializa los contadores de las cajitas de sorteo
        self.contadores_cajitas = [0] * 2           # OK, NG-MIX
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

        # Variables de la báscula
        self.peso_anterior = 0.0
        self.peso_actual = 0.0
        self.tara = 0.0  # Tara de la báscula
    
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
        self.contadores_cajitas = [0] * 2  # OK, NG-MIX
        self.gui.limpia_cajitas()
        self.peso_anterior = 0
        self.peso_actual = 0

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

    def incrementa_contador(self, idx):
        self.multiplicador = self.gui.multiplicador_var.get()
        self.contadores_cajitas[idx] += self.multiplicador
        ok = ng = 0
        if idx == 0:
            ok = self.multiplicador
        else:
            ng = self.multiplicador  

        asyncio.run_coroutine_threadsafe(
            self._pieza_inspeccionada(self.pieza_numero, idx, ok, ng),
            self.loop
        )
        self.pieza_numero += self.multiplicador
        self.gui.actualiza_cajitas(self.pieza_numero, idx)

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
    def inicia_bascula(self):
        self.muestreo_activo = True

        def loop_muestreo():
            while self.muestreo_activo:
                self.muestrea_bascula()
                time.sleep(0.5)

        self.hilo_bascula = threading.Thread(target=loop_muestreo, daemon=True)
        self.hilo_bascula.start()

    def lee_bascula_simula(self):
        try:
            promedio = float(self.gui.peso_promedio_entry.get())
            tolerancia_pct = float(self.gui.tolerancia_var.get()) / 100.0
        except ValueError:
            promedio = 100.0
            tolerancia_pct = 0.05

        peso_pieza = random.uniform(
            promedio * (1.0 - tolerancia_pct),
            promedio * (1.0 + tolerancia_pct)
        )
        return round(self.peso_actual + peso_pieza, 1)

    def muestrea_bascula(self):
        self.gui.apaga_peso_actual()
        time.sleep(0.5)
        peso_bascula = self.lee_bascula_ok()
        if peso_bascula < 0.0:  
            self.tara = self.peso_anterior
            self.gui.despliega_bascula_apagada(True)
            time.sleep(0.75)
            self.gui.despliega_bascula_apagada(False)
            return
        else:
            peso_bascula = peso_bascula + self.tara
            self.gui.despliega_peso_actual(peso_bascula)

        self.gui.despliega_titulo_peso()
        if self.gui.tipo_conteo_peso.get() == False:
            return

        if self.es_nueva_pieza_por_peso(self.peso_anterior, peso_bascula):
            self.gui.portal.prende_led_ok()
            self.incrementa_contador(0)
            peso_pieza = round(peso_bascula - self.peso_anterior, 1)
            self.peso_anterior = peso_bascula
            self.gui.actualiza_pesos(self.peso_anterior, peso_bascula, peso_pieza)
            time.sleep(2.0)
            self.gui.portal.apaga_led_ok()

    def es_nueva_pieza_por_peso(self, anterior, actual):
        try:
            promedio = float(self.gui.peso_promedio_entry.get())
            tolerancia_pct = float(self.gui.tolerancia_var.get()) / 100.0
            incremento = actual - anterior
            limite_inferior = promedio * (1.0 - tolerancia_pct)
            limite_superior = promedio * (1.0 + tolerancia_pct)
            return limite_inferior <= incremento <= limite_superior
        except ValueError:
            return False
        
    def lee_bascula(self):
        lecturas = []
        num_lecturas = 3
        umbral_estabilidad = 2.0  # gramos

        for _ in range(num_lecturas):
            try:
                peso = self.lee_bascula()
                lecturas.append(peso)
            except Exception as e:
                print("Error leyendo báscula:", e)
                return 0.0
            time.sleep(0.1)  # pequeña pausa entre lecturas

        max_peso = max(lecturas)
        min_peso = min(lecturas)

        if max_peso - min_peso <= umbral_estabilidad:
            return round(sum(lecturas) / len(lecturas), 1)
        else:
            print("Lectura inestable:", lecturas)
            return 0.0


    def lee_bascula_ok(self):
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

