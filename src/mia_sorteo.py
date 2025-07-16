import asyncio
import threading
import time

class ManejadorSorteo:
    def __init__(self, gui):
        self.gui = gui
        self.loop = asyncio.get_event_loop()
        # Inicializa los contadores de las cajitas de sorteo
        self.contadores_cajitas = [0] * 7           # OK, NG-1, NG-2, NG-3, NG-4, NG-5, NG-MIX
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
        self.contadores_cajitas = [0] * 7
        self.gui.limpia_cajitas()
        # Pone el "radiobutton" de multiplicador en X1
        self.gui.multiplicador_var.set(1)
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
        if idx == 6:
            for i in range(5):
                if self.estado_botones_inci[i]:
                    inci.append(incidentes[i+1])
          
        else:
            inci.append(incidentes[idx])
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