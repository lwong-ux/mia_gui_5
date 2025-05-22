import asyncio
import threading
import time

class ManejadorSorteo:
    def __init__(self, gui):
        self.gui = gui
        # Inicializa los contadores de las cajitas de sorteo
        self.contadores_botones = [0] * 7  # OK, NG-1, NG-2, NG-3, NG-4, NG-5, NG-MIX
        self.pieza_numero = 1
        self._conteo_iniciado = False
        self._conteo_detenido = False
        self._conteo_task = None

        # Variables de conteo integradas
        self.contador_ok = 0
        self.contador_ng = 0
        self.contador_activo = False

    # Respuesta al botón INIC: limpia contdores e inica la transmisión automática de piezas 
    def inicia_conteo(self):
        if not self._conteo_iniciado:
            self._conteo_iniciado = True
            self._conteo_detenido = False
            self.limpia_contadores()
            self.gui.despliega_detener()
            self.gui.limpia_cajitas()
            loop = asyncio.get_event_loop()
            self._conteo_task = loop.create_task(self._conteo_periodico())
        else:
            self.limpia_contadores()
    
    # Inicializa todos los contadores: si el proceso automático está detenido, genera la tarea de muestrea_contadores
    def limpia_contadores(self):
        self.contador_ok = 0
        self.contador_ng = 0
        self.pieza_numero = 1
        self.contadores_botones = [0] * 7
        self.gui.limpia_cajitas()
        if self.contador_activo:
            self.contador_ng = 0
            self.contador_ok = 0
            self.gui.despliega_ok(f"{self.contador_ok:>10}")
            self.gui.despliega_ng(f"{self.contador_ng:>10}")
        else:
            self.contador_activo = True
            threading.Thread(target=self.muestrea_contadores, daemon=True).start()
    
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
        self.contadores_botones[idx] += 1
        ok = ng = 0
        if idx == 0:
            ok = 1
        else:
            ng = 1   
        loop = asyncio.get_event_loop()
        self._conteo_task = loop.create_task(self._envia_sorteo(self.pieza_numero, idx, ok, ng))
        self.pieza_numero += 1
        self.gui.actualiza_cajitas(self.pieza_numero, idx)

    async def _envia_sorteo(self, pieza, idx, ok, ng):
        incidentes = ["", "raya", "golpe", "marca", "longitud incorrecta", "falta buje", "multiples"]
        mesa_id = "MIA-" + str(self.gui.lee_mesa()).zfill(2)
        datos = {"mesa": mesa_id, "pieza": pieza, "piezas_ok": ok, "piezas_ng": ng, "incidente": incidentes[idx]}
        await self.gui.websocket_mia.envia_mensaje(self.gui.sysqb_socket, mesa_id, datos)

    