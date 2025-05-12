import threading
import time

class ContadorPiezas:
    def __init__(self, gui):
        self.gui = gui
        self.contador_ok = 0
        self.contador_ng = 0
        self.mesa = 1
        self.contador_activo = False

    def inicia_contadores(self):
            self.contador_ok = 0
            self.contador_ng = 0
            if self.contador_activo:
                self.contador_ng = 0
                self.contador_ok = 0
                self.gui.despliega_ok(f"{self.contador_ok:>10}")
                self.gui.despliega_ng(f"{self.contador_ng:>10}")
            else:
                self.contador_activo = True
                threading.Thread(target=self.muestrea_contadores, daemon=True).start()

    def muestrea_contadores(self):
        while self.contador_activo:
            if not self.gui.detiene_conteo:
                self.contador_ok += 1
                self.contador_ng = self.contador_ok // 9
                self.gui.despliega_ok(f"{self.contador_ok:>10}")
                self.gui.despliega_ng(f"{self.contador_ng:>10}")
                time.sleep(1)

    def lee_ok(self):
        return self.contador_ok
    
    def lee_ng(self):
        return self.contador_ng 
    
