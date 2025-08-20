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
        self.peso_bascula = 0.0
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
        self.peso_anterior = 0.0
        self.peso_actual = 0.0
        self.tara = 0.0
        self.peso_bascula = 0.0

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

    def incrementa_contador(self, idx, piezas):
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
        self.sorteo_activo = True
        def loop_muestreo():
            while self.sorteo_activo:
                self.muestrea_bascula()
                time.sleep(0.5)
                   
        self.hilo_bascula = threading.Thread(target=loop_muestreo, daemon=True)
        self.hilo_bascula.start()

    def muestrea_bascula(self):
        self.gui.apaga_peso_actual()
        time.sleep(0.5)
        self.peso_bascula = self.lee_bascula()
        if self.peso_bascula < 0.0:  
            self.tara = self.peso_anterior
            self.gui.despliega_bascula_apagada(True)
            time.sleep(0.75)
            self.gui.despliega_bascula_apagada(False)
            return
        else:
            self.peso_bascula = self.peso_bascula + self.tara
            self.gui.despliega_peso_actual(self.peso_bascula)

        self.gui.despliega_titulo_peso()
        if self.gui.tipo_conteo_peso.get() == False:
            return

        es_valido, piezas = self.es_nueva_pieza_por_peso(self.peso_anterior, self.peso_bascula)
        if es_valido:  
            print(f"Peso válido: {self.peso_bascula} kg, Piezas estimadas: {piezas}")  
            self.gui.portal.prende_led_ok()
            self.incrementa_contador(0, piezas)
            peso_pieza = round(self.peso_bascula - self.peso_anterior, 1)
            self.peso_anterior = self.peso_bascula
            self.gui.actualiza_pesos(self.peso_anterior, self.peso_bascula, piezas)
            time.sleep(2.0)
            self.gui.portal.apaga_led_ok()

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
        
    def lee_bascula(self):
        num_lecturas_max = 10  # Número máximo de lecturas consecutivas
        umbral_estabilidad = 2.0  # Diferencia máxima permitida entre lecturas (en gramos)
        lecturas_consecutivas_estables = 3  # Número de lecturas consecutivas necesarias para considerar estabilidad

        lecturas = []
        contador_estables = 0

        for _ in range(num_lecturas_max):
            try:
                peso = self.lee_bascula_ok()  # Llama al método que realiza una lectura de la báscula
                lecturas.append(peso)

                # Si hay lecturas previas, compara con la última
                if len(lecturas) > 1:
                    diferencia = abs(lecturas[-1] - lecturas[-2])
                    if diferencia <= umbral_estabilidad:
                        contador_estables += 1
                    else:
                        contador_estables = 0  # Reinicia el contador si la lectura no es estable

                # Si se alcanzan las lecturas consecutivas estables necesarias, regresa el valor promedio
                if contador_estables >= lecturas_consecutivas_estables:
                    return round(sum(lecturas[-lecturas_consecutivas_estables:]) / lecturas_consecutivas_estables, 1)

            except Exception as e:
                print("Error leyendo báscula:", e)
                return 0.0  # Regresa un valor predeterminado en caso de error

            time.sleep(0.1)  # Pausa breve entre lecturas para evitar lecturas rápidas consecutivas

        # Si no se alcanzó estabilidad después del número máximo de lecturas, regresa un valor predeterminado
        print("Lectura inestable después de", num_lecturas_max, "lecturas:", lecturas)
        return 0.0

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