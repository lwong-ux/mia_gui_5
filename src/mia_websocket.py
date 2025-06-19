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
        self.gui = gui
        self.ws = None
        self.is_running = False
       
    async def conecta_async(self):
        # Conexión al WebSocket de Rails
        try:
            sysqb_socket = await websockets.connect(self.url, ping_interval=20, ping_timeout=10)
            print("🔌 Conectado al WebSocket de Rails\n")
            self.gui.despliega_mensaje_tx("\n🔌 Conectado al WebSocket de Rails")

            # Inicia la tarea para leer mensajes del servidor SysQB
            asyncio.create_task(self.lector_websocket(sysqb_socket))
            return sysqb_socket
           
        except Exception as e:
            print(f"❌ Error al conectar al WebSocket de Rails: {e}")
            self.gui.despliega_mensaje_tx(f"Error al conectar al SysQB WebSocket: {e}\n")
            return None
    
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
            print("📡 Enviado:", mensaje)
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
                    print("📡 Keep-Alive recibido del servidor")
                    try:
                        await sysqb_socket.send(json.dumps({"type": "pong"}))
                        print("📡 Pong enviado al servidor")
                    except Exception as e:
                        print("❌ Error al enviar pong:", e)
                elif data.get("message"):
                    print("📡 Mensaje recibido:", data["message"])
                    self.gui.despliega_mensaje_rx(f"📡  {data.get('message')}")
                # Puedes agregar más tipos de mensajes aquí si lo necesitas
            except websockets.exceptions.ConnectionClosedError as e:
                print("❌ Conexión cerrada:", e)
                self.gui.despliega_mensaje_tx("❌ Conexión cerrada, intenta reconectar...\n")
                break

    async def suscribe(self, sysqb_socket, mesa_id): 
        mensaje_suscribir = {
            "command": "subscribe",
            "identifier": json.dumps({"channel": "MiaChannel", "mia_id": mesa_id})
        }
        try:
            await sysqb_socket.send(json.dumps(mensaje_suscribir))
            print(f"🔗  Suscrito al canal MiaChannel: {mesa_id}")
            self.gui.despliega_mensaje_tx(f"🔗  Suscrito al canal MiaChannel: {mesa_id}\n")
            return True  # Indica éxito 
        except Exception as e:
            print(f"❌ Error al enviar el mensaje de suscripción: {e}")
            self.gui.despliega_mensaje_tx(f"❌ Error al enviar el mensaje de su suscripción: {e}\n")
            return False
