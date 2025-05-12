import asyncio
import websockets
import threading
import json
import time

# URL del servidor Rails SysQB en la Mac / ruta del WebSocket (Action Cable) declarada en config/environments/development.rb
URL_LA_PAZ = "ws://192.168.1.129:3000/cable" 
URL_SIMULADOR = "wss://shielded-taiga-04156.herokuapp.com/cable"

class WebSocketMia:
    def __init__(self, gui, contador):
        self.url = URL_LA_PAZ
        self.gui = gui
        self.contador = contador
        self.ws = None
        self.is_running = False
        self.mesa_id = "MIA-01"
        
    

    def connect(self):
        if not self.is_running:
            self.is_running = True
            threading.Thread(target=self._run_forever, daemon=True).start()

    def _run_forever(self):
        asyncio.run(self._ciclo_infinito())

    async def _ciclo_infinito(self):
        
        # Conexión al WebSocket de Rails
        sysqb_websocket = await self._conecta_rails_websocket()
        if sysqb_websocket is None:
            print("❌ No se pudo establecer la conexión WebSocket con Rails.")
            return  # Salir si no se pudo conectar

        try:
            print("🔌 Conectado al servidor SysQB por WebSocket")
            #self.gui.despliega_mensaje_rx("🔌 Conectado al servidor SysQB por WebSocket")

            # Se suscribe al canal "MiaChannel con el id de la mesa: MIA-XX"
            self.mesa_id = f"MIA-{str(self.gui.lee_mesa()).zfill(2)}"  # Convierte a cadena de dos dígitos con cero al inicio y prefijo "MIA-"
            while not await self._suscribe_mia_channel(sysqb_websocket, self.mesa_id):
                print("🔄 Reintentando suscripción en 5 segundos...")
                self.gui.despliega_mensaje_tx("Reintentando suscripción en 5 segundos...\n")
                await asyncio.sleep(5)
                        
            while self.is_running:
                try:
                    respuesta_servidor = await sysqb_websocket.recv()
                    data = json.loads(respuesta_servidor)
                    print(" Respuesta del servidor:", data)
                    
                    # Si el mensaje es un "ping", simplemente se ignora para mantener la conexión
                    if data.get("type") == "ping":
                        print("📡 Keep-Alive recibido del servidor")
                        self.gui.despliega_mensaje_rx("Keep-Alive recibido del servidor")
                        continue
                        
                    if 'message' in data:
                        self.gui.despliega_mensaje_rx(f"{data['message']}")

                    ok = self.contador.lee_ok()
                    ng = self.contador.lee_ng()
                    mesa = self.gui.lee_mesa()
                    
                    # Envía datos periódicamente al canal "MiaChannel" de Rails
                    data = {
                        "command": "message",
                        "identifier": json.dumps({"channel": "MiaChannel", "mia_id": self.mesa_id}),
                        "data": json.dumps({"mesa": mesa, "piezas_ok": ok, "piezas_ng": ng})
                    }
                    await sysqb_websocket.send(json.dumps(data))
                    print("📡 Enviado:", data)
                    self.gui.despliega_mensaje_tx(f"{data['data']}")

                    

                    await asyncio.sleep(1)  # Enviar datos cada 1 segundo

                except websockets.exceptions.ConnectionClosed:
                    print("❌ Conexión WebSocket cerrada. Reintentando en 5 segundos...")
                    await asyncio.sleep(5)
                    return await self.connect()  # Reintenta conexión
        finally:
            await sysqb_websocket.close()  # Se cierra la conexión 

    async def _conecta_rails_websocket(self):
        # Conexión al WebSocket de Rails
        try:
            sysqb_socket = await websockets.connect(self.url, ping_interval=20, ping_timeout=10)
            return sysqb_socket
        except Exception as e:
            print(f"❌ Error al conectar al WebSocket de Rails: {e}")
            self.gui.despliega_mensaje_tx(f"Error al conectar al SysQB WebSocket de: {e}\n")
            return None
    
    async def _suscribe_mia_channel(self, sysqb_socket, mesa_id): 
        mensaje_suscribir = {
            "command": "subscribe",
            "identifier": json.dumps({"channel": "MiaChannel", "mia_id": mesa_id})
        }
        try:
            await sysqb_socket.send(json.dumps(mensaje_suscribir))
            print("🔗 Suscrito al canal MiaChannel")
            self.gui.despliega_mensaje_tx("🔗  Suscrito al canal MiaChannel.\n")
            return True  # Indica éxito 
        except Exception as e:
            print(f"❌ Error al enviar el mensaje de suscripción: {e}")
            self.gui.despliega_mensaje_tx(f"❌ Error al enviar el mensaje de su suscripción: {e}\n")
            return False

    def envia_mensaje(self, sysqb_socket, mia_id, datos):
        
        mensaje = {
            "command": "message",
            "identifier": json.dumps({"channel": "MiaChannel", "mia_id": mia_id}),
            "data": json.dumps(datos)
        }
        self.sysqb_socket.send(json.dumps(mensaje))

    def disconnect(self):
        self.is_running = False

    def on_message(self, ws, message):
        print(f"Message received: {message}")

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket closed")

    def send_message(self, message):
        if self.is_running and self.ws:
            self.ws.send(message)