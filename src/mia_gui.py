import tkinter as tk
from tkinter import PhotoImage
from PIL import Image, ImageTk  # Importar Pillow par
from tkinter import scrolledtext
from mia_websocket import WebSocketMia
from mia_contadores import ContadorPiezas
import asyncio


class MiaGui:
    def __init__(self):
        self.root = tk.Tk()

        self.root.title("Wong Instruments             MIA - Simulación            Ver_2.0")
        
        # Cargar y redimensionar la imagen del logo
        original_logo = Image.open("wi_logo_1.png")  # Reemplaza con la ruta de tu imagen
        resized_logo = original_logo.resize((60, 60))  # Cambia el tamaño a 100x100 píxeles
        self.logo = ImageTk.PhotoImage(resized_logo)  # Convertir a un formato compatible con Tkinter
        # Crear un Label para mostrar el logo
        logo_label = tk.Label(self.root, image=self.logo)
        logo_label.pack(side=tk.LEFT, pady=5, padx=10)  # Coloca el logo
        
        self.contador = ContadorPiezas(self)
        self.websocket_mia = WebSocketMia(self, self.contador) 
        self.create_widgets()
        self.inicia_conteo = False
        self.detiene_conteo = False
        

    def create_widgets(self):
        # Frame principal para organizar text areas y el frame de variables
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame para la etiqueta y el Canvas
        signal_frame = tk.Frame(main_frame)
        signal_frame.pack(side=tk.TOP, anchor=tk.NW, padx=5, pady=(5, 0))
        
        # Etiqueta para el Canvas
        tk.Label(signal_frame, text="Conexión", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))
        # Canvas para la señal visual en la parte superior izquierda
        self.signal_canvas = tk.Canvas(signal_frame, width=20, height=20, bg=main_frame.cget("bg"), highlightthickness=0)
        self.signal_canvas.pack(side=tk.LEFT)
        self.signal_circle = self.signal_canvas.create_oval(2, 2, 18, 18, fill="gray", outline="")  # Círculo inicial (apagado)
        self.signal_circle = self.signal_canvas.create_oval(4, 4, 16, 16, fill="gray", outline="")  # Círculo inicial (apagado)

        # Sub-frame para los text areas
        text_frame = tk.Frame(main_frame)
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Título y text_area_tx
        tk.Label(text_frame, text="Tx al servidor SysQB", font=("Arial", 10)).pack(pady=(0, 5))
        self.text_area_tx = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=50, height=6, font=("Arial", 10))
        self.text_area_tx.pack(pady=(0, 10), padx=(10, 10))
        # Agregar margen interno al texto
        self.text_area_tx.tag_configure("margin", lmargin1=10, lmargin2=10, rmargin=10)
        self.text_area_tx.insert("1.0", " ", "margin")  # Aplicar la configuración de margen

        # Título y text_area_rx
        tk.Label(text_frame, text="Rx del servidor SysQB", font=("Arial", 10)).pack(pady=(0, 5))
        self.text_area_rx = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=50, height=6, font=("Arial", 10))
        self.text_area_rx.pack(pady=(0, 10), padx=(10, 10))
        # Agregar margen interno al texto
        self.text_area_rx.tag_configure("margin", lmargin1=10, lmargin2=10, rmargin=10)
        self.text_area_rx.insert("1.0", " ", "margin")  # Aplicar la configuración de margen

        # Frame para desplegar variables
        variable_frame = tk.Frame(main_frame, relief=tk.GROOVE, borderwidth=2)
        variable_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)

        tk.Label(variable_frame, text="SORTEO", font=("Arial", 12, "bold")).pack(pady=(10, 5))

        # Etiqueta y campo de texto para "Mesa No."
        mesa_container = tk.Frame(variable_frame)
        mesa_container.pack(pady=30, fill=tk.X)
        self.mesa_label = tk.Label(mesa_container, text="Mesa No.", font=("Arial", 12))
        self.mesa_label.pack(side=tk.LEFT, padx=5)
        self.mesa_entry = tk.Entry(mesa_container, font=("Arial", 14), width=4)
        self.mesa_entry.pack(side=tk.RIGHT, padx=5)
        self.mesa_entry.insert(0, " 1")  # Establecer el valor predeterminado a 1

        # Etiqueta y campo de texto para "Piezas OK"
        pza_ok_container = tk.Frame(variable_frame)
        pza_ok_container.pack(pady=5, fill=tk.X)
        self.pza_ok_label = tk.Label(pza_ok_container, text="Piezas OK", font=("Arial", 12))
        self.pza_ok_label.pack(side=tk.LEFT, padx=5)
        self.pza_ok_entry = tk.Entry(pza_ok_container, font=("Arial", 14), width=8)
        self.pza_ok_entry.pack(side=tk.RIGHT, padx=5)

        # Etiqueta y campo de texto para "Piezas NG"
        pza_ng_container = tk.Frame(variable_frame)
        pza_ng_container.pack(pady=5, fill=tk.X)
        self.pza_ng_label = tk.Label(pza_ng_container, text="Piezas NG", font=("Arial", 12))
        self.pza_ng_label.pack(side=tk.LEFT, padx=5)
        self.pza_ng_entry = tk.Entry(pza_ng_container, font=("Arial", 14), width=8)
        self.pza_ng_entry.pack(side=tk.RIGHT, padx=5)
        
        # Crear un contenedor para los botones
        conteo_buttons_frame = tk.Frame(variable_frame)
        conteo_buttons_frame.pack(side=tk.BOTTOM, pady=10, anchor=tk.CENTER)

        # Botón para iniciar el conteo
        self.inic_conteo_button = tk.Button(conteo_buttons_frame, text="INIC", command=self.inicia_conteo)
        self.inic_conteo_button.pack(side=tk.LEFT, padx=5)  # Alinear a la izquierda con un espacio entre botones

        # Botón para detener el conteo
        self.detiene_conteo_button = tk.Button(conteo_buttons_frame, text="ALTO/CONTINÚA", command=self.detiene_conteo)
        self.detiene_conteo_button.pack(side=tk.LEFT, padx=5)  # Alinear a la izquierda con un espacio entre botones

        # Crear un frame para los botones
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, pady=5)

        # Botón Disconnect a la extrema izquierda
        self.disconnect_button = tk.Button(button_frame, text="Desconecta", command=self.disconnect_websocket)
        self.disconnect_button.pack(side=tk.LEFT, padx=20, pady=5)

        # Botón Connect 
        self.connect_button = tk.Button(button_frame, text="Conecta", command=self.connect_websocket)
        self.connect_button.pack(side=tk.LEFT, padx=20, pady=5)

    def despliega_mensaje_tx(self, mensaje):
        self.text_area_tx.insert("1.0", mensaje + "\n", "margin")

    def despliega_mensaje_rx(self, mensaje):
        self.text_area_rx.insert("1.0", mensaje + "\n", "margin")

    def despliega_ok(self, ok):
        self.pza_ok_entry.delete(0, tk.END)
        self.pza_ok_entry.insert(0, ok)

    def despliega_ng(self, ng):
        self.pza_ng_entry.delete(0, tk.END)
        self.pza_ng_entry.insert(0, ng)
        
    def despliega_mesa(self, mesa):
        self.pza_mesa_entry.delete(0, tk.END)
        self.pza_mesa_entry.insert(0, mesa)
    
    def lee_mesa(self):
        try:
            return int(self.mesa_entry.get().strip())  # Convierte a entero y elimina espacios en blanco
        except ValueError:
            return 1  # Valor predeterminado si no es un número válido
    
    def inicia_conteo(self):
        self.inicia_conteo = True
        self.contador.inicia_contadores()

    def detiene_conteo(self):
        self.detiene_conteo = not self.detiene_conteo


    def connect_websocket(self):
        self.websocket_mia.connect()
        # Cambiar el color del círculo a verde (encendido)
        self.signal_canvas.itemconfig(self.signal_circle, fill="lime")
        
    def disconnect_websocket(self):
        self.websocket_mia.disconnect()
        # Cambiar el color del círculo a gris (apagado)
        self.signal_canvas.itemconfig(self.signal_circle, fill="gray")
         
    def run(self):
        self.root.mainloop()
