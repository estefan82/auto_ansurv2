import json
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pyautogui
import pyperclip
import sys
from pathlib import Path

BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
CONFIG_FILE = str(BASE_DIR / "config_buscador.json")


class BuscadorInventarioPythonApp(ttk.Window):
    def __init__(self):
        super(BuscadorInventarioPythonApp, self).__init__(themename="darkly")
        self.title("Buscador y Automatizador MANSIS")
        self.geometry("850x700")
        self.minsize(750, 1050)

        self.inventory_map = {}
        self.current_item = None
        self.sequence_list = []
        self.csv_path = ""

        self.create_widgets()
        self.cargar_configuracion_previa()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=BOTH, expand=True)

        # Título
        title_lbl = ttk.Label(main_frame, text="Automatizador de Inventario MANSIS", font=("Segoe UI", 18, "bold"))
        title_lbl.pack(anchor="w", pady=(0, 15))

        # Sección 1: Carga de CSV
        file_frame = ttk.Labelframe(main_frame, text=" 1. Archivo CSV ", padding=15)
        file_frame.pack(fill=X, pady=(0, 15))

        btn_cargar = ttk.Button(file_frame, text="Seleccionar Archivo CSV", command=self.seleccionar_y_guardar_csv,
                                bootstyle="outline-primary")
        btn_cargar.pack(side=LEFT, padx=(0, 15))

        self.lbl_estado = ttk.Label(file_frame, text="Ningún archivo cargado", font=("Segoe UI", 10),
                                    bootstyle="secondary")
        self.lbl_estado.pack(side=LEFT, fill=X, expand=True)

        # Sección 2: Buscador
        search_frame = ttk.Labelframe(main_frame, text=" 2. Búsqueda por Código ", padding=15)
        search_frame.pack(fill=X, pady=(0, 15))

        ttk.Label(search_frame, text="Código del equipo:", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 5))

        box_search = ttk.Frame(search_frame)
        box_search.pack(fill=X)

        self.entry_codigo = ttk.Entry(box_search, font=("Segoe UI", 12), state="disabled")
        self.entry_codigo.pack(side=LEFT, fill=X, expand=True, padx=(0, 15))
        self.entry_codigo.bind("<Return>", lambda e: self.ejecutar_busqueda())

        self.btn_buscar = ttk.Button(box_search, text="Buscar", command=self.ejecutar_busqueda, state="disabled",
                                     bootstyle="primary")
        self.btn_buscar.pack(side=RIGHT)

        # Sección 3: Ficha de Resultados
        self.result_frame = ttk.Labelframe(main_frame, text=" 3. Datos del Equipo Encontrado ", padding=15)
        self.result_frame.pack(fill=BOTH, expand=True, pady=(0, 15))

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
            lbl_key = ttk.Label(self.result_frame, text=label_text, font=("Segoe UI", 10, "bold"),
                                bootstyle="secondary")
            lbl_key.grid(row=i, column=0, sticky="w", pady=6, padx=(0, 20))

            val_var = tk.StringVar(value="-")
            self.result_vars[key] = val_var
            lbl_val = ttk.Label(self.result_frame, textvariable=val_var, font=("Segoe UI", 11, "bold"),
                                bootstyle="info")
            lbl_val.grid(row=i, column=1, sticky="w", pady=6)

        # Sección 4: Configuración de Envío
        control_frame = ttk.Labelframe(main_frame, text=" 4. Método de Envío y Tecla de Salto ", padding=15)
        control_frame.pack(fill=X, pady=(0, 0))

        options_grid = ttk.Frame(control_frame)
        options_grid.pack(fill=X, pady=(0, 12))

        ttk.Label(options_grid, text="Tecla de salto entre campos:", font=("Segoe UI", 10, "bold")).pack(side=LEFT,
                                                                                                         padx=(0, 15))
        self.combo_tecla = ttk.Combobox(options_grid, values=["FLECHA ABAJO", "TAB", "ENTER"], width=18,
                                        state="readonly", font=("Segoe UI", 10))
        self.combo_tecla.set("FLECHA ABAJO")
        self.combo_tecla.pack(side=LEFT)
        self.combo_tecla.bind("<<ComboboxSelected>>", lambda e: self.guardar_preferencia_tecla())

        self.btn_auto = ttk.Button(control_frame, text="Enviar Todo Automático (Espera 3s)",
                                   command=self.iniciar_envio_auto, state="disabled", bootstyle="success")
        self.btn_auto.pack(fill=X, pady=(5, 5), ipady=5)

        self.lbl_status_envio = ttk.Label(control_frame, text="", font=("Segoe UI", 10, "bold"), bootstyle="warning")
        self.lbl_status_envio.pack(anchor="w", pady=(5, 0))

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

    def cargar_csv_desde_ruta(self, file_path):
        if not file_path or not os.path.exists(file_path):
            return False

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
                return False

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
                return False

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

            self.csv_path = file_path
            self.lbl_estado.config(text=f"Cargado: {os.path.basename(file_path)} ({len(self.inventory_map)} equipos)",
                                   bootstyle="success")
            self.entry_codigo.config(state="normal")
            self.btn_buscar.config(state="normal")
            return True
        except Exception:
            return False

    def guardar_configuracion(self, key_to_update, value):
        data = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass

        data[key_to_update] = value
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def seleccionar_y_guardar_csv(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return

        success = self.cargar_csv_desde_ruta(file_path)
        if success:
            self.guardar_configuracion("last_csv_path", file_path)
            self.entry_codigo.focus()
        else:
            messagebox.showerror("Error", "No se pudo procesar el archivo CSV o faltaban columnas requeridas.")

    def guardar_preferencia_tecla(self):
        self.guardar_configuracion("last_key_method", self.combo_tecla.get())

    def cargar_configuracion_previa(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # Cargar ruta del CSV
                    path = data.get("last_csv_path", "")
                    if path and os.path.exists(path):
                        success = self.cargar_csv_desde_ruta(path)
                        if success:
                            self.entry_codigo.focus()

                    # Cargar método de tecla guardado
                    tecla_guardada = data.get("last_key_method", "")
                    if tecla_guardada in ["FLECHA ABAJO", "TAB", "ENTER"]:
                        self.combo_tecla.set(tecla_guardada)
            except Exception:
                pass

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

            self.result_vars['res_serie'].set(item['serie'])
            self.result_vars['res_codigo'].set(item['codigo'])
            self.result_vars['res_marca'].set(item['marca'])
            self.result_vars['res_modelo'].set(item['modelo'])
            self.result_vars['res_ubicacion'].set(item['ubicacion'])
            self.result_vars['res_guion'].set(item['guion'])

            self.btn_auto.config(state="normal")
            self.lbl_status_envio.config(text="Equipo encontrado. Listo para enviar.", bootstyle="info")
        else:
            self.current_item = None
            for var in self.result_vars.values():
                var.set("-")
            self.btn_auto.config(state="disabled")
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
        self.entry_codigo.config(state="disabled")
        self.btn_buscar.config(state="disabled")

        threading.Thread(target=self._proceso_auto, daemon=True).start()

    def _proceso_auto(self):
        for i in range(3, 0, -1):
            self.lbl_status_envio.config(text=f"Cámbiate a tu ventana... escribiendo en {i}s", bootstyle="warning")
            time.sleep(1)

        self.lbl_status_envio.config(text="Escribiendo datos...", bootstyle="info")
        tecla = self.obtener_tecla_salto()

        time.sleep(0.3)
        for valor in self.sequence_list:
            pyperclip.copy(str(valor))
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.08)
            pyautogui.press(tecla)
            time.sleep(0.12)

        self.lbl_status_envio.config(text="¡Datos enviados correctamente!", bootstyle="success")
        self.btn_auto.config(state="normal")
        self.entry_codigo.config(state="normal")
        self.btn_buscar.config(state="normal")
        self.entry_codigo.delete(0, tk.END)
        self.entry_codigo.focus()


if __name__ == "__main__":
    app = BuscadorInventarioPythonApp()
    app.mainloop()