import tkinter as tk
from tkinter import ttk
from tkinter import PhotoImage
from PIL import Image, ImageTk  
from tkinter import scrolledtext
from mia_websocket import WebSocketMia
from mia_sorteo import ManejadorSorteo
import asyncio


class MiaGui:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Wong Instruments             MIA - Simulación            Ver 3.1")
        
        # Carga y redimensiona la imagen del logo
        original_logo = Image.open("wi_logo_1.png")  # Reemplaza con la ruta de tu imagen
        resized_logo = original_logo.resize((60, 60))  # Cambia el tamaño a 100x100 píxeles
        self.logo = ImageTk.PhotoImage(resized_logo)  # Convertir a un formato compatible con Tkinter
        
        # Crea una etiqueta para mostrar el logo
        logo_label = tk.Label(self.root, image=self.logo)
        logo_label.pack(side=tk.LEFT, pady=5, padx=10)  # Coloca el logo
        
        self.websocket_mia = WebSocketMia(self) 
        self.sorteo = ManejadorSorteo(self)
        self.inicia_conteo = False
        self.detiene_conteo = False
        self.sysqb_socket = None
        self.mesa_id = "MIA-01"  # ID de la mesa por omisión
        self.create_widgets()
        
    def create_widgets(self):

        # Contenedor principal para organizar las áreas de texto y los botones de sorteo de piezas
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Sub-frame para las áreas de texto
        text_frame = tk.Frame(main_frame)
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(30, 0))

        # Título y área de TX
        tk.Label(text_frame, text="Tx al servidor SysQB", font=("Arial", 14)).pack(pady=(0, 5))
        self.text_area_tx = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=42, height=15, font=("Arial", 12))
        self.text_area_tx.pack(pady=(0, 10), padx=(10, 10))
        # Agrega margen interno al texto
        self.text_area_tx.tag_configure("margin", lmargin1=10, lmargin2=10, rmargin=10)
        self.text_area_tx.insert("1.0", " ", "margin")  # Aplicar la configuración de margen

        # Título y área de RX
        tk.Label(text_frame, text="Rx del servidor SysQB", font=("Arial", 14)).pack(pady=(0, 5))
        self.text_area_rx = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=42, height=15, font=("Arial", 12))
        self.text_area_rx.pack(pady=(0, 10), padx=(10, 10))
        # Agrega margen interno al texto
        self.text_area_rx.tag_configure("margin", lmargin1=10, lmargin2=10, rmargin=10)
        self.text_area_rx.insert("1.0", " ", "margin")  # Aplicar la configuración de margen

        # Sub-frame para la señal de conexión
        signal_frame = tk.Frame(text_frame)
        signal_frame.pack(side=tk.TOP, anchor=tk.NW, padx=5, pady=(5, 0))
        
        # Etiqueta para la señal de conexión
        tk.Label(signal_frame, text="Conexión", font=("Arial", 12)).pack(side=tk.LEFT, padx=(0, 5))
        # Lienzo para dibujar la sennal de conexión (superior izquierda)
        self.signal_canvas = tk.Canvas(signal_frame, width=20, height=20, bg=main_frame.cget("bg"), highlightthickness=0)
        self.signal_canvas.pack(side=tk.LEFT)
        self.signal_circle = self.signal_canvas.create_oval(2, 2, 18, 18, fill="gray", outline="")  # Círculo inicial (apagado)
        self.signal_circle = self.signal_canvas.create_oval(4, 4, 16, 16, fill="gray", outline="")  # Círculo inicial (apagado)

        # Función de respuesta (callback) para el tacto de las cajitas de sorteo
        def make_incrementa_callback(idx):
            return lambda event: self.sorteo.incrementa_contador(idx)
        # Función de respuesta (callback) para el tacto de los botones de tipo de incidente asociados a NG-MIX
        def make_circulo_boton_callback(idx):
            return lambda event: self.circulo_boton_callback(idx)

        # Sub-frame para el despliegue de las cajitas y botoneras de sorteo (OK, NG-nn)
        variable_frame = tk.Frame(main_frame, relief=tk.GROOVE, borderwidth=2)
        variable_frame.pack(side=tk.RIGHT, fill=tk.Y, pady=(15, 0), padx=20)

        # Etiqueta, cajita y contador para "PIEZA"
        pieza_container = tk.Frame(variable_frame)
        pieza_container.pack(pady=5, fill=tk.X)
        self.pieza_label = tk.Label(pieza_container, text="PIEZA No.", font=("Arial", 16))
        self.pieza_label.pack(side=tk.LEFT, padx=5)
        self.pieza_entry = tk.Entry(pieza_container, font=("Arial", 24), width=8)
        self.pieza_entry.pack(side=tk.RIGHT, padx=5)
        self.pieza_entry.insert(0, f"{self.sorteo.pieza_numero:>10}")

        # Checkboxes para multiplicadores X1, X10 y X100
        multiplicador_frame = tk.Frame(variable_frame)
        multiplicador_frame.pack(pady=(0, 5), fill=tk.X)
        self.multiplicador_var = tk.IntVar(value=1)

        radio_x1 = tk.Radiobutton(multiplicador_frame, text="x1", variable=self.multiplicador_var, value=1)
        radio_x10 = tk.Radiobutton(multiplicador_frame, text="x10", variable=self.multiplicador_var, value=10)
        radio_x100 = tk.Radiobutton(multiplicador_frame, text="x100", variable=self.multiplicador_var, value=100)

        radio_x1.pack(side=tk.LEFT, padx=10)
        radio_x10.pack(side=tk.LEFT, padx=10)
        radio_x100.pack(side=tk.LEFT, padx=10)

        # Actualiza la variable multiplicador_valor al cambiar el valor del "radiobutton"
        self.multiplicador_valor = self.multiplicador_var.get()
        def actualiza_multiplicador(*args):
            self.multiplicador_valor = self.multiplicador_var.get()
        self.multiplicador_var.trace_add("write", lambda *args: actualiza_multiplicador())

        # Etiqueta, cajita y contador para "Piezas OK"
        pza_ok_container = tk.Frame(variable_frame)
        pza_ok_container.pack(pady=10, fill=tk.X)
        self.pza_ok_label = tk.Label(pza_ok_container, text="Piezas OK", font=("Arial", 12))
        self.pza_ok_label.pack(side=tk.LEFT, padx=5)
        self.pza_ok_entry = tk.Entry(pza_ok_container, font=("Arial", 16), width=8)
        self.pza_ok_entry.pack(side=tk.RIGHT, padx=5)
        ok_btn = tk.Canvas(pza_ok_container, width=28, height=28, bg=variable_frame.cget("bg"), highlightthickness=0, cursor="hand2")
        ok_btn.pack(side=tk.RIGHT, padx=5)
        rect_ok_1 = ok_btn.create_rectangle(2, 2, 26, 26, fill="#7CBB00", outline="")
        rect_ok_2 = ok_btn.create_rectangle(6, 6, 22, 22, fill="white", outline="")
        ok_btn.bind("<Button-1>", make_incrementa_callback(0))
        
        # Crea el efecto "Hover" para la cajita de "Piezas OK"
        def on_ok_hover(event):
            ok_btn.itemconfig(rect_ok_2, fill="#A6E22E")  # Verde más claro al pasar el ratón
        def on_ok_leave(event): 
            ok_btn.itemconfig(rect_ok_2, fill="white")  # Color original al salir
        ok_btn.bind("<Enter>", on_ok_hover)
        ok_btn.bind("<Leave>", on_ok_leave)

        # Etiqueta, cajita y contador para "Piezas NG-1"
        pza_ng_container = tk.Frame(variable_frame)
        pza_ng_container.pack(pady=5, fill=tk.X)
        self.pza_ng_label = tk.Label(pza_ng_container, text="Piezas NG-1", font=("Arial", 12))
        self.pza_ng_label.pack(side=tk.LEFT, padx=5)
        self.pza_ng_entry = tk.Entry(pza_ng_container, font=("Arial", 16), width=8)
        self.pza_ng_entry.pack(side=tk.RIGHT, padx=5)
        ng1_btn = tk.Canvas(pza_ng_container, width=28, height=28, bg=variable_frame.cget("bg"), highlightthickness=0, cursor="hand2")
        ng1_btn.pack(side=tk.RIGHT, padx=5)
        ng1_btn.create_rectangle(2, 2, 26, 26, fill="#F65314", outline="")
        rect_ng1 = ng1_btn.create_rectangle(6, 6, 22, 22, fill="white", outline="")
        ng1_btn.bind("<Button-1>", make_incrementa_callback(1))
        
        # Crea el efecto "Hover" para la cajita de "Piezas NG-1"
        def on_ng1_hover(event):
            ng1_btn.itemconfig(rect_ng1, fill="#FB9D78")  # Rojo más claro al pasar el ratón
        def on_ng1_leave(event): 
            ng1_btn.itemconfig(rect_ng1, fill="white")  # Color original al salir 
        ng1_btn.bind("<Enter>", on_ng1_hover)
        ng1_btn.bind("<Leave>", on_ng1_leave)
        
        # Etiqueta, cajita y contador para "Piezas NG-2"
        pza_ng_container_2 = tk.Frame(variable_frame)
        pza_ng_container_2.pack(pady=5, fill=tk.X)
        self.pza_ng_label_2 = tk.Label(pza_ng_container_2, text="Piezas NG-2", font=("Arial", 12))
        self.pza_ng_label_2.pack(side=tk.LEFT, padx=5)
        self.pza_ng_entry_2 = tk.Entry(pza_ng_container_2, font=("Arial", 16), width=8)
        self.pza_ng_entry_2.pack(side=tk.RIGHT, padx=5)
        ng2_btn = tk.Canvas(pza_ng_container_2, width=28, height=28, bg=variable_frame.cget("bg"), highlightthickness=0, cursor="hand2")
        ng2_btn.pack(side=tk.RIGHT, padx=5)
        ng2_btn.create_rectangle(2, 2, 26, 26, fill="#F65314", outline="")
        rect_ng2 = ng2_btn.create_rectangle(6, 6, 22, 22, fill="white", outline="")
        ng2_btn.bind("<Button-1>", make_incrementa_callback(2))
        
        # Crea el efecto "Hover" para la cajita de "Piezas NG-2"
        def on_ng2_hover(event):
            ng2_btn.itemconfig(rect_ng2, fill="#FB9D78")  # Rojo más claro al pasar el mouse
        def on_ng2_leave(event): 
            ng2_btn.itemconfig(rect_ng2, fill="white")  # Color original al salir
        ng2_btn.bind("<Enter>", on_ng2_hover)
        ng2_btn.bind("<Leave>", on_ng2_leave)
        
        # Etiqueta, cajita y contador para "Piezas NG-3"
        pza_ng_container_3 = tk.Frame(variable_frame)
        pza_ng_container_3.pack(pady=5, fill=tk.X)
        self.pza_ng_label_3 = tk.Label(pza_ng_container_3, text="Piezas NG-3", font=("Arial", 12))
        self.pza_ng_label_3.pack(side=tk.LEFT, padx=5)
        self.pza_ng_entry_3 = tk.Entry(pza_ng_container_3, font=("Arial", 16), width=8)
        self.pza_ng_entry_3.pack(side=tk.RIGHT, padx=5)
        ng3_btn = tk.Canvas(pza_ng_container_3, width=28, height=28, bg=variable_frame.cget("bg"), highlightthickness=0, cursor="hand2")
        ng3_btn.pack(side=tk.RIGHT, padx=5)
        ng3_btn.create_rectangle(2, 2, 26, 26, fill="#F65314", outline="")
        rect_ng3 = ng3_btn.create_rectangle(6, 6, 22, 22, fill="white", outline="")
        ng3_btn.bind("<Button-1>", make_incrementa_callback(3))
        
        # Crea el efecto "Hover" para la cajita de "Piezas NG-3"
        def on_ng3_hover(event):
            ng3_btn.itemconfig(rect_ng3, fill="#FB9D78")  # Rojo más claro al pasar el ratón
        def on_ng3_leave(event): 
            ng3_btn.itemconfig(rect_ng3, fill="white")  # Color original al salir 
        ng3_btn.bind("<Enter>", on_ng3_hover)
        ng3_btn.bind("<Leave>", on_ng3_leave)
        
        # Etiqueta, cajita y contador para "Piezas NG-4"
        pza_ng_container_4 = tk.Frame(variable_frame)
        pza_ng_container_4.pack(pady=5, fill=tk.X)
        self.pza_ng_label_4 = tk.Label(pza_ng_container_4, text="Piezas NG-4", font=("Arial", 12))
        self.pza_ng_label_4.pack(side=tk.LEFT, padx=5)
        self.pza_ng_entry_4 = tk.Entry(pza_ng_container_4, font=("Arial", 16), width=8)
        self.pza_ng_entry_4.pack(side=tk.RIGHT, padx=5)
        ng4_btn = tk.Canvas(pza_ng_container_4, width=28, height=28, bg=variable_frame.cget("bg"), highlightthickness=0, cursor="hand2")
        ng4_btn.pack(side=tk.RIGHT, padx=5)
        ng4_btn.create_rectangle(2, 2, 26, 26, fill="#F65314", outline="")
        rect_ng4 = ng4_btn.create_rectangle(6, 6, 22, 22, fill="white", outline="")
        ng4_btn.bind("<Button-1>", make_incrementa_callback(4))
        
        # Crea el efecto "Hover" para la cajita de "Piezas NG-4"
        def on_ng4_hover(event):
            ng4_btn.itemconfig(rect_ng4, fill="#FB9D78")  # Rojo más claro al pasar el ratón
        def on_ng4_leave(event): 
            ng4_btn.itemconfig(rect_ng4, fill="white")  # Color original al salir
        ng4_btn.bind("<Enter>", on_ng4_hover)
        ng4_btn.bind("<Leave>", on_ng4_leave)
        
        # Etiqueta, cajita y contador para "Piezas NG-5"
        pza_ng_container_5 = tk.Frame(variable_frame)
        pza_ng_container_5.pack(pady=5, fill=tk.X)
        self.pza_ng_label_5 = tk.Label(pza_ng_container_5, text="Piezas NG-5", font=("Arial", 12))
        self.pza_ng_label_5.pack(side=tk.LEFT, padx=5)
        self.pza_ng_entry_5 = tk.Entry(pza_ng_container_5, font=("Arial", 16), width=8)
        self.pza_ng_entry_5.pack(side=tk.RIGHT, padx=5)
        ng5_btn = tk.Canvas(pza_ng_container_5, width=28, height=28, bg=variable_frame.cget("bg"), highlightthickness=0, cursor="hand2")
        ng5_btn.pack(side=tk.RIGHT, padx=5)
        ng5_btn.create_rectangle(2, 2, 26, 26, fill="#F65314", outline="")
        rect_ng5 = ng5_btn.create_rectangle(6, 6, 22, 22, fill="white", outline="")
        ng5_btn.bind("<Button-1>", make_incrementa_callback(5))
        
        # Crea el efecto "Hover" para la cajita de "Piezas NG-5"
        def on_ng5_hover(event):
            ng5_btn.itemconfig(rect_ng5, fill="#FB9D78")  # Rojo más claro al pasar el ratón
        def on_ng5_leave(event): 
            ng5_btn.itemconfig(rect_ng5, fill="white")  # Color original al salir
        ng5_btn.bind("<Enter>", on_ng5_hover)
        ng5_btn.bind("<Leave>", on_ng5_leave)
        
        # Etiqueta, cajita y contador para "Piezas NG-MIX"
        pza_ng_container_mix = tk.Frame(variable_frame)
        pza_ng_container_mix.pack(pady=20, fill=tk.X)
        self.pza_ng_label_mix = tk.Label(pza_ng_container_mix, text="Piezas NG-MIX", font=("Arial", 12))
        self.pza_ng_label_mix.pack(side=tk.LEFT, padx=5)
        self.pza_ng_entry_mix = tk.Entry(pza_ng_container_mix, font=("Arial", 16), width=8)
        self.pza_ng_entry_mix.pack(side=tk.RIGHT, padx=5)
        ngmix_btn = tk.Canvas(pza_ng_container_mix, width=28, height=28, bg=variable_frame.cget("bg"), highlightthickness=0, cursor="hand2")
        ngmix_btn.pack(side=tk.RIGHT, padx=5)
        ngmix_btn.create_rectangle(2, 2, 26, 26, fill="#BB10F9", outline="")
        rect_ngmix = ngmix_btn.create_rectangle(6, 6, 22, 22, fill="white", outline="")
        ngmix_btn.bind("<Button-1>", make_incrementa_callback(6))
        
        # Crea el efecto "Hover" para la cajita de "Piezas NG-MIX"
        def on_ngmix_hover(event):
            ngmix_btn.itemconfig(rect_ngmix, fill="#DA78FB")  # Violeta más claro al pasar el mouse
        def on_ngmix_leave(event): 
            ngmix_btn.itemconfig(rect_ngmix, fill="white")  # Color original al salir
        ngmix_btn.bind("<Enter>", on_ngmix_hover)
        ngmix_btn.bind("<Leave>", on_ngmix_leave)

        # Sub-frame para los lienzos donde dibujar los focos indicadores de incidentes múltiples 
        self.focos_lienzos = []
        self.focos_dibujos = []
        circulos_frame = tk.Frame(variable_frame)
        circulos_frame.pack(pady=(10, 0))

        for i in range(5):
            canvas = tk.Canvas(circulos_frame, width=24, height=24, bg=main_frame.cget("bg"), highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=7)
            # Primer óvalo (amarillo, borde exterior)
            circulo_ext = canvas.create_oval(2, 2, 22, 22, fill="gray", outline="")
            # Segundo óvalo (gris, interior)
            circulo_interior = canvas.create_oval(6, 6, 20, 20, fill="gray", outline="")
            self.focos_lienzos.append(canvas)
            self.focos_dibujos.append((circulo_ext, circulo_interior))
        
        # Sub-frame para los lienzos donde dibujar los botones que seleccionan incidentes múltiples
        self.boton_circular_dibujos = []
        self.boton_circular_lienzos = []
        circulos_botones_frame = tk.Frame(variable_frame)
        circulos_botones_frame.pack(pady=(0, 10))

        for i in range(5):
            canvas_btn = tk.Canvas(circulos_botones_frame, width=24, height=24, bg=main_frame.cget("bg"), highlightthickness=0, cursor="hand2")
            canvas_btn.pack(side=tk.LEFT, padx=7)
            # Círculo exterior (azul claro)
            circulo_ext = canvas_btn.create_oval(2, 2, 22, 22, fill="#1094F9", outline="")
            # Círculo interior (blanco)
            circulo_interior = canvas_btn.create_oval(6, 6, 18, 18, fill="white", outline="")
            canvas_btn.bind("<Button-1>", make_circulo_boton_callback(i))
            self.boton_circular_dibujos.append((circulo_ext, circulo_interior))
            self.boton_circular_lienzos.append(canvas_btn)

        # Sub-frame para los botones de INIC y DETENER/CONTINUAR
        conteo_buttons_frame = tk.Frame(variable_frame)
        conteo_buttons_frame.pack(side=tk.BOTTOM, pady=30, anchor=tk.CENTER)

        # Botón para iniciar el conteo
        self.inic_conteo_button = tk.Button(conteo_buttons_frame, text="INICIA ", command=self.sorteo.inicia_conteo)
        self.inic_conteo_button.pack(side=tk.LEFT, padx=5)  # Alinear a la izquierda con un espacio entre botones

        # Botón para detener el conteo
        #self.detiene_conteo_button = tk.Button(conteo_buttons_frame, text="--------", command=self.sorteo.detiene_conteo)
        self.detiene_conteo_button = tk.Button(conteo_buttons_frame, text="TERMINA", command=self.sorteo.fin_conteo)
        self.detiene_conteo_button.pack(side=tk.LEFT, padx=5)  # Alinear a la izquierda con un espacio entre botones

        # Contenedor para los botones de Desconecta, Conecta y No. de Mesa
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, pady=30)

        # Botón Desconecta a la extrema izquierda (columna 0)
        style = ttk.Style()
        style.configure("Red.TButton", foreground="gray", font=("Arial", 14, "bold"))
        self.disconnect_button = ttk.Button(button_frame, text="Desconecta", command=self.desconecta_sysqb, style="Red.TButton")
        self.disconnect_button.grid(row=0, column=0, padx=20, pady=5, sticky="e")

        # Etiqueta, cajita y contador para "Mesa No." (columna 1)
        mesa_container = tk.Frame(button_frame)
        mesa_container.grid(row=0, column=1, padx=20, pady=5)
        self.mesa_label = tk.Label(mesa_container, text="Mesa No.", font=("Arial", 14))
        self.mesa_label.pack(side=tk.LEFT, padx=5)
        self.mesa_entry = tk.Entry(mesa_container, font=("Arial", 14), width=4)
        self.mesa_entry.pack(side=tk.RIGHT, padx=5)
        self.mesa_entry.insert(0, " 1")  # Establecer el valor predeterminado a 1

        # Botón Conecta a la extrema derecha (columna 2) 
        style.configure("Green.TButton", foreground="#1094F9", font=("Arial", 14, "bold"))
        self.connect_button = ttk.Button(button_frame, text="Conecta con SysQB", command=self.conecta_sysqb, style="Green.TButton")
        self.connect_button.grid(row=0, column=2, padx=20, pady=5, sticky="e")

    # Actualiza la cajita de PIEZA No. y la cajita de sorteo accionada
    def actualiza_cajitas(self, pieza_numero, idx):
        entrys = [
            self.pza_ok_entry,
            self.pza_ng_entry,
            self.pza_ng_entry_2,
            self.pza_ng_entry_3,
            self.pza_ng_entry_4,
            self.pza_ng_entry_5,
            self.pza_ng_entry_mix
        ]
        self.pieza_entry.insert(0, f"{pieza_numero:>10}")
        entrys[idx].delete(0, 'end')
        entrys[idx].insert(0, f"{self.sorteo.contadores_cajitas[idx]:>10}")

    #  Función de respuesta al toque para los botones de tipo de incidente ("callback")
    def circulo_boton_callback(self, idx):
        print(f"Botón circular {idx+1} presionado")
       # Cambia el color del círculo interno superior correspondiente
        canvas = self.focos_lienzos[idx]
        circulo_ext, circulo_interior = self.focos_dibujos[idx]
        current_color = canvas.itemcget(circulo_interior, "fill")
        if current_color == "yellow":
            canvas.itemconfig(circulo_interior, fill="gray")
            self.sorteo.estado_botones_inci[idx] = False
        else:
            canvas.itemconfig(circulo_interior, fill="yellow")
            self.sorteo.estado_botones_inci[idx] = True

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

    def despliega_continuar(self):
        self.detiene_conteo_button.config(text="CONTINUAR")
       
    def despliega_detener(self):    
        self.detiene_conteo_button.config(text="\u00A0-DETENER-\u00A0")
    
    def limpia_cajitas(self):  
        entrys = [
            self.pza_ok_entry,
            self.pza_ng_entry,
            self.pza_ng_entry_2,
            self.pza_ng_entry_3,
            self.pza_ng_entry_4,
            self.pza_ng_entry_5,
            self.pza_ng_entry_mix
        ]
        self.pieza_entry.insert(0, f"{self.sorteo.pieza_numero:>10}")
        for idx in range(len(entrys)):
            entrys[idx].delete(0, 'end')
            entrys[idx].insert(0, f"{self.sorteo.contadores_cajitas[idx]:>10}")
         
    def lee_mesa(self):
        try:
            return int(self.mesa_entry.get().strip())  # Convierte a entero y elimina espacios en blanco
        except ValueError:
            return 1  # Valor predeterminado si no es un número válido

    def connect_websocket(self):
        self.websocket_mia.connect()
        # Cambia el color del círculo a amarillo (encendido)
        self.signal_canvas.itemconfig(self.signal_circle, fill="#F9F110")
    
    def conecta_sysqb(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self._conecta_sysqb_async())
       
    async def _conecta_sysqb_async(self):
        self.sysqb_socket = await self.websocket_mia.conecta_async()
        self.mesa_id = "MIA-" + str(self.lee_mesa()).zfill(2)  # Formato "MIA-01"
        suscripcion = await self.websocket_mia.suscribe(self.sysqb_socket, self.mesa_id)
        if not suscripcion:
            return
        # Cambia el color del círculo a amarillo (encendido)
        self.signal_canvas.itemconfig(self.signal_circle, fill="yellow")

    def desconecta_sysqb(self):
        # Detiene el conteo
        self.detiene_conteo = True
        self.inicia_conteo = False
        #self.despliega_continuar()
        
        # Cierra WebSocket
        loop = asyncio.get_event_loop()
        loop.create_task(self._desconecta_sysqb_async())
    
    async def _desconecta_sysqb_async(self): 
        # Desconecta el WebSocket
        await self.websocket_mia.desconecta_async(self.sysqb_socket)
        
        # Cambia el color del círculo a gris (apagado)
        self.signal_canvas.itemconfig(self.signal_circle, fill="gray")

    # Para mantener el bucle de eventos de asyncio en Tkinter y procesar tareas pendientes
    # que fueron creadas con loop.create.task
    def _asyncio_loop(self, loop):
        try:
            loop.call_soon(loop.stop)
            loop.run_forever()
        finally:
            self.root.after(10, self._asyncio_loop, loop)

    def run(self):
        loop = asyncio.get_event_loop()
        self._asyncio_loop(loop)
        self.root.mainloop()
