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

        #self.url = URL_SIMULADOR
        self.gui = gui
        url = self.gui.lee_url()  # Obtiene la URL desde la GUI
        self.url = self.convierte_url(url) 
        self.ws = None
        self.is_running = False
        self.keep_alive  = False
        self.socket_activo = None
        self.mesa_id = None

    async def conecta_async(self, mia_id):
       
        # Conexión al WebSocket de Rails
        try:
            url = self.gui.lee_url()
            self.url = self.convierte_url(url)
            self.mesa_id = mia_id
            #sysqb_socket = await websockets.connect(self.url, ping_interval=60, ping_timeout=30)
            self.socket_activo = await websockets.connect(
                self.url,
                ping_interval=None,      # deshabilita los ping automáticos de websocket
                ping_timeout=None,       # deshabilita el timeout de ping
                close_timeout=None       # no enforced close handshake timeout
            )
            print("Conectando al WebSocket de Rails")
            self.gui.despliega_mensaje_tx("Conectando al WebSocket de Rails")
            
            # Se suscribe al canal MiaChannel con  identificador de mesa
            suscripcion = await self.suscribe(self.mesa_id)
            if not suscripcion:
                return None

            # Lanzar keepalive manual para evitar timeouts
            asyncio.create_task(self._keepalive())

            # Inicia la tarea para leer mensajes del servidor SysQB
            asyncio.create_task(self.lector_websocket())
            self.gui.conectado = True
            return self.socket_activo
           
        except Exception as e:
            print(f"Error al conectar al WebSocket de Rails: {e}")
            self.gui.despliega_mensaje_tx(f"Error al conectar al SysQB WebSocket: {e}\n")
            return None
        
    async def _keepalive(self):
        # Envía pings manuales cada 5 segundos para mantener la conexión viva.
        try:
            while True:
                await asyncio.sleep(1)
                try:
                    await self.socket_activo.ping()
                except Exception as e:
                    self.gui.conectado = False
                    print(f"Falló el envío del ping : {e}")
                    self.gui.conectado = False
                    # Si ping falla, la conexión se cerrará y lector_websocket lo detectará
                    break # Sale del bucle para que lector_websocket maneje la reconexión
        except Exception as e:
            print(f"Error en keepalive: {e}")
    
    async def desconecta_async(self):
        # Desconecta el WebSocket
        try:
            await self.socket_activo.close()
            print("Desconectado del WebSocket de Rails\n")
            self.gui.despliega_mensaje_tx("Desconectado del WebSocket de Rails\n")
            return True
        except Exception as e:
            print(f"Error al desconectar del WebSocket de Rails: {e}")
            self.gui.despliega_mensaje_tx(f"Error al desconectar del SysQB WebSocket: {e}\n")
            return None

    async def envia_mensaje(self, mia_id, datos):
        mensaje = {
        "command": "message",
        "identifier": json.dumps({"channel": "MiaChannel", "mia_id": mia_id}),
        "data": json.dumps(datos)
        }
        try:
            await self.socket_activo.send(json.dumps(mensaje))
            print("\nEnviado:", mensaje)
            self.gui.despliega_mensaje_tx(f"{mensaje['data']}")
            
        except websockets.exceptions.ConnectionClosedError as e:
            print("Conexión cerrada, intenta reconectar:", e)
            self.gui.despliega_mensaje_tx("Conexión cerrada, intenta reconectar...\n")
        
    async def lector_websocket(self):
        while True:
            try:
                mensaje = await self.socket_activo.recv()
                data = json.loads(mensaje)
                # Procesa el mensaje según su tipo
                if data.get("type") == "ping":
                    if self.keep_alive == False:
                        print("Keep-Alive recibido del servidor: ", time.strftime("%H:%M:%S") , end="", flush=True)
                        self.keep_alive = True
                    print(".", end="", flush=True)
                elif data.get("type") == "welcome":
                    print("\nConexión WebSocket establecida (welcome)")
                    self.gui.despliega_mensaje_rx("Conexión WebSocket establecida (welcome)")
                elif data.get("type") == "confirm_subscription":
                    identifier = json.loads(data.get("identifier", "{}"))
                    mia_id = identifier.get("mia_id")
                    print(f"\nSuscripción confirmada al canal {mia_id}") 
                    self.gui.despliega_mensaje_rx(f"Suscripción confirmada al canal {mia_id}")
                #elif data.get("message"):
                elif data.get("message") and data.get("type") is None:
                    self.keep_alive = False
                    print("\nMensaje recibido:", time.strftime("%H:%M:%S"), data["message"])
                    self.gui.despliega_mensaje_rx(f"{data.get('message')}")
                    if data.get("message", {}).get("accion") == "INICIA_FOLIO":
                        self.gui.sorteo.inicia_conteo()
                else:
                    print("\nMensaje desconocido:", data)
                    self.gui.despliega_mensaje_rx(f"Mensaje desconocido: {data}\n" )
            except websockets.exceptions.ConnectionClosedError as e:
                print("\nConexión cerrada:", e)
                self.gui.despliega_mensaje_tx("Conexión cerrada, intenta reconectar...\n")
                # Intentar reconectar después de unos segundos
                self.gui.conectado = False
                self.gui.supervisa_conexion()
                await asyncio.sleep(5)
                await self.desconecta_async()
                await self.conecta_async(self.mesa_id)
                break

    async def suscribe(self, mesa_id): 
        mensaje_suscribir = {
            "command": "subscribe",
            "identifier": json.dumps({"channel": "MiaChannel", "mia_id": mesa_id})
        }
        try:
            await self.socket_activo.send(json.dumps(mensaje_suscribir))
            print(f"Suscribiéndose al canal MiaChannel: {mesa_id}")
            self.gui.despliega_mensaje_tx(f"Suscribiéndose al canal MiaChannel: {mesa_id}")
            return True  # Indica éxito 
        except Exception as e:
            print(f"Error al enviar el mensaje de suscripción: {e}")
            self.gui.despliega_mensaje_tx(f"Error al enviar el mensaje de su suscripción: {e}\n")
            return False
        
    def convierte_url(self, url):
        """
        Convierte la URL de la GUI a un formato adecuado para el WebSocket.
        """
        if url == "LOCAL":
            return URL_MEZTLI
        elif url == "RAILS Simula":
            return URL_SIMULADOR
        elif url == "RAILS QB":
            return "URL_MEZTLI"  # Aquí se agrega la URL específica para RAILS QB
