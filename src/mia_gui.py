import tkinter as tk
from tkinter import ttk
from tkinter import PhotoImage
import tkinter.font as tkfont
from PIL import Image, ImageTk, ImageOps
from tkinter import messagebox, scrolledtext
from mia_websocket import WebSocketMia
from mia_sorteo import ManejadorSorteo
from mia_portal import ManejadorPortal
import asyncio
import psutil
import random
import os


class MiaGui:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Wong Instruments             MIA - Portal             Ver 5.6") 
        self.root.bind("<Escape>", lambda e: self.root.attributes("-fullscreen", False))
        
        # Carga y redimensiona la imagen del logo
        self.base_dir = os.path.dirname(os.path.abspath(__file__))  # Obtiene el directorio actual del archivo
        original_logo = Image.open(os.path.join(self.base_dir, "wi_logo_1.png"))  # Reemplaza con la ruta de tu imagen
        resized_logo = original_logo.resize((60, 60))  # Cambia el tamaño a 100x100 píxeles
        self.logo = ImageTk.PhotoImage(resized_logo)  # Convertir a un formato compatible con Tkinter
        
        # Crea una etiqueta para mostrar el logo
        logo_label = tk.Label(self.root, image=self.logo)
        logo_label.pack(side=tk.LEFT, pady=5, padx=10)  # Coloca el logo
        
        self.url_var = tk.StringVar(value="ws://192.168.100.25:3000/cable")  # <--- Agrega esto aquí
        self.websocket_mia = WebSocketMia(self) 
        self.sorteo = ManejadorSorteo(self)
        self.portal = ManejadorPortal(self.sorteo)
        self.inicia_conteo = False
        self.detiene_conteo = False
        self.sysqb_socket = None
        self.mesa_id = "MIA-01"  # ID de la mesa por omisión
        self.conectado = False
        self.despliega_mensaje = False
        self.create_widgets()
        self.supervisa_conexion()
        self.sorteo.inicia_bascula()
        self.root.option_add('*TCombobox*Listbox.font', self.mesa_popdown_font)  # Aplica la fuente grande al Combobox de mesa

        ancho = self.root.winfo_screenwidth()
        alto = self.root.winfo_screenheight()
        if self.portal.es_pi == False: 
            self.root.attributes("-fullscreen", False)  # Pantalla completa solo en Raspberry Pi
           
        else:
            #self.root.attributes("-fullscreen", True)  # Pantalla completa solo en Raspberry Pi
            self.root.geometry(f"{ancho}x{alto}+0+0")  # Ajusta la ventana al tamaño de la pantalla
    
    def create_widgets(self):

        # Contenedor principal main_frame: Cuadro 1 y Cuadro 2
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        #######################################################################
        #
        #   Cuadro 1 (sorteo_frame): tipo de sorteo, mul, cajas de sorteo OK/NG y comunicación
        #
        # #####################################################################
        sorteo_frame = tk.Frame(main_frame, relief=tk.GROOVE, borderwidth=2)
        sorteo_frame.pack_propagate(True)  # No ajustar al contenido
        sorteo_frame.pack(side=tk.LEFT,  anchor='n', pady=(20, 20), padx=(5,5))
        
        #
        # tipo_conteo_row: Conteo por IR o Conteo por Peso (Checkbuttons)
        #
        self.tipo_conteo_ir = tk.BooleanVar(value=False)
        self.tipo_conteo_peso = tk.BooleanVar(value=False)
        tipo_conteo_row = tk.Frame(sorteo_frame, relief=tk.GROOVE, borderwidth=2)
        tipo_conteo_row.pack(side=tk.TOP, pady=(20,0), anchor="center")
        tk.Checkbutton(tipo_conteo_row, text="BARRERA", variable=self.tipo_conteo_ir, onvalue=True, offvalue=False, font=("Arial", 18)).pack(side=tk.LEFT, padx=(10,60))
        tk.Checkbutton(tipo_conteo_row, text="PESO", variable=self.tipo_conteo_peso, onvalue=True, offvalue=False, font=("Arial", 18)).pack(side=tk.LEFT, padx=(60,10))

        #
        # multiplicador_frame: Checkboxes X1, X10 y X100
        #
        multiplicador_frame = tk.Frame(sorteo_frame)
        multiplicador_frame.pack(padx=(60, 60), pady=(20, 5), anchor="center")
        self.multiplicador_var = tk.IntVar(value=1)

        radio_x1 = tk.Radiobutton(multiplicador_frame, text="x1", variable=self.multiplicador_var, value=1, font=("Arial", 16))
        radio_x10 = tk.Radiobutton(multiplicador_frame, text="x10", variable=self.multiplicador_var, value=10, font=("Arial", 16))
        radio_x100 = tk.Radiobutton(multiplicador_frame, text="x100", variable=self.multiplicador_var, value=100, font=("Arial", 16))

        radio_x1.pack(side=tk.LEFT, padx=10)
        radio_x10.pack(side=tk.LEFT, padx=10)
        radio_x100.pack(side=tk.LEFT, padx=10)

        # Actualiza la variable multiplicador_valor al cambiar el valor del "radiobutton"
        self.multiplicador_valor = self.multiplicador_var.get()
        def actualiza_multiplicador(*args):
            self.multiplicador_valor = self.multiplicador_var.get()
        self.multiplicador_var.trace_add("write", lambda *args: actualiza_multiplicador())

        # Función de respuesta (callback) para el tacto de las cajitas de sorteo
        def make_incrementa_callback(idx):
            return lambda event: self.sorteo.incrementa_contador(idx,0)
        
        #
        # pza_ok_container: Etiqueta, cajita y contador para "Piezas OK"
        #
        pza_ok_container = tk.Frame(sorteo_frame)
        pza_ok_container.pack(padx=(10,10), pady=(15,5),anchor="center")
        self.pza_ok_label = tk.Label(pza_ok_container, text="OK", font=("Arial", 18))
        self.pza_ok_label.pack(side=tk.LEFT, padx=0)
        self.pza_ok_entry = tk.Entry(pza_ok_container, font=("Arial", 30), width=5)
        self.pza_ok_entry.pack(side=tk.LEFT, padx=(0,2))
        self.pza_ok_entry.config(bg="white", fg="#1CA301")
        self.pza_ok_entry.bind("<Key>", lambda e: "break")  # Bloquea teclado
        ok_btn = tk.Canvas(pza_ok_container, width=36, height=36, bg=sorteo_frame.cget("bg"), highlightthickness=0, cursor="hand2")
        ok_btn.pack(side=tk.LEFT, padx=1)
        rect_ok_1 = ok_btn.create_rectangle(0, 0, 36, 36, fill="#7CBB00", outline="")
        rect_ok_2 = ok_btn.create_rectangle(4, 4, 32, 32, fill="white", outline="")
        ok_btn.bind("<Button-1>", make_incrementa_callback(0))
        
        # Crea el efecto "Hover" para la cajita de "Piezas OK"
        def on_ok_hover(event):
            ok_btn.itemconfig(rect_ok_2, fill="#A6E22E")  # Verde más claro al pasar el ratón
        def on_ok_leave(event): 
            ok_btn.itemconfig(rect_ok_2, fill="white")  # Color original al salir
        ok_btn.bind("<Enter>", on_ok_hover)
        ok_btn.bind("<Leave>", on_ok_leave)

        #
        # pza_ng_container_mix: Etiqueta, cajita y contador para "Piezas NG-MIX"
        #
        #pza_ng_container_mix = tk.Frame(sorteo_frame)
        #pza_ng_container_mix.pack(padx=(50,50), pady=(10, 20), anchor="center")
        self.pza_ng_label_mix = tk.Label(pza_ok_container, text="NG", font=("Arial", 18))
        self.pza_ng_label_mix.pack(side=tk.LEFT, padx=(30,0))
        self.pza_ng_entry_mix = tk.Entry(pza_ok_container, font=("Arial", 30), width=5)
        self.pza_ng_entry_mix.pack(side=tk.LEFT, padx=(1,1))
        self.pza_ng_entry_mix.config(bg="white", fg="#FA0505")
        self.pza_ng_entry_mix.bind("<Key>", lambda e: "break")  # Bloquea teclado
        ngmix_btn = tk.Canvas(pza_ok_container, width=36, height=36, bg=sorteo_frame.cget("bg"), highlightthickness=0, cursor="hand2")
        ngmix_btn.pack(side=tk.LEFT, padx=1)
        ngmix_btn.create_rectangle(0, 0, 36, 36, fill="#FA0505", outline="")
        rect_ngmix = ngmix_btn.create_rectangle(4, 4, 32, 32, fill="white", outline="")
        ngmix_btn.bind("<Button-1>", make_incrementa_callback(1))
        
        # Crea el efecto "Hover" para la cajita de "Piezas NG-MIX"
        def on_ngmix_hover(event):
            ngmix_btn.itemconfig(rect_ngmix, fill="#FA8585")  # Rojo más claro al pasar el mouse
        def on_ngmix_leave(event): 
            ngmix_btn.itemconfig(rect_ngmix, fill="white")  # Color original al salir
        ngmix_btn.bind("<Enter>", on_ngmix_hover)
        ngmix_btn.bind("<Leave>", on_ngmix_leave)

        #
        # pieza_container: PIEZA No.
        #
        pieza_container = tk.Frame(sorteo_frame)
        pieza_container.pack(pady=(25,25), padx=(10,10), fill=tk.X)
        self.pieza_label = tk.Label(pieza_container, text="PIEZA No.", font=("Arial", 16))
        self.pieza_label.pack(side=tk.LEFT, padx=(1,1))
        self.pieza_entry = tk.Entry(pieza_container, font=("Arial", 80), width=6)
        self.pieza_entry.pack(side=tk.LEFT, padx=2)
        self.pieza_entry.bind("<Key>", lambda e: "break")  # Bloquea teclado
        self.pieza_entry.config(state="normal") 
        self.pieza_entry.insert(0, f"{self.sorteo.pieza_numero:>6}")
        self.pieza_entry.config(state="disabled", disabledforeground="#0241EC")  # Deshabilita el Entry para evitar el cursor

        # Separadores horizontales tipo GROOVE 
        separador1 = tk.Frame(sorteo_frame, height=1, bd=1, relief=tk.GROOVE, bg="gray")
        separador1.pack(fill=tk.X, padx=(5,5), pady=(5, 2))
        separador2 = tk.Frame(sorteo_frame, height=1, bd=1, relief=tk.GROOVE, bg="gray")
        separador2.pack(fill=tk.X, padx=(10,10), pady=(0, 7))

        #
        # signal_row: Contenedor para señal de conexión y URL (en una sola línea)
        #
        signal_row = tk.Frame(sorteo_frame)
        signal_row.pack(side=tk.TOP, anchor=tk.NW, padx=5, pady=(30, 10))

        tk.Label(signal_row, text="Conexión", font=("Arial", 12)).pack(side=tk.LEFT, padx=(0, 5))
        self.signal_canvas = tk.Canvas(signal_row, width=20, height=20, bg=sorteo_frame.cget("bg"), highlightthickness=0)
        self.signal_canvas.pack(side=tk.LEFT, padx=(0, 10))
        self.signal_circle = self.signal_canvas.create_oval(2, 2, 18, 18, fill="gray", outline="")
        self.signal_circle = self.signal_canvas.create_oval(4, 4, 16, 16, fill="gray", outline="")

        self.url_label = tk.Label(signal_row, text="URL:", font=("DejaVu Sans Mono", 14))
        self.url_label.pack(side=tk.LEFT, padx=(0, 5))
        self.url_menu = ttk.Combobox(signal_row, textvariable=self.url_var, font=("Arial", 16), width=9, state="readonly")
        self.url_menu['values'] = ["LOCAL", "SIMULA", "QB"]
        self.url_menu.current(0)
        self.url_menu.pack(side=tk.LEFT)

        #
        # conecta_button_row: Contenedor para los botones Desconecta, Mesa y Conecta 
        #
        conecta_button_row = tk.Frame(sorteo_frame)
        conecta_button_row.pack(fill=tk.X, pady=(10, 20), anchor="center")
        conecta_button_row.columnconfigure(0, weight=1)
        conecta_button_row.columnconfigure(1, weight=1)
        conecta_button_row.columnconfigure(2, weight=1)

        # Botón DESCONECTA
        style = ttk.Style()
        style.configure("Red.TButton", foreground="gray", font=("DejaVu Sans Mono", 12))
        self.disconnect_button = tk.Button(conecta_button_row, text="DESC", command=self.desconecta_sysqb, relief=tk.RAISED,
            bd=4,
            height=1,
            width=6,
            font=("Arial", 12),
            bg="#e0e0e0",
            fg="black",
            activebackground="#cccccc",
            activeforeground="black")
        self.disconnect_button.grid(row=0, column=0, padx=(20,10), sticky="nsew")
        #
        # mesa_container: Contenedor para el Combobox de mesa
        #
        mesa_container = tk.Frame(conecta_button_row)
        mesa_container.grid(row=0, column=1, padx=(10,10), sticky="nsew")
        
        self.mesa_label = tk.Label(mesa_container, text="MIA", font=("Arial", 18, "bold"))
        self.mesa_label.pack(side=tk.LEFT, padx=5)
        self.mesa_var = tk.StringVar(value="1")
        
        # Fuente grande para el popdow (listado)
        self.mesa_popdown_font = tkfont.Font(family="Arial", size=32)
        def _ajusta_popdown_mesa():
            try:
                # Obtiene la ventana de popdown de este combobox
                popdown = self.mesa_menu.tk.call("ttk::combobox::PopdownWindow", str(self.mesa_menu))
                lb_path = popdown + ".f.l"   # Ruta del listbox interno
                # Aplicar fuente grande a los elementos del dropdown
                self.mesa_menu.tk.call(lb_path, "configure", "-font", self.mesa_popdown_font)
                # Limita filas visibles 
                filas_visibles = min(6, len(self.mesa_menu['values']))
                try:
                    self.mesa_menu.configure(height=filas_visibles)
                except tk.TclError:
                    pass
                "Reposiciona el popdown después de que se haya  mapeado"
                self.root.after(0, lambda: _reposiciona_popdown_mesa(popdown, lb_path))
            except tk.TclError:
                pass  # Si no se puede obtener el popdown, no hacer nada
        
        # Remueve la selección activa y el enfoque al cambiar el valor del Combobox
        def limpia_enfoque_combobox(event):
            self.root.after(100, lambda: event.widget.selection_clear())
            self.root.after(150, lambda: self.root.focus_force())

        def _reposiciona_popdown_mesa(popdown, lb_path):
        # Mide pantalla y coloca el popdown arriba si no cabe abajo.
            try:
                # Asegura tamaños actualizados
                self.root.update_idletasks()

                # Coordenadas del widget y medidas de pantalla
                x = self.mesa_menu.winfo_rootx()
                y = self.mesa_menu.winfo_rooty()
                h_widget = self.mesa_menu.winfo_height()
                screen_h = self.root.winfo_screenheight()

                # Altura estimada del popdown según filas y métrica de fuente
                try:
                    filas = int(self.mesa_menu.cget("height"))
                except Exception:
                    filas = 6
                line_h = self.mesa_popdown_font.metrics("linespace")
                # Un poco de margen/padding adicional
                est_pop_h = int(filas * line_h + 16)

                # ¿Cabe abajo?
                y_abajo = y + h_widget
                y_arriba = y - est_pop_h

                # Si no cabe abajo, y sí cabe arriba, súbelo
                if y_abajo + est_pop_h > screen_h and y_arriba >= 0:
                    # Solo ajustamos posición Y. Conservamos X y ancho actuales.
                    # Obtenemos geometría actual para preservar ancho
                    pdw = self.root.nametowidget(popdown)
                    # fuerza layout
                    pdw.update_idletasks()
                    # Solo seteamos +x+y (sin WxH) para no distorsionar tamaño
                    self.root.tk.call("wm", "geometry", popdown, f"+{x}+{y_arriba}")
                else:
                    # Dejarlo abajo (asegura posición estándar)
                    self.root.tk.call("wm", "geometry", popdown, f"+{x}+{y_abajo}")
            except Exception:
                pass

        self.mesa_menu = ttk.Combobox(
            mesa_container, textvariable=self.mesa_var, font=("Arial", 24), width=3, height=20, state="readonly",
            postcommand=_ajusta_popdown_mesa, justify="center")
        self.mesa_menu['values'] = [str(i) for i in range(1, 17)]
        self.mesa_menu.current(0)
        self.mesa_menu.pack(side=tk.LEFT, padx=5)
        self.mesa_menu.bind("<<ComboboxSelected>>", limpia_enfoque_combobox)

        # Botón CONECTA
        style.configure("Green.TButton", foreground="#1094F9", font=("DejaVu Sans Mono", 12))
        self.connect_button = tk.Button(conecta_button_row, text="CONEC", command=self.conecta_sysqb, relief=tk.RAISED,
            bd=4,
            height=1,
            width=6,
            font=("Arial", 12),
            bg="#e0e0e0",
            fg="black",
            activebackground="#cccccc",
            activeforeground="black")
        self.connect_button.grid(row=0, column=2, padx=(10,20), sticky="nsew")

        #self.titulo_label = tk.Label(sorteo_frame, text="Wong Instruments  /  MIA-Portal   Ver 5.6", font=("Arial", 12))
        #self.titulo_label.pack(side=tk.LEFT, padx=0, pady=(10,0), anchor="center")
        #######################################################################
        #
        #   Cuadro 2 (bascula_frame):  Despliegue de báscula: calibración y tiempo real de peso
        #
        #######################################################################
        bascula_frame = tk.Frame(main_frame, relief=tk.GROOVE, borderwidth=2)
        bascula_frame.pack(side=tk.RIGHT,  expand=False, pady=(20, 20), padx=(5, 15))

        #
        # Sub-frame calibra_container: 
        #
        #self.calibra_container = tk.Frame(bascula_frame, relief=tk.GROOVE, borderwidth=2)
        self.calibra_container = tk.Frame(bascula_frame)
        self.calibra_container.pack(padx=(10,10), pady=(2,2), fill=tk.X)
        # Título centrado para el frame de báscula
        tk.Label(self.calibra_container, text="CALIBRA PESO/PIEZA (BÁSCULA OK)", font=("Arial", 14)).pack(pady=(5,10), anchor="center")

        # Renglón de Tolerancia
        tolerancia_row = tk.Frame(self.calibra_container)
        tolerancia_row.pack(side=tk.TOP, anchor="center", pady=(10,15))
        self.peso_promedio_label = tk.Label(tolerancia_row, text="Peso Prom", font=("Arial", 14))
        self.peso_promedio_label.pack(side=tk.LEFT, padx=5)
        self.peso_promedio_entry = tk.Entry(tolerancia_row, font=("Arial", 14), width=5)
        self.peso_promedio_entry.pack(side=tk.LEFT, padx=0)
        #
        self.tolerancia_label = tk.Label(tolerancia_row, text="+/- (%)", font=("Arial", 14))
        self.tolerancia_label.pack(side=tk.LEFT, padx=(15,0))
        self.tolerancia_var = tk.StringVar(value="20")  # Valor por omisión 15%
        self.tolerancia_menu = ttk.Combobox(tolerancia_row, textvariable=self.tolerancia_var, 
            font=("Arial", 16), width=4, state="readonly", justify="center")
        self.tolerancia_menu['values'] = ["5", "10", "15", "20", "30", "50"]
        self.tolerancia_menu.current(3)  # Selecciona el valor por omisión (10%)
        self.tolerancia_menu.pack(side=tk.LEFT, padx=0)
        self.tolerancia_menu.bind("<<ComboboxSelected>>", limpia_enfoque_combobox)

        # Renglón para los tres Entry y sus etiquetas
        peso_row = tk.Frame(self.calibra_container)
        peso_row.pack(side=tk.TOP, anchor="center", pady=10)

        self.peso_labels = []
        self.peso_entries = []

        for i in range(1, 4):  # Itera para M1, M2, M3
            label = tk.Label(peso_row, text=f"M{i}", font=("Arial", 14))
            label.pack(side=tk.LEFT, padx=0)
            self.peso_labels.append(label)

            entry = tk.Entry(peso_row, font=("Arial", 14), width=5)
            entry.pack(side=tk.LEFT, padx=(0,10))
            self.peso_entries.append(entry)

        # Renglón para el botón de toma de muestras secuenciales
        self.muestra_actual = 0  # Índice de la muestra actual (0 para M1, 1 para M2, etc.)
        self.boton_toma_muestra = tk.Button(
            self.calibra_container,
            text=f"MUESTRA {self.muestra_actual + 1}",
            font=("Arial", 16),
            command=self.toma_muestra_secuencial
        )
        self.boton_toma_muestra.pack(side=tk.TOP, pady=(10,20))

        # Peso 1
        # peso_1_row = tk.Frame(self.calibra_container)
        # peso_1_row.pack(side=tk.TOP,  anchor="center", pady=4)
        # self.peso_1_label = tk.Label(peso_1_row, text="M1", font=("Arial", 14))
        # self.peso_1_label.pack(side=tk.LEFT, padx=5)
        # self.peso_1_entry = tk.Entry(peso_1_row, font=("Arial", 14), width=5)
        # self.peso_1_entry.pack(side=tk.LEFT, padx=5)
        # self.peso_1_btn = tk.Button(peso_1_row, text="Registra", font=("Arial", 16), command=self.lee_peso_1)
        # self.peso_1_btn.pack(side=tk.LEFT, padx=5)

        # Peso 2
        # peso_2_row = tk.Frame(self.calibra_container)
        # peso_2_row.pack(side=tk.TOP, anchor="center", pady=4)
        # self.peso_2_label = tk.Label(peso_2_row, text="M2", font=("Arial", 14))
        # self.peso_2_label.pack(side=tk.LEFT, padx=5)
        # self.peso_2_entry = tk.Entry(peso_2_row, font=("Arial", 14), width=5)
        # self.peso_2_entry.pack(side=tk.LEFT, padx=5)
        # self.peso_2_btn = tk.Button(peso_2_row, text="Registra", font=("Arial", 16), command=self.lee_peso_2)
        # self.peso_2_btn.pack(side=tk.LEFT, padx=5)

        # Peso 3
        # peso_3_row = tk.Frame(self.calibra_container)
        # peso_3_row.pack(side=tk.TOP, anchor="center", pady=4)
        # self.peso_3_label = tk.Label(peso_3_row, text="M3", font=("Arial", 14))
        # self.peso_3_label.pack(side=tk.LEFT, padx=5)
        # self.peso_3_entry = tk.Entry(peso_3_row, font=("Arial", 14), width=5)
        # self.peso_3_entry.pack(side=tk.LEFT, padx=5)
        # self.peso_3_btn = tk.Button(peso_3_row, text="Registra", font=("Arial", 16), command=self.lee_peso_3)
        # self.peso_3_btn.pack(side=tk.LEFT, padx=5)

        #
        # peso_container: Calibración de báscula y lecturas en vivo
        #
        self.peso_container = tk.Frame(bascula_frame)
        self.peso_container.pack(padx=(20,20), pady=(5,0), fill=tk.X)
        
        # Separadores horizontales tipo GROOVE antes del peso_container
        separador1 = tk.Frame(self.peso_container, height=1, bd=1, relief=tk.GROOVE, bg="gray")
        separador1.pack(fill=tk.X, padx=(5,5), pady=(5, 2))
        separador2 = tk.Frame(self.peso_container, height=1, bd=1, relief=tk.GROOVE, bg="gray")
        separador2.pack(fill=tk.X, padx=(10,10), pady=(0, 5))

        self.titulo_peso = tk.Label(self.peso_container, text="DETECCIÓN DE PIEZAS/PESO (gms)", font=("Arial", 14))
        self.titulo_peso.pack(pady=(5,10), anchor="center")
        #
        # lectura_peso_container: (OK) Lectura anterior, actual y pieza registrada
        #
        self.lectura_peso_container = tk.Frame(self.peso_container, relief=tk.GROOVE, borderwidth=2)
        self.lectura_peso_container.pack(padx=(10,10), pady=(10,10), fill=tk.X)
        #
        # peso_row: Peso último y actual 
        #
        peso_row = tk.Frame(self.lectura_peso_container)
        peso_row.pack(side=tk.TOP, anchor="w", fill=tk.X, pady=(5,0))
        self.peso_ultimo_label = tk.Label(peso_row, text="Anterior:", font=("Arial", 14))
        self.peso_ultimo_label.pack(side=tk.LEFT, padx=5)
        self.peso_ultimo_entry = tk.Entry(peso_row, font=("Arial", 14), width=6)
        self.peso_ultimo_entry.pack(side=tk.LEFT, padx=2)
        self.peso_ultimo_entry.bind("<Key>", lambda e: "break")  # Bloquea teclado
        self.peso_actual_label = tk.Label(peso_row, text="Actual:", font=("Arial", 14))
        self.peso_actual_label.pack(side=tk.LEFT, padx=(20,0))
        self.peso_actual_entry = tk.Entry(peso_row, font=("Arial", 14), width=6)
        self.peso_actual_entry.pack(side=tk.LEFT, padx=2)
        self.peso_actual_entry.bind("<Key>", lambda e: "break")  # Bloquea teclado
       
        pieza_final_container = tk.Frame(self.lectura_peso_container)
        pieza_final_container.pack(pady=(5, 5), fill=tk.X, anchor='n')
        self.pieza_final_label = tk.Label(pieza_final_container, text="PZAS OK", font=("Arial", 20))
        self.pieza_final_label.pack(side=tk.LEFT, padx=(10,0))
        self.pieza_final_label.config( fg="#1CA301")
        self.pieza_final_peso_entry = tk.Entry(pieza_final_container, font=("Arial", 24), width=6)
        self.pieza_final_peso_entry.pack(side=tk.LEFT, padx=5)
        self.pieza_final_peso_entry.config(bg="white", fg="#1CA301")
        self.pieza_final_peso_entry.bind("<Key>", lambda e: "break")  # Bloquea teclado
       

        #
        # lectura_peso_ng_container: (NG) Lectura anterior, actual y pieza registrada
        #
        self.lectura_peso_ng_container = tk.Frame(self.peso_container, relief=tk.GROOVE, borderwidth=2)
        self.lectura_peso_ng_container.pack(padx=(10,10), pady=(10,10), fill=tk.X)
        #
        # peso_row: Peso último y actual 
        #
        peso_ng_row = tk.Frame(self.lectura_peso_ng_container)
        peso_ng_row.pack(side=tk.TOP, anchor="w", fill=tk.X, pady=(5,0))
        self.peso_ultimo_ng_label = tk.Label(peso_ng_row, text="Anterior:", font=("Arial", 14))
        self.peso_ultimo_ng_label.pack(side=tk.LEFT, padx=5)
        self.peso_ultimo_ng_entry = tk.Entry(peso_ng_row, font=("Arial", 14), width=6)
        self.peso_ultimo_ng_entry.pack(side=tk.LEFT, padx=2)
        self.peso_ultimo_ng_entry.bind("<Key>", lambda e: "break")  # Bloquea teclado
        self.peso_actual_ng_label = tk.Label(peso_ng_row, text="Actual:", font=("Arial", 14))
        self.peso_actual_ng_label.pack(side=tk.LEFT, padx=(20,0))
        self.peso_actual_ng_entry = tk.Entry(peso_ng_row, font=("Arial", 14), width=6)
        self.peso_actual_ng_entry.pack(side=tk.LEFT, padx=2)
        self.peso_actual_ng_entry.bind("<Key>", lambda e: "break")  # Bloquea teclado
       
        pieza_final_ng_container = tk.Frame(self.lectura_peso_ng_container)
        pieza_final_ng_container.pack(pady=(5, 5), fill=tk.X, anchor='n')
        self.pieza_final_ng_label = tk.Label(pieza_final_ng_container, text="PZAS NG", font=("Arial", 20))
        self.pieza_final_ng_label.pack(side=tk.LEFT, padx=(10,0))
        self.pieza_final_ng_label.config( fg="#FA0505")
        self.pieza_final_peso_ng_entry = tk.Entry(pieza_final_ng_container, font=("Arial", 24), width=6)
        self.pieza_final_peso_ng_entry.pack(side=tk.LEFT, padx=5)
        self.pieza_final_peso_ng_entry.config( fg="#FA0505")
        self.pieza_final_peso_ng_entry.bind("<Key>", lambda e: "break")  # Bloquea teclado
       

        # Carga y redimensiona la imagen del botón de apagado
        boton_encendido_path = os.path.join(self.base_dir, "boton_encendido_negro.png")
        boton_encendido_img = Image.open(boton_encendido_path).resize((32, 32))  # Ajusta el tamaño según sea necesario
        # Invierte los colores de la imagen
        #boton_encendido_img = ImageOps.invert(boton_encendido_img.convert("RGB"))
        self.boton_encendido = ImageTk.PhotoImage(boton_encendido_img)

        # Función para apagar la Raspberry Pi
        def apagar_raspberry():
            if self.portal.es_pi == True:
                if self.root.attributes("-fullscreen") == False:    # Regresa a moso Pantalla Completa
                    self.root.attributes("-fullscreen", True)
                    return
                respuesta = messagebox.askyesno("Confirmación", "¿Estás seguro de que deseas apagar la Raspberry Pi?")
                if respuesta:  # Si el usuario confirma
                    os.system("sudo shutdown now")
            else:
                self.root.destroy()  # Cierra la ventana principal

        # Botón de apagado
        boton_apagado = tk.Button(
            self.root,
            image=self.boton_encendido,
            command=apagar_raspberry,
            relief=tk.FLAT,
            bg="white",
            activebackground="white",
            borderwidth=0,
            cursor="hand2"
        )
        boton_apagado.place(x=10, y=10)  # Posiciona el botón en la esquina superior izquierda
    
    # Tarea periódica para supervisar el estado de la conexión
    def supervisa_conexion(self):
        
        if not self.conectado or not self.wifi_activo():
            self.alerta_desconexión()
            self.despliega_mensaje = True
        else:
            self.signal_canvas.itemconfig(self.signal_circle, fill="yellow")
            if self.despliega_mensaje:
                self.despliega_mensaje_rx("Conexión establecida con el servidor SysQB.\n")
                self.despliega_mensaje = False
        self.root.after(1000, self.supervisa_conexion)

    def alerta_desconexión(self):
        # Puedes mostrar un mensaje en la GUI, cambiar colores, etc.
        self.signal_canvas.itemconfig(self.signal_circle, fill="red")
        if (self.conectado):
            self.despliega_mensaje_rx("Wi-Fi desconectado!!")
        else:
            self.despliega_mensaje_rx("Websocket desconectado!!")

    def wifi_activo(self):
        # Busca interfaces típicas de Wi-Fi en Linux, Mac y Windows
        wifi_keywords = ["wlan", "wifi", "wl", "en0", "en1"]
        for iface, addrs in psutil.net_if_addrs().items():
            if any(keyword in iface.lower() for keyword in wifi_keywords):
                stats = psutil.net_if_stats().get(iface)
                if stats and stats.isup:
                    return True
        return False

    # Actualiza la cajita de PIEZA No. y la cajita de sorteo accionada
    def actualiza_cajitas(self, pieza_numero, idx):
        entrys = [
            self.pza_ok_entry,
            # self.pza_ng_entry,
            # self.pza_ng_entry_2,
            # self.pza_ng_entry_3,
            # self.pza_ng_entry_4,
            # self.pza_ng_entry_5,
            self.pza_ng_entry_mix
        ]
        self.pieza_entry.config(state="normal")  # Habilita temporalmente
        self.pieza_entry.delete(0, tk.END)
        self.pieza_entry.insert(0, f"{pieza_numero:>6}")
        self.pieza_entry.config(state="disabled")  # deshabilita temporalmente
        entrys[idx].delete(0, 'end')
        entrys[idx].insert(0, f"{self.sorteo.contadores_cajitas[idx]:>5}")

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
        #self.text_area_tx.insert("1.0", mensaje + "\n", "margin")
        pass

    def despliega_mensaje_rx(self, mensaje):
        #self.text_area_rx.insert("1.0", mensaje + "\n", "margin")
        pass

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

    def despliega_titulo_peso(self):
        self.titulo_peso.config(text="DETECCIÓN DE PIEZAS/PESO (gms)", fg="Black")

    def despliega_bascula_apagada(self, despliega):
        if self.tipo_conteo_ir.get():
            return
        if despliega:
            self.titulo_peso.config(text="!!! BÁSCULA  APAGADA ...", fg="#FF0000")
        else:
            self.titulo_peso.config(text=" ", fg="Black")
       
    def limpia_cajitas(self):  
        entrys = [
            self.pza_ok_entry,
            # self.pza_ng_entry,
            # self.pza_ng_entry_2,
            # self.pza_ng_entry_3,
            # self.pza_ng_entry_4,
            # self.pza_ng_entry_5,
            self.pza_ng_entry_mix
        ]
        self.pieza_entry.config(state="normal")  # Habilita temporalmente
        self.pieza_entry.delete(0, tk.END)
        self.pieza_entry.insert(0, f"{self.sorteo.pieza_numero:>6}")
        self.pieza_entry.config(state="disabled")  # deshabilita temporalmente
        for idx in range(len(entrys)):
            entrys[idx].delete(0, 'end')
            entrys[idx].insert(0, f"{self.sorteo.contadores_cajitas[idx]:>5}")
         
    def lee_mesa(self):
        try:
            return int(self.mesa_var.get())  # Convierte a entero y elimina espacios en blanco
        except ValueError:
            return 1  # Valor predeterminado si no es un número válido

    def lee_url(self):
        try:
            return self.url_var.get()  
        except ValueError:
            return "ws://192.168.100.25:3000/cable"  # Valor predeterminado si no es un número válido
    
    # def connect_websocket(self):
    #     self.websocket_mia.connect()
    #     # Cambia el color del círculo a amarillo (encendido)
    #     self.signal_canvas.itemconfig(self.signal_circle, fill="#F9F110")
    
    def conecta_sysqb(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self._conecta_sysqb_async())
       
    async def _conecta_sysqb_async(self):
        self.mesa_id = "MIA-" + str(self.lee_mesa()).zfill(2)  # Formato "MIA-01"
        socket = await self.websocket_mia.conecta_async(self.mesa_id)
        if (socket):    
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
        await self.websocket_mia.desconecta_async()
        
        # Cambia el color del círculo a gris (apagado)
        self.signal_canvas.itemconfig(self.signal_circle, fill="gray")

    def lee_peso_1(self):
        #valor = self.sorteo.lee_bascula()
        valor =  self.sorteo.peso_bascula
        self.peso_1_entry.delete(0, tk.END)
        self.peso_1_entry.insert(0, str(valor))
        self.actualiza_promedio_peso()

    def lee_peso_2(self):
        #valor = self.sorteo.lee_bascula()
        valor = self.sorteo.peso_bascula
        self.peso_2_entry.delete(0, tk.END)
        self.peso_2_entry.insert(0, str(valor))
        self.actualiza_promedio_peso()

    def lee_peso_3(self):
        #valor = self.sorteo.lee_bascula()
        valor =  self.sorteo.peso_bascula
        self.peso_3_entry.delete(0, tk.END)
        self.peso_3_entry.insert(0, str(valor))
        self.actualiza_promedio_peso()

    # Función para tomar muestras secuenciales
    def toma_muestra_secuencial(self):
        try:
            peso = self.sorteo.peso_bascula  # Obtiene el peso de la báscula
            self.peso_entries[self.muestra_actual].delete(0, tk.END)
            self.peso_entries[self.muestra_actual].insert(0, f"{str(peso):>5}")

            # Actualiza el índice de la muestra actual
            self.muestra_actual = (self.muestra_actual + 1) % 3  # Recorre en círculos (0, 1, 2)

            # Actualiza el texto del botón
            self.boton_toma_muestra.config(text=f"MUESTRA {self.muestra_actual + 1}")

            # Actualiza el promedio de peso
            self.actualiza_promedio_peso()
        except ValueError:
            pass

    def actualiza_promedio_peso(self):
        try:
            # Obtiene los valores de los Entry en self.peso_entries
            pesos = [float(entry.get()) for entry in self.peso_entries]
            # Calcula el promedio
            promedio = round(sum(pesos) / len(pesos), 1)
            # Actualiza el Entry del promedio
            self.peso_promedio_entry.delete(0, tk.END)
            self.peso_promedio_entry.insert(0, f"{str(promedio):>5}")
        except ValueError:
            pass  # Ignora errores si algún Entry está vacío o tiene un valor inválido

    def actualiza_pesos(self, anterior, actual, peso_pieza):
        self.peso_ultimo_entry.delete(0, tk.END)
        self.peso_ultimo_entry.insert(0, f"{str(anterior):>8}")
        self.peso_actual_entry.delete(0, tk.END)
        self.peso_actual_entry.insert(0, f"{str(actual):>8}")
        self.pieza_final_peso_entry.delete(0, tk.END)
        self.pieza_final_peso_entry.insert(0, f"{str(peso_pieza):>8}") 

    def despliega_peso_actual(self, peso_actual):
        self.peso_actual_entry.delete(0, tk.END)
        self.peso_actual_entry.insert(0, f"{str(peso_actual):>8}")
    
    def limpia_pesos(self):
        # detener hilo de muestreo
        # self.sorteo.muestreo_activo = False
        # if hasattr(self.sorteo, 'hilo_bascula') and self.sorteo.hilo_bascula.is_alive():
        #     self.sorteo.hilo_bascula.join(timeout=1)

        # limpiar entradas
        for entry in [self.peso_ultimo_entry, self.peso_actual_entry, self.pieza_final_peso_entry]:
            entry.delete(0, tk.END)
            entry.insert(0, str(0).rjust(5))

        # reiniciar hilo de muestreo
        #self.sorteo.inicia_bascula()
    
    def apaga_peso_actual(self):
        self.peso_actual_entry.delete(0, tk.END)
        self.peso_actual_entry.insert(0, " "* 6)  # Espacios en blanco para simular apagado
        
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
