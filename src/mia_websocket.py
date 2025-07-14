import asyncio
import websockets
import threading
import json
import time

# URL del servidor Rails SysQB en la Mac / ruta del WebSocket (Action Cable) declarada en config/environments/development.rb
URL_MEZTLI = "ws://192.168.100.25:3000/cable" 
URL_SIMULADOR = "ws://shielded-taiga-04156.herokuapp.com/cable"

class WebSocketMia:
    def __init__(self, gui):
        self.url = URL_MEZTLI
        #self.url = URL_SIMULADOR
        self.gui = gui
        self.ws = None
        self.is_running = False
        self.keep_alive  = False       
    async def conecta_async(self):
        # Conexión al WebSocket de Rails
        try:
            #sysqb_socket = await websockets.connect(self.url, ping_interval=60, ping_timeout=30)
            sysqb_socket = await websockets.connect(
                self.url,
                ping_interval=None,      # deshabilita los ping automáticos de websocket
                ping_timeout=None,       # deshabilita el timeout de ping
                close_timeout=None       # no enforced close handshake timeout
            )
            print("🔌 Conectando al WebSocket de Rails")
            self.gui.despliega_mensaje_tx("🔌 Conectando al WebSocket de Rails")

            # Lanzar keepalive manual para evitar timeouts
            asyncio.create_task(self._keepalive(sysqb_socket))

            # Inicia la tarea para leer mensajes del servidor SysQB
            asyncio.create_task(self.lector_websocket(sysqb_socket))
            return sysqb_socket
           
        except Exception as e:
            print(f"❌ Error al conectar al WebSocket de Rails: {e}")
            self.gui.despliega_mensaje_tx(f"Error al conectar al SysQB WebSocket: {e}\n")
            return None
        
    async def _keepalive(self, websocket):
        """Envía pings manuales cada 30 segundos para mantener la conexión viva."""
        try:
            while True:
                await asyncio.sleep(30)
                await websocket.ping()
        except Exception as e:
            print(f"❌ Falló el envío del ping : {e}")
            # Si ping falla, la conexión se cerrará y lector_websocket lo detectará
            pass

    async def desconecta_async(self, sysqb_socket):
        # Desconecta el WebSocket
        try:
            await sysqb_socket.close()
            print("🔌 Desconectado del WebSocket de Rails\n")
            self.gui.despliega_mensaje_tx("🔌 Desconectado del WebSocket de Rails\n")
            return True
        except Exception as e:
            print(f"❌ Error al desconectar del WebSocket de Rails: {e}")
            self.gui.despliega_mensaje_tx(f"Error al desconectar del SysQB WebSocket: {e}\n")
            return None

    async def envia_mensaje(self, sysqb_socket, mia_id, datos):
        mensaje = {
        "command": "message",
        "identifier": json.dumps({"channel": "MiaChannel", "mia_id": mia_id}),
        "data": json.dumps(datos)
        }
        try:
            await sysqb_socket.send(json.dumps(mensaje))
            print("\n📡 Enviado:", mensaje)
            self.gui.despliega_mensaje_tx(f"{mensaje['data']}")
            
        except websockets.exceptions.ConnectionClosedError as e:
            print("❌ Conexión cerrada, intenta reconectar:", e)
            self.gui.despliega_mensaje_tx("❌ Conexión cerrada, intenta reconectar...\n")
        
    async def lector_websocket(self, sysqb_socket):
        while True:
            try:
                mensaje = await sysqb_socket.recv()
                data = json.loads(mensaje)
                # Procesa el mensaje según su tipo
                if data.get("type") == "ping":
                    if self.keep_alive == False:
                        print("📡 Keep-Alive recibido del servidor: ", time.strftime("%H:%M:%S") , end="", flush=True)
                        self.keep_alive = True
                    print(".", end="", flush=True)
                elif data.get("type") == "welcome":
                    print("\n✅ Conexión WebSocket establecida (welcome)")
                    self.gui.despliega_mensaje_rx("Conexión WebSocket establecida (welcome)")
                elif data.get("type") == "confirm_subscription":
                    identifier = json.loads(data.get("identifier", "{}"))
                    mia_id = identifier.get("mia_id")
                    print(f"\n✅ Suscripción confirmada al canal {mia_id}") 
                    self.gui.despliega_mensaje_rx(f"Suscripción confirmada al canal {mia_id}")
                #elif data.get("message"):
                elif data.get("message") and data.get("type") is None:
                    self.keep_alive = False
                    print("\n📡 Mensaje recibido:", time.strftime("%H:%M:%S"), data["message"])
                    self.gui.despliega_mensaje_rx(f"📡  {data.get('message')}")
                    if data.get("message", {}).get("accion") == "INICIA_FOLIO":
                        self.gui.sorteo.inicia_conteo()
                else:
                    print("\n📡 Mensaje desconocido:", data)
                    self.gui.despliega_mensaje_rx(f"📡  Mensaje desconocido: {data}\n" )
            except websockets.exceptions.ConnectionClosedError as e:
                print("\n❌ Conexión cerrada:", e)
                self.gui.despliega_mensaje_tx("❌ Conexión cerrada, intenta reconectar...\n")
                # Intentar reconectar después de unos segundos
                await asyncio.sleep(5)
                await self.conecta_async()
                break

    async def suscribe(self, sysqb_socket, mesa_id): 
        mensaje_suscribir = {
            "command": "subscribe",
            "identifier": json.dumps({"channel": "MiaChannel", "mia_id": mesa_id})
        }
        try:
            await sysqb_socket.send(json.dumps(mensaje_suscribir))
            print(f"🔗  Suscribiéndose al canal MiaChannel: {mesa_id}")
            self.gui.despliega_mensaje_tx(f"🔗  Suscribiéndose al canal MiaChannel: {mesa_id}")
            return True  # Indica éxito 
        except Exception as e:
            print(f"❌ Error al enviar el mensaje de suscripción: {e}")
            self.gui.despliega_mensaje_tx(f"❌ Error al enviar el mensaje de su suscripción: {e}\n")
            return False
