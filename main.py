import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pyautogui
import pyperclip


class BuscadorInventarioPythonApp(ttk.Window):
    def __init__(self):
        super(BuscadorInventarioPythonApp, self).__init__(themename="cosmo")
        self.title("Buscador y Automatizador de Inventario (Python)")
        self.geometry("720x650")
        self.minsize(650, 600)

        self.inventory_map = {}
        self.current_item = None
        self.sequence_list = []
        self.current_step = 0

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=BOTH, expand=True)

        # Título
        title_lbl = ttk.Label(main_frame, text="Automatizador MANSIS - Python", font=("Segoe UI", 16, "bold"))
        title_lbl.pack(anchor="w", pady=(0, 15))

        # Sección 1: Carga de CSV
        file_frame = ttk.Labelframe(main_frame, text=" 1. Archivo CSV ", padding=15)
        file_frame.pack(fill=X, pady=(0, 15))

        btn_cargar = ttk.Button(file_frame, text="Seleccionar Archivo CSV", command=self.cargar_csv,
                                bootstyle="outline-primary")
        btn_cargar.pack(side=LEFT, padx=(0, 10))

        self.lbl_estado = ttk.Label(file_frame, text="Ningún archivo cargado", font=("Segoe UI", 9),
                                    bootstyle="secondary")
        self.lbl_estado.pack(side=LEFT, fill=X, expand=True)

        # Sección 2: Buscador
        search_frame = ttk.Labelframe(main_frame, text=" 2. Búsqueda por Código ", padding=15)
        search_frame.pack(fill=X, pady=(0, 15))

        ttk.Label(search_frame, text="Código del equipo:", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 5))

        box_search = ttk.Frame(search_frame)
        box_search.pack(fill=X)

        self.entry_codigo = ttk.Entry(box_search, font=("Segoe UI", 11), state="disabled")
        self.entry_codigo.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        self.entry_codigo.bind("<Return>", lambda e: self.ejecutar_busqueda())

        self.btn_buscar = ttk.Button(box_search, text="Buscar", command=self.ejecutar_busqueda, state="disabled",
                                     bootstyle="primary")
        self.btn_buscar.pack(side=RIGHT)

        # Sección 3: Ficha de Resultados
        self.result_frame = ttk.Labelframe(main_frame, text=" 3. Datos del Equipo Encontrado ", padding=15)
        self.result_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        fields = [
            ("Nº Serie:", "res_serie"),
            ("Código:", "res_codigo"),
            ("Marca:", "res_marca"),
            ("Modelo:", "res_modelo"),
            ("Área ubicación:", "res_ubicacion"),
            ("Guion Final:", "res_guion")
        ]

        self.result_vars = {}
        for i, (label_text, key) in enumerate(fields):
            lbl_key = ttk.Label(self.result_frame, text=label_text, font=("Segoe UI", 9, "bold"), bootstyle="secondary")
            lbl_key.grid(row=i, column=0, sticky="w", pady=4, padx=(0, 15))

            val_var = tk.StringVar(value="-")
            self.result_vars[key] = val_var
            lbl_val = ttk.Label(self.result_frame, textvariable=val_var, font=("Segoe UI", 10, "bold"))
            lbl_val.grid(row=i, column=1, sticky="w", pady=4)

        # Sección 4: Configuración de Automatización y Envío
        control_frame = ttk.Labelframe(main_frame, text=" 4. Método de Envío y Tecla de Salto ", padding=15)
        control_frame.pack(fill=X, pady=(5, 0))

        options_grid = ttk.Frame(control_frame)
        options_grid.pack(fill=X, pady=(0, 10))

        ttk.Label(options_grid, text="Tecla de salto:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w",
                                                                                           padx=(0, 10))
        self.combo_tecla = ttk.Combobox(options_grid, values=["FLECHA ABAJO", "TAB", "ENTER"], width=15,
                                        state="readonly")
        self.combo_tecla.set("FLECHA ABAJO")
        self.combo_tecla.grid(row=0, column=1, sticky="w", padx=(0, 20))

        # Botones de acción
        btns_action_frame = ttk.Frame(control_frame)
        btns_action_frame.pack(fill=X)

        self.btn_auto = ttk.Button(btns_action_frame, text="Enviar Todo Automático (3s)",
                                   command=self.iniciar_envio_auto, state="disabled", bootstyle="success")
        self.btn_auto.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))

        self.btn_step = ttk.Button(btns_action_frame, text="Modo Paso a Paso (Secuencial)",
                                   command=self.iniciar_envio_paso, state="disabled", bootstyle="info")
        self.btn_step.pack(side=RIGHT, fill=X, expand=True, padx=(5, 0))

        self.lbl_status_envio = ttk.Label(control_frame, text="", font=("Segoe UI", 9, "bold"), bootstyle="warning")
        self.lbl_status_envio.pack(anchor="w", pady=(8, 0))

    def parse_csv_line(self, line, delimiter=','):
        result = []
        current = ''
        in_quotes = False
        i = 0
        while i < len(line):
            char = line[i]
            next_char = line[i + 1] if i + 1 < len(line) else ''
            if char == '"':
                if in_quotes and next_char == '"':
                    current += '"'
                    i += 1
                else:
                    in_quotes = not in_quotes
            elif char == delimiter and not in_quotes:
                result.append(current.strip())
                current = ''
            else:
                current += char
            i += 1
        result.append(current.strip())
        return result

    def cargar_csv(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return

        try:
            text = ""
            for enc in ['utf-8', 'windows-1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        text = f.read()
                    break
                except UnicodeDecodeError:
                    continue

            lines = [l for l in text.splitlines() if l.strip()]
            if len(lines) < 2:
                messagebox.showerror("Error", "El archivo CSV está vacío o no contiene registros válidos.")
                return

            delimiter = ';' if ';' in lines[0] and ',' not in lines[0] else ','
            headers = self.parse_csv_line(lines[0], delimiter)

            idx_codigo = 0
            idx_marca = next((i for i, h in enumerate(headers) if h.lower() == 'marca'), -1)
            idx_modelo = next((i for i, h in enumerate(headers) if h.lower() == 'modelo'), -1)
            idx_serie = next((i for i, h in enumerate(headers) if h.lower() == 'serie'), -1)

            ubicacion_count = 0
            idx_ubicacion = -1
            for i, h in enumerate(headers):
                if h.lower() in ['área ubicación', 'area ubicacion']:
                    ubicacion_count += 1
                    if ubicacion_count == 2:
                        idx_ubicacion = i
                        break

            if idx_marca == -1 or idx_modelo == -1 or idx_serie == -1 or idx_ubicacion == -1:
                messagebox.showerror("Error",
                                     "No se han encontrado todas las columnas requeridas (Marca, Modelo, Serie o 2ª Área ubicación).")
                return

            self.inventory_map.clear()
            for line in lines[1:]:
                cols = self.parse_csv_line(line, delimiter)
                if cols and cols[idx_codigo]:
                    codigo = cols[idx_codigo].strip()
                    self.inventory_map[codigo.upper()] = {
                        'serie': cols[idx_serie] if idx_serie < len(cols) else 'N/D',
                        'codigo': codigo,
                        'marca': cols[idx_marca] if idx_marca < len(cols) else 'N/D',
                        'modelo': cols[idx_modelo] if idx_modelo < len(cols) else 'N/D',
                        'ubicacion': cols[idx_ubicacion] if idx_ubicacion < len(cols) else 'N/D',
                        'guion': '-'
                    }

            self.lbl_estado.config(text=f"Cargado: {len(self.inventory_map)} equipos indexados", bootstyle="success")
            self.entry_codigo.config(state="normal")
            self.btn_buscar.config(state="normal")
            self.entry_codigo.focus()

        except Exception as e:
            messagebox.showerror("Excepción", f"Error al procesar el archivo:\n{str(e)}")

    def ejecutar_busqueda(self):
        query = self.entry_codigo.get().strip().upper()
        if not query:
            messagebox.showwarning("Aviso", "Introduce un código para buscar.")
            return

        item = self.inventory_map.get(query)
        if item:
            self.current_item = item
            self.sequence_list = [
                item['serie'],
                item['codigo'],
                item['marca'],
                item['modelo'],
                item['ubicacion'],
                item['guion']
            ]
            self.current_step = 0

            self.result_vars['res_serie'].set(item['serie'])
            self.result_vars['res_codigo'].set(item['codigo'])
            self.result_vars['res_marca'].set(item['marca'])
            self.result_vars['res_modelo'].set(item['modelo'])
            self.result_vars['res_ubicacion'].set(item['ubicacion'])
            self.result_vars['res_guion'].set(item['guion'])

            self.btn_auto.config(state="normal")
            self.btn_step.config(state="normal", text="Modo Paso a Paso (Paso 1/6)")
            self.lbl_status_envio.config(text="Equipo encontrado. Listo para enviar.", bootstyle="info")
        else:
            self.current_item = None
            for var in self.result_vars.values():
                var.set("-")
            self.btn_auto.config(state="disabled")
            self.btn_step.config(state="disabled")
            messagebox.showinfo("Sin resultados",
                                f"No se encontró ningún equipo con el código '{self.entry_codigo.get().strip()}'.")

    def obtener_tecla_salto(self):
        seleccion = self.combo_tecla.get()
        if seleccion == "FLECHA ABAJO":
            return 'down'
        elif seleccion == "TAB":
            return 'tab'
        else:
            return 'enter'

    def iniciar_envio_auto(self):
        if not self.current_item:
            return
        self.btn_auto.config(state="disabled")
        self.btn_step.config(state="disabled")
        self.entry_codigo.config(state="disabled")
        self.btn_buscar.config(state="disabled")

        threading.Thread(target=self._proceso_auto, daemon=True).start()

    def _proceso_auto(self):
        for i in range(3, 0, -1):
            self.lbl_status_envio.config(text=f"Cámbiate a tu ventana... escribiendo en {i}s", bootstyle="warning")
            time.sleep(1)

        self.lbl_status_envio.config(text="Escribiendo datos...", bootstyle="info")
        tecla = self.obtener_tecla_salto()

        time.sleep(0.4)
        for valor in self.sequence_list:
            pyperclip.copy(str(valor))
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.08)
            pyautogui.press(tecla)
            time.sleep(0.12)

        self.lbl_status_envio.config(text="¡Datos enviados correctamente!", bootstyle="success")
        self.btn_auto.config(state="normal")
        self.btn_step.config(state="normal", text="Modo Paso a Paso (Secuencial)")
        self.entry_codigo.config(state="normal")
        self.btn_buscar.config(state="normal")
        self.entry_codigo.delete(0, tk.END)
        self.entry_codigo.focus()

    def iniciar_envio_paso(self):
        if not self.current_item or self.current_step >= len(self.sequence_list):
            return

        threading.Thread(target=self._proceso_paso, daemon=True).start()

    def _proceso_paso(self):
        valor = self.sequence_list[self.current_step]
        tecla = self.obtener_tecla_salto()

        # Copiar e inyectar el campo actual
        pyperclip.copy(str(valor))
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.08)
        pyautogui.press(tecla)

        self.current_step += 1

        if self.current_step < len(self.sequence_list):
            nombres_pasos = ["Nº Serie", "Código", "Marca", "Modelo", "Área ubicación", "Guion Final"]
            siguiente_nombre = nombres_pasos[self.current_step]
            self.btn_step.config(text=f"Siguiente: {siguiente_nombre} [{self.current_step + 1}/6]")
            self.lbl_status_envio.config(text=f"Copiado '{valor}'. Vuelve a pulsar para el siguiente.",
                                         bootstyle="info")
        else:
            self.btn_step.config(state="disabled", text="¡Secuencia completada!")
            self.lbl_status_envio.config(text="Todos los campos del equipo han sido enviados.", bootstyle="success")
            self.current_step = 0
            self.after(2000, lambda: self.btn_step.config(text="Modo Paso a Paso (Secuencial)"))


if __name__ == "__main__":
    app = BuscadorInventarioPythonApp()
    app.mainloop()