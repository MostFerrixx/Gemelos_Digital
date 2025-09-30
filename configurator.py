# -*- coding: utf-8 -*-
"""
Configurador del Simulador de Almacen - Herramienta Autocontenida
Interfaz grafica independiente para configurar parametros de simulacion.
Version refactorizada sin dependencias de submodulos.
"""

import sys
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


class VentanaConfiguracion:
    """
    Ventana de configuracion completa con todos los widgets y validaciones.
    Implementacion autocontenida sin dependencias externas.
    """

    def __init__(self, parent):
        self.parent = parent
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Variables de configuracion
        self.total_ordenes_var = tk.IntVar(value=300)
        self.pct_pequeno = tk.IntVar(value=60)
        self.pct_mediano = tk.IntVar(value=30)
        self.pct_grande = tk.IntVar(value=10)
        self.vol_pequeno = tk.IntVar(value=5)
        self.vol_mediano = tk.IntVar(value=25)
        self.vol_grande = tk.IntVar(value=80)
        self.capacidad_carro = tk.IntVar(value=150)

        # Recursos
        self.num_operarios_terrestres = tk.IntVar(value=1)
        self.num_montacargas = tk.IntVar(value=1)
        self.capacidad_montacargas = tk.IntVar(value=1000)
        self.tiempo_descarga_por_tarea = tk.IntVar(value=5)

        # Estrategias
        self.dispatch_strategy_var = tk.StringVar(value='Ejecucion de Plan (Filtro por Prioridad)')

        # Layout
        self.layout_path_var = tk.StringVar(value='layouts/WH1.tmx')
        self.sequence_path_var = tk.StringVar(value='layouts/Warehouse_Logic.xlsx')
        self.map_scale_var = tk.DoubleVar(value=1.3)

        # Resolucion
        self.resolution_var = tk.StringVar(value='Pequena (800x800)')

        # Asignacion de recursos
        self.assignment_rules = {
            "GroundOperator": {1: 1},
            "Forklift": {1: 2, 2: 1, 3: 1, 4: 1, 5: 1}
        }
        self.assignment_widgets = {"GroundOperator": [], "Forklift": []}

        # Outbound Staging
        self.outbound_staging_vars = {str(i): tk.IntVar(value=100 if i == 1 else 0) for i in range(1, 8)}

        # Flota de agentes
        self.available_work_areas = []
        self.fleet_groups = []

        # Crear tabs
        self._crear_tab_carga_trabajo()
        self._crear_tab_recursos()
        self._crear_tab_estrategias()
        self._crear_tab_layout()
        self._crear_tab_flota()
        self._crear_tab_outbound_staging()

        # Frame de botones inferior
        self._crear_frame_botones()

    def _crear_tab_carga_trabajo(self):
        """Tab 1: Configuracion de carga de trabajo"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='Carga de Trabajo')

        # Frame principal con scroll
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Total de ordenes
        frame_total = ttk.LabelFrame(scrollable_frame, text="Total de Ordenes", padding=10)
        frame_total.pack(fill='x', padx=10, pady=5)

        ttk.Label(frame_total, text="Total de ordenes:").grid(row=0, column=0, sticky='w', padx=5)
        ttk.Entry(frame_total, textvariable=self.total_ordenes_var, width=10).grid(row=0, column=1, padx=5)

        # Distribucion de tipos
        frame_dist = ttk.LabelFrame(scrollable_frame, text="Distribucion de Tipos de Ordenes", padding=10)
        frame_dist.pack(fill='x', padx=10, pady=5)

        # Pequeno
        ttk.Label(frame_dist, text="Pequeno:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
        ttk.Label(frame_dist, text="Porcentaje (%):").grid(row=1, column=0, sticky='w', padx=20)
        ttk.Entry(frame_dist, textvariable=self.pct_pequeno, width=10).grid(row=1, column=1, padx=5)
        ttk.Label(frame_dist, text="Volumen (unidades):").grid(row=1, column=2, sticky='w', padx=20)
        ttk.Entry(frame_dist, textvariable=self.vol_pequeno, width=10).grid(row=1, column=3, padx=5)

        # Mediano
        ttk.Label(frame_dist, text="Mediano:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky='w', pady=5)
        ttk.Label(frame_dist, text="Porcentaje (%):").grid(row=3, column=0, sticky='w', padx=20)
        ttk.Entry(frame_dist, textvariable=self.pct_mediano, width=10).grid(row=3, column=1, padx=5)
        ttk.Label(frame_dist, text="Volumen (unidades):").grid(row=3, column=2, sticky='w', padx=20)
        ttk.Entry(frame_dist, textvariable=self.vol_mediano, width=10).grid(row=3, column=3, padx=5)

        # Grande
        ttk.Label(frame_dist, text="Grande:", font=('Arial', 10, 'bold')).grid(row=4, column=0, sticky='w', pady=5)
        ttk.Label(frame_dist, text="Porcentaje (%):").grid(row=5, column=0, sticky='w', padx=20)
        ttk.Entry(frame_dist, textvariable=self.pct_grande, width=10).grid(row=5, column=1, padx=5)
        ttk.Label(frame_dist, text="Volumen (unidades):").grid(row=5, column=2, sticky='w', padx=20)
        ttk.Entry(frame_dist, textvariable=self.vol_grande, width=10).grid(row=5, column=3, padx=5)

        # Validacion
        self.label_total_pct = ttk.Label(frame_dist, text="Total: 100%", foreground='green')
        self.label_total_pct.grid(row=6, column=0, columnspan=4, pady=10)

        # Capacidad de carro
        frame_capacidad = ttk.LabelFrame(scrollable_frame, text="Capacidad de Carro", padding=10)
        frame_capacidad.pack(fill='x', padx=10, pady=5)

        ttk.Label(frame_capacidad, text="Capacidad del carro (unidades):").grid(row=0, column=0, sticky='w', padx=5)
        ttk.Entry(frame_capacidad, textvariable=self.capacidad_carro, width=10).grid(row=0, column=1, padx=5)

        # Bind para validacion en tiempo real
        self.pct_pequeno.trace_add('write', lambda *args: self.validar_porcentajes())
        self.pct_mediano.trace_add('write', lambda *args: self.validar_porcentajes())
        self.pct_grande.trace_add('write', lambda *args: self.validar_porcentajes())

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _crear_tab_recursos(self):
        """Tab 2: Configuracion de recursos"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='Recursos')

        frame_recursos = ttk.LabelFrame(tab, text="Configuracion de Recursos", padding=20)
        frame_recursos.pack(fill='both', expand=True, padx=10, pady=10)

        # Operarios terrestres
        ttk.Label(frame_recursos, text="Operarios Terrestres:").grid(row=0, column=0, sticky='w', pady=5, padx=5)
        ttk.Entry(frame_recursos, textvariable=self.num_operarios_terrestres, width=10).grid(row=0, column=1, pady=5, padx=5)

        # Montacargas
        ttk.Label(frame_recursos, text="Montacargas:").grid(row=1, column=0, sticky='w', pady=5, padx=5)
        ttk.Entry(frame_recursos, textvariable=self.num_montacargas, width=10).grid(row=1, column=1, pady=5, padx=5)

        # Capacidad montacargas
        ttk.Label(frame_recursos, text="Capacidad Montacargas (unidades):").grid(row=2, column=0, sticky='w', pady=5, padx=5)
        ttk.Entry(frame_recursos, textvariable=self.capacidad_montacargas, width=10).grid(row=2, column=1, pady=5, padx=5)

        # Tiempo de descarga
        ttk.Label(frame_recursos, text="Tiempo Descarga por Tarea (s):").grid(row=3, column=0, sticky='w', pady=5, padx=5)
        ttk.Entry(frame_recursos, textvariable=self.tiempo_descarga_por_tarea, width=10).grid(row=3, column=1, pady=5, padx=5)

        # Total de operarios
        ttk.Label(frame_recursos, text="Total de Operarios:", font=('Arial', 10, 'bold')).grid(row=4, column=0, sticky='w', pady=10, padx=5)
        self.label_total_operarios = ttk.Label(frame_recursos, text="2", font=('Arial', 10, 'bold'))
        self.label_total_operarios.grid(row=4, column=1, pady=10, padx=5)

        # Bind para actualizar total
        self.num_operarios_terrestres.trace_add('write', lambda *args: self.actualizar_total())
        self.num_montacargas.trace_add('write', lambda *args: self.actualizar_total())

    def _crear_tab_estrategias(self):
        """Tab 3: Estrategias de dispatch"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='Estrategias')

        frame_estrategias = ttk.LabelFrame(tab, text="Estrategia de Dispatch", padding=20)
        frame_estrategias.pack(fill='both', expand=True, padx=10, pady=10)

        ttk.Label(frame_estrategias, text="Selecciona la estrategia de dispatch:").pack(anchor='w', pady=5)

        estrategias = [
            'Ejecucion de Plan (Filtro por Prioridad)',
            'FIFO Simple',
            'Prioridad por Volumen'
        ]

        for estrategia in estrategias:
            ttk.Radiobutton(
                frame_estrategias,
                text=estrategia,
                variable=self.dispatch_strategy_var,
                value=estrategia
            ).pack(anchor='w', pady=2, padx=20)

    def _crear_tab_layout(self):
        """Tab 4: Configuracion de layout y archivos"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='Layout')

        frame_layout = ttk.LabelFrame(tab, text="Archivos de Layout", padding=20)
        frame_layout.pack(fill='both', expand=True, padx=10, pady=10)

        # Layout file
        ttk.Label(frame_layout, text="Archivo de Layout (.tmx):").grid(row=0, column=0, sticky='w', pady=5)
        ttk.Entry(frame_layout, textvariable=self.layout_path_var, width=40).grid(row=0, column=1, pady=5, padx=5)
        ttk.Button(frame_layout, text="Buscar...", command=self._seleccionar_layout).grid(row=0, column=2, pady=5)

        # Sequence file
        ttk.Label(frame_layout, text="Archivo de Secuencia (.xlsx):").grid(row=1, column=0, sticky='w', pady=5)
        ttk.Entry(frame_layout, textvariable=self.sequence_path_var, width=40).grid(row=1, column=1, pady=5, padx=5)
        ttk.Button(frame_layout, text="Buscar...", command=self._seleccionar_secuencia).grid(row=1, column=2, pady=5)

        # Map scale
        ttk.Label(frame_layout, text="Escala del Mapa:").grid(row=2, column=0, sticky='w', pady=5)
        ttk.Entry(frame_layout, textvariable=self.map_scale_var, width=10).grid(row=2, column=1, pady=5, padx=5, sticky='w')

        # Resolucion
        ttk.Label(frame_layout, text="Resolucion de Ventana:").grid(row=3, column=0, sticky='w', pady=5)
        resoluciones = ['Pequena (800x800)', 'Mediana (1024x768)', 'Grande (1280x1024)', 'Extra Grande (1920x1080)']
        ttk.Combobox(frame_layout, textvariable=self.resolution_var, values=resoluciones, width=30, state='readonly').grid(row=3, column=1, pady=5, padx=5, sticky='w')

    def _crear_tab_flota(self):
        """Tab 5: Flota de agentes"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='Flota de Agentes')

        # Canvas con scrollbar
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        self.fleet_frame = ttk.Frame(canvas)

        self.fleet_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.fleet_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Botones de control
        frame_controles = ttk.Frame(tab)
        frame_controles.pack(side='top', fill='x', padx=10, pady=5)

        ttk.Button(frame_controles, text="Generar Flota por Defecto", command=self._generar_flota_defecto_ui).pack(side='left', padx=5)
        ttk.Button(frame_controles, text="Agregar Grupo", command=self._agregar_grupo_manual).pack(side='left', padx=5)
        ttk.Button(frame_controles, text="Limpiar Todo", command=self._limpiar_todos_los_grupos).pack(side='left', padx=5)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mensaje inicial
        ttk.Label(self.fleet_frame, text="No hay grupos de flota configurados.\nUsa 'Generar Flota por Defecto' o 'Agregar Grupo' para comenzar.",
                 justify='center').pack(pady=50)

    def _crear_tab_outbound_staging(self):
        """Tab 6: Distribucion de Outbound Staging"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='Outbound Staging')

        frame_staging = ttk.LabelFrame(tab, text="Distribucion de Staging Areas (%)", padding=20)
        frame_staging.pack(fill='both', expand=True, padx=10, pady=10)

        ttk.Label(frame_staging, text="Configura el porcentaje de ordenes asignadas a cada area de staging:").pack(anchor='w', pady=10)

        for i in range(1, 8):
            frame_row = ttk.Frame(frame_staging)
            frame_row.pack(fill='x', pady=5)

            ttk.Label(frame_row, text=f"Staging Area {i}:", width=20).pack(side='left', padx=5)
            ttk.Entry(frame_row, textvariable=self.outbound_staging_vars[str(i)], width=10).pack(side='left', padx=5)
            ttk.Label(frame_row, text="%").pack(side='left')

            # Bind para validacion
            self.outbound_staging_vars[str(i)].trace_add('write', lambda *args: self._validar_staging_distribution())

        # Label de validacion
        self.label_staging_total = ttk.Label(frame_staging, text="Total: 100%", foreground='green', font=('Arial', 10, 'bold'))
        self.label_staging_total.pack(pady=10)

    def _crear_frame_botones(self):
        """Frame de botones inferior"""
        frame_botones = ttk.Frame(self.parent)
        frame_botones.pack(side='bottom', fill='x', padx=10, pady=10)

        ttk.Button(frame_botones, text="Guardar Configuracion", command=self.guardar_config).pack(side='left', padx=5)
        ttk.Button(frame_botones, text="Cargar Defaults", command=self.valores_por_defecto_new).pack(side='left', padx=5)
        ttk.Button(frame_botones, text="Salir", command=self.parent.quit).pack(side='right', padx=5)

    # ========== METODOS DE VALIDACION ==========

    def validar_porcentajes(self):
        """Valida que los porcentajes sumen 100%"""
        try:
            total = self.pct_pequeno.get() + self.pct_mediano.get() + self.pct_grande.get()

            if total == 100:
                self.label_total_pct.config(text=f"Total: {total}%", foreground='green')
                return True
            else:
                self.label_total_pct.config(text=f"Total: {total}% (debe ser 100%)", foreground='red')
                return False
        except:
            self.label_total_pct.config(text="Total: Error", foreground='red')
            return False

    def actualizar_total(self):
        """Actualiza el total de operarios"""
        try:
            total = self.num_operarios_terrestres.get() + self.num_montacargas.get()
            self.label_total_operarios.config(text=str(total))
        except:
            self.label_total_operarios.config(text="Error")

    def _validar_staging_distribution(self):
        """Valida que la distribucion de staging sume 100%"""
        try:
            total = sum(var.get() for var in self.outbound_staging_vars.values())

            if total == 100:
                self.label_staging_total.config(text=f"Total: {total}%", foreground='green')
                return True
            else:
                self.label_staging_total.config(text=f"Total: {total}% (debe ser 100%)", foreground='red')
                return False
        except:
            self.label_staging_total.config(text="Total: Error", foreground='red')
            return False

    def _validar_configuracion_picking(self, total_ordenes, pct_pequeno, pct_mediano, pct_grande,
                                      vol_pequeno, vol_mediano, vol_grande, capacidad_carro,
                                      op_terrestres, montacargas, total_operarios):
        """Valida la configuracion de picking"""
        # Validar que los porcentajes sumen 100
        if pct_pequeno + pct_mediano + pct_grande != 100:
            messagebox.showerror("Error de Validacion", "Los porcentajes deben sumar exactamente 100%")
            return False

        # Validar valores positivos
        if any(x <= 0 for x in [total_ordenes, vol_pequeno, vol_mediano, vol_grande, capacidad_carro, total_operarios]):
            messagebox.showerror("Error de Validacion", "Todos los valores deben ser mayores que 0")
            return False

        return True

    # ========== METODOS DE UI - LAYOUT ==========

    def _seleccionar_layout(self):
        """Abre dialogo para seleccionar archivo de layout"""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo de layout",
            filetypes=[("TMX files", "*.tmx"), ("All files", "*.*")]
        )
        if filename:
            self.layout_path_var.set(filename)

    def _seleccionar_secuencia(self):
        """Abre dialogo para seleccionar archivo de secuencia"""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo de secuencia",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            self.sequence_path_var.set(filename)

    # ========== METODOS DE FLOTA ==========

    def _cargar_work_areas_automatico(self, sequence_file):
        """Carga WorkAreas automaticamente desde el archivo de secuencia"""
        try:
            import openpyxl

            if not os.path.exists(sequence_file):
                raise FileNotFoundError(f"Archivo no encontrado: {sequence_file}")

            wb = openpyxl.load_workbook(sequence_file, read_only=True, data_only=True)

            # Buscar hoja Warehouse_Logic
            if 'Warehouse_Logic' in wb.sheetnames:
                ws = wb['Warehouse_Logic']

                # Leer WorkAreas desde la columna 'WorkArea' (asumiendo que esta en columna C o similar)
                work_areas = set()
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if row and len(row) > 2:
                        work_area = row[2]  # Columna C (index 2)
                        if work_area:
                            work_areas.add(str(work_area))

                self.available_work_areas = sorted(list(work_areas))
                print(f"[FLOTA] WorkAreas cargadas: {self.available_work_areas}")

            wb.close()

        except ImportError:
            print("[FLOTA] ERROR: openpyxl no esta instalado. No se pueden cargar WorkAreas automaticamente.")
        except Exception as e:
            print(f"[FLOTA] ERROR cargando WorkAreas: {e}")
            raise

    def _generar_flota_defecto_ui(self):
        """Genera flota por defecto con confirmacion de usuario"""
        if not self.available_work_areas:
            # Intentar cargar WorkAreas primero
            sequence_file = self.sequence_path_var.get()
            if sequence_file:
                try:
                    self._cargar_work_areas_automatico(sequence_file)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudieron cargar WorkAreas:\n{e}")
                    return
            else:
                messagebox.showwarning("Advertencia", "Primero debes configurar el archivo de secuencia en la tab 'Layout'")
                return

        if messagebox.askyesno("Confirmar", "Esto generara una flota por defecto y eliminara cualquier configuracion existente. Continuar?"):
            self._limpiar_todos_los_grupos()
            config_defecto = self._generar_config_defecto()
            for group_config in config_defecto:
                self._crear_grupo_desde_config(group_config)
            messagebox.showinfo("Exito", f"Flota por defecto generada con {len(config_defecto)} grupos")

    def _generar_config_defecto(self):
        """Genera configuracion de flota por defecto"""
        if not self.available_work_areas:
            return []

        # Configuracion por defecto: 1 GroundOperator y 5 Forklifts
        config = []

        # 1 GroundOperator con prioridades iguales
        ground_priorities = {wa: 1 for wa in self.available_work_areas}
        config.append({
            'agent_type': 'GroundOperator',
            'cantidad': 1,
            'capacidad': 150,
            'tiempo_descarga': 5,
            'work_area_priorities': ground_priorities
        })

        # 5 Forklifts con diferentes prioridades
        for i in range(5):
            forklift_priorities = {wa: (i % len(self.available_work_areas)) + 1 for wa in self.available_work_areas}
            config.append({
                'agent_type': 'Forklift',
                'cantidad': 1,
                'capacidad': 1000,
                'tiempo_descarga': 5,
                'work_area_priorities': forklift_priorities
            })

        return config

    def _agregar_grupo_manual(self):
        """Agrega un grupo de flota manualmente (simplificado)"""
        if not self.available_work_areas:
            messagebox.showwarning("Advertencia", "Primero debes cargar WorkAreas desde el archivo de secuencia")
            return

        # Crear configuracion basica
        config = {
            'agent_type': 'GroundOperator',
            'cantidad': 1,
            'capacidad': 150,
            'tiempo_descarga': 5,
            'work_area_priorities': {wa: 1 for wa in self.available_work_areas}
        }

        self._crear_grupo_desde_config(config)

    def _crear_grupo_desde_config(self, config):
        """Crea un widget de grupo de flota desde configuracion"""
        frame_grupo = ttk.LabelFrame(self.fleet_frame, text=f"Grupo {len(self.fleet_groups) + 1}", padding=10)
        frame_grupo.pack(fill='x', padx=10, pady=5)

        # Fila 1: Tipo y cantidad
        frame_row1 = ttk.Frame(frame_grupo)
        frame_row1.pack(fill='x', pady=2)

        ttk.Label(frame_row1, text="Tipo:").pack(side='left', padx=5)
        tipo_var = tk.StringVar(value=config['agent_type'])
        ttk.Combobox(frame_row1, textvariable=tipo_var, values=['GroundOperator', 'Forklift'], width=15, state='readonly').pack(side='left', padx=5)

        ttk.Label(frame_row1, text="Cantidad:").pack(side='left', padx=5)
        cantidad_var = tk.IntVar(value=config['cantidad'])
        ttk.Entry(frame_row1, textvariable=cantidad_var, width=5).pack(side='left', padx=5)

        # Fila 2: Capacidad y tiempo
        frame_row2 = ttk.Frame(frame_grupo)
        frame_row2.pack(fill='x', pady=2)

        ttk.Label(frame_row2, text="Capacidad:").pack(side='left', padx=5)
        capacidad_var = tk.IntVar(value=config['capacidad'])
        ttk.Entry(frame_row2, textvariable=capacidad_var, width=8).pack(side='left', padx=5)

        ttk.Label(frame_row2, text="Tiempo Descarga:").pack(side='left', padx=5)
        tiempo_var = tk.IntVar(value=config['tiempo_descarga'])
        ttk.Entry(frame_row2, textvariable=tiempo_var, width=5).pack(side='left', padx=5)

        # Guardar referencias
        grupo_data = {
            'frame': frame_grupo,
            'tipo_var': tipo_var,
            'cantidad_var': cantidad_var,
            'capacidad_var': capacidad_var,
            'tiempo_var': tiempo_var,
            'priorities': config['work_area_priorities']
        }

        self.fleet_groups.append(grupo_data)

        # Boton eliminar
        ttk.Button(frame_grupo, text="Eliminar", command=lambda: self._eliminar_grupo(grupo_data)).pack(side='right', padx=5)

    def _eliminar_grupo(self, grupo_data):
        """Elimina un grupo de flota"""
        grupo_data['frame'].destroy()
        self.fleet_groups.remove(grupo_data)

    def _limpiar_todos_los_grupos(self):
        """Elimina todos los grupos de flota"""
        for grupo in self.fleet_groups[:]:
            grupo['frame'].destroy()
        self.fleet_groups = []

    def _poblar_ui_flota(self, grupos_config):
        """Pobla la UI de flota con grupos desde configuracion"""
        self._limpiar_todos_los_grupos()
        for grupo_config in grupos_config:
            self._crear_grupo_desde_config(grupo_config)

    # ========== METODOS DE CONFIGURACION ==========

    def valores_por_defecto_new(self):
        """Carga valores por defecto en todos los campos"""
        # Carga de trabajo
        self.total_ordenes_var.set(300)
        self.pct_pequeno.set(60)
        self.pct_mediano.set(30)
        self.pct_grande.set(10)
        self.vol_pequeno.set(5)
        self.vol_mediano.set(25)
        self.vol_grande.set(80)
        self.capacidad_carro.set(150)

        # Recursos
        self.num_operarios_terrestres.set(1)
        self.num_montacargas.set(1)
        self.capacidad_montacargas.set(1000)
        self.tiempo_descarga_por_tarea.set(5)

        # Estrategias
        self.dispatch_strategy_var.set('Ejecucion de Plan (Filtro por Prioridad)')

        # Layout
        self.layout_path_var.set('layouts/WH1.tmx')
        self.sequence_path_var.set('layouts/Warehouse_Logic.xlsx')
        self.map_scale_var.set(1.3)
        self.resolution_var.set('Pequena (800x800)')

        # Outbound Staging
        for i in range(1, 8):
            self.outbound_staging_vars[str(i)].set(100 if i == 1 else 0)

        # Validaciones
        self.validar_porcentajes()
        self.actualizar_total()
        self._validar_staging_distribution()

        print("[CONFIGURATOR] Valores por defecto cargados")

    def guardar_config(self):
        """Metodo simplificado para guardar (sera llamado por ConfiguradorSimulador)"""
        print("[VENTANA] Metodo guardar_config() llamado")

    def obtener_configuracion(self):
        """Obtiene la configuracion actual como diccionario"""
        # Construir agent_types desde fleet_groups
        agent_types = []
        for grupo in self.fleet_groups:
            cantidad = grupo['cantidad_var'].get()
            for _ in range(cantidad):
                agent_types.append({
                    'type': grupo['tipo_var'].get(),
                    'capacity': grupo['capacidad_var'].get(),
                    'discharge_time': grupo['tiempo_var'].get(),
                    'work_area_priorities': grupo['priorities'].copy()
                })

        config = {
            'total_ordenes': self.total_ordenes_var.get(),
            'distribucion_tipos': {
                'pequeno': {'porcentaje': self.pct_pequeno.get(), 'volumen': self.vol_pequeno.get()},
                'mediano': {'porcentaje': self.pct_mediano.get(), 'volumen': self.vol_mediano.get()},
                'grande': {'porcentaje': self.pct_grande.get(), 'volumen': self.vol_grande.get()}
            },
            'capacidad_carro': self.capacidad_carro.get(),
            'dispatch_strategy': self.dispatch_strategy_var.get(),
            'layout_file': self.layout_path_var.get(),
            'sequence_file': self.sequence_path_var.get(),
            'map_scale': self.map_scale_var.get(),
            'selected_resolution_key': self.resolution_var.get(),
            'num_operarios_terrestres': self.num_operarios_terrestres.get(),
            'num_montacargas': self.num_montacargas.get(),
            'num_operarios_total': self.num_operarios_terrestres.get() + self.num_montacargas.get(),
            'capacidad_montacargas': self.capacidad_montacargas.get(),
            'tiempo_descarga_por_tarea': self.tiempo_descarga_por_tarea.get(),
            'assignment_rules': self.assignment_rules.copy(),
            'outbound_staging_distribution': {str(i): self.outbound_staging_vars[str(i)].get() for i in range(1, 8)},
            'agent_types': agent_types,
            'num_operarios': self.num_operarios_terrestres.get() + self.num_montacargas.get()
        }

        return config


class ConfiguradorSimulador:
    """Configurador independiente del simulador con funcionalidad de guardado"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Configurador de Simulacion - Gemelo Digital")
        self.root.geometry("650x550")
        self.root.resizable(True, True)

        # Centrar ventana
        self._centrar_ventana()

        # Crear el configurador principal pasando la ventana raiz
        self.ventana_config = VentanaConfiguracion(self.root)

        # CORRECCION: Diferir carga hasta que UI este completamente lista
        # Usar after() para evitar dependencias circulares durante inicializacion
        self.root.after(100, self._cargar_configuracion_existente)

        print("[CONFIGURATOR] Configurador independiente inicializado")

    def _centrar_ventana(self):
        """Centra la ventana en la pantalla"""
        self.root.update_idletasks()
        ancho_ventana = 650
        alto_ventana = 550
        x = (self.root.winfo_screenwidth() // 2) - (ancho_ventana // 2)
        y = (self.root.winfo_screenheight() // 2) - (alto_ventana // 2)
        self.root.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")

    def _cargar_configuracion_existente(self):
        """Carga configuracion existente de config.json al iniciar"""
        config_path = os.path.join(os.path.dirname(__file__), "config.json")

        if os.path.exists(config_path):
            try:
                print(f"[CONFIGURATOR] Cargando configuracion desde: {config_path}")
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # Sanitizar assignment_rules: convertir claves str a int
                if 'assignment_rules' in config and config['assignment_rules']:
                    sanitized_rules = {}
                    for agent_type, rules in config['assignment_rules'].items():
                        sanitized_rules[agent_type] = {int(k): v for k, v in rules.items()}
                    config['assignment_rules'] = sanitized_rules
                    print("[CONFIGURATOR] assignment_rules sanitizadas: claves str -> int")

                self._poblar_ui_desde_config(config)
                print("[CONFIGURATOR] Configuracion cargada exitosamente en UI")

            except (json.JSONDecodeError, KeyError, Exception) as e:
                print(f"[CONFIGURATOR WARN] Error cargando config.json: {e}")
                print("[CONFIGURATOR] Usando valores por defecto")
        else:
            print("[CONFIGURATOR] config.json no encontrado, usando valores por defecto")

    def _poblar_ui_desde_config(self, config: dict):
        """Pobla todos los campos de la UI con datos del config"""
        try:
            # Carga de trabajo
            self.ventana_config.total_ordenes_var.set(config.get('total_ordenes', 300))

            distribucion = config.get('distribucion_tipos', {})
            pequeno = distribucion.get('pequeno', {'porcentaje': 60, 'volumen': 5})
            mediano = distribucion.get('mediano', {'porcentaje': 30, 'volumen': 25})
            grande = distribucion.get('grande', {'porcentaje': 10, 'volumen': 80})

            self.ventana_config.pct_pequeno.set(pequeno.get('porcentaje', 60))
            self.ventana_config.pct_mediano.set(mediano.get('porcentaje', 30))
            self.ventana_config.pct_grande.set(grande.get('porcentaje', 10))

            self.ventana_config.vol_pequeno.set(pequeno.get('volumen', 5))
            self.ventana_config.vol_mediano.set(mediano.get('volumen', 25))
            self.ventana_config.vol_grande.set(grande.get('volumen', 80))

            self.ventana_config.capacidad_carro.set(config.get('capacidad_carro', 150))

            # Recursos
            self.ventana_config.num_operarios_terrestres.set(config.get('num_operarios_terrestres', 1))
            self.ventana_config.num_montacargas.set(config.get('num_montacargas', 1))
            self.ventana_config.capacidad_montacargas.set(config.get('capacidad_montacargas', 1000))
            self.ventana_config.tiempo_descarga_por_tarea.set(config.get('tiempo_descarga_por_tarea', 5))

            # Estrategias
            self.ventana_config.dispatch_strategy_var.set(config.get('dispatch_strategy', 'Ejecucion de Plan (Filtro por Prioridad)'))

            # Layout y archivos
            self.ventana_config.layout_path_var.set(config.get('layout_file', 'layouts/WH1.tmx'))
            self.ventana_config.sequence_path_var.set(config.get('sequence_file', 'layouts/Warehouse_Logic.xlsx'))

            # NUEVO: Escala del mapa
            self.ventana_config.map_scale_var.set(config.get('map_scale', 1.3))

            # Resolucion
            self.ventana_config.resolution_var.set(config.get('selected_resolution_key', 'Pequena (800x800)'))

            # Asignacion de recursos
            assignment_rules = config.get('assignment_rules', {
                "GroundOperator": {1: 1},
                "Forklift": {1: 2, 2: 1, 3: 1, 4: 1, 5: 1}
            })
            self.ventana_config.assignment_rules = assignment_rules

            # Distribucion de OutboundStaging
            outbound_staging_distribution = config.get('outbound_staging_distribution', {
                "1": 100, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0
            })
            for staging_id, percentage in outbound_staging_distribution.items():
                if staging_id in self.ventana_config.outbound_staging_vars:
                    self.ventana_config.outbound_staging_vars[staging_id].set(percentage)
            self.ventana_config._validar_staging_distribution()

            # Actualizar validaciones y resumenes
            self.ventana_config.validar_porcentajes()
            self.ventana_config.actualizar_total()

            # NUEVA FUNCIONALIDAD: Carga de Flota de Agentes desde config.json
            agent_types = config.get('agent_types', [])
            if agent_types:
                print(f"[CONFIGURATOR] Cargando {len(agent_types)} agentes en UI de Flota...")
                grupos_para_ui = self._agrupar_agentes_para_ui(agent_types)
                self.ventana_config._poblar_ui_flota(grupos_para_ui)
                print(f"[CONFIGURATOR] EXITO - Flota cargada: {len(grupos_para_ui)} grupos creados")

            # NUEVA FUNCIONALIDAD: Inicializacion inteligente
            self._inicializacion_inteligente(config)

        except Exception as e:
            print(f"[CONFIGURATOR ERROR] Error poblando UI desde config: {e}")
            raise

    def _inicializacion_inteligente(self, config):
        """
        Inicializacion inteligente: Carga WorkAreas automaticamente y genera flota por defecto si es necesario
        """
        try:
            print("[CONFIGURATOR] Iniciando inicializacion inteligente...")

            # PASO 1: Cargar WorkAreas automaticamente
            sequence_file = self.ventana_config.sequence_path_var.get()
            if sequence_file:
                try:
                    print(f"[CONFIGURATOR] Cargando WorkAreas automaticamente desde: {sequence_file}")
                    self.ventana_config._cargar_work_areas_automatico(sequence_file)
                    print(f"[CONFIGURATOR] EXITO - WorkAreas cargadas: {self.ventana_config.available_work_areas}")
                except Exception as e:
                    print(f"[CONFIGURATOR] ADVERTENCIA - Error cargando WorkAreas: {e}")
                    # Continuar sin fallar - WorkAreas se pueden cargar manualmente despues

            # PASO 2: Verificar si existe configuracion de flota
            agent_types = config.get('agent_types', [])

            # PASO 3: Generar flota por defecto si no existe configuracion
            if not agent_types and self.ventana_config.available_work_areas:
                print("[CONFIGURATOR] No se encontro configuracion de flota. Generando configuracion por defecto...")
                try:
                    # Llamar a la funcion de generacion automatica (sin dialogos)
                    self._generar_flota_por_defecto_silencioso()
                    print("[CONFIGURATOR] EXITO - Flota por defecto generada automaticamente")
                except Exception as e:
                    print(f"[CONFIGURATOR] ADVERTENCIA - Error generando flota por defecto: {e}")
                    # Continuar sin fallar
            else:
                print(f"[CONFIGURATOR] Configuracion de flota existente encontrada: {len(agent_types)} tipos de agentes")

        except Exception as e:
            print(f"[CONFIGURATOR ERROR] Error en inicializacion inteligente: {e}")
            # No lanzar excepcion - la inicializacion inteligente es opcional

    def _agrupar_agentes_para_ui(self, agent_types_list):
        """
        Agrupa agent_types del JSON en formato para _poblar_ui_flota
        Agentes con mismo type, capacity, discharge_time y work_area_priorities se agrupan
        """
        grupos = {}

        for agent in agent_types_list:
            agent_type = agent.get('type', 'GroundOperator')
            capacity = agent.get('capacity', 150)
            discharge_time = agent.get('discharge_time', 5)
            work_area_priorities = agent.get('work_area_priorities', {})

            # Crear clave unica para agrupar agentes similares
            priority_key = tuple(sorted(work_area_priorities.items()))
            group_key = (agent_type, capacity, discharge_time, priority_key)

            if group_key not in grupos:
                grupos[group_key] = {
                    'agent_type': agent_type,
                    'cantidad': 0,
                    'capacidad': capacity,
                    'tiempo_descarga': discharge_time,
                    'work_area_priorities': work_area_priorities
                }

            grupos[group_key]['cantidad'] += 1

        return list(grupos.values())

    def _generar_flota_por_defecto_silencioso(self):
        """
        Version silenciosa de generacion de flota por defecto (sin dialogos de confirmacion)
        Se usa durante la inicializacion automatica
        """
        try:
            # Verificar que hay WorkAreas disponibles
            if not self.ventana_config.available_work_areas:
                print("[CONFIGURATOR] No hay WorkAreas disponibles para generar flota por defecto")
                return

            print("[CONFIGURATOR] Generando flota por defecto silenciosa...")

            # Usar la nueva funcion unificada sin dialogos
            config_defecto = self.ventana_config._generar_config_defecto()

            # Limpiar y poblar sin confirmaciones
            self.ventana_config._limpiar_todos_los_grupos()
            for group_config in config_defecto:
                self.ventana_config._crear_grupo_desde_config(group_config)

            print("[CONFIGURATOR] EXITO - Flota por defecto generada silenciosamente")

        except Exception as e:
            print(f"[CONFIGURATOR ERROR] Error en generacion silenciosa de flota: {e}")
            raise

    def guardar_configuracion(self):
        """Guarda la configuracion actual en config.json"""
        try:
            # Validar configuracion antes de guardar
            if not self._validar_configuracion_actual():
                return

            # Obtener configuracion de la UI
            config = self._obtener_configuracion_ui()

            # Guardar en archivo JSON
            config_path = os.path.join(os.path.dirname(__file__), "config.json")

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

            messagebox.showinfo(
                "Configuracion Guardada",
                f"La configuracion se ha guardado exitosamente en:\n{config_path}\n\n"
                f"Ahora puedes ejecutar 'python run_simulator.py' directamente "
                f"para usar esta configuracion automaticamente."
            )
            print(f"[CONFIGURATOR] Configuracion guardada en: {config_path}")

        except Exception as e:
            messagebox.showerror(
                "Error al Guardar",
                f"No se pudo guardar la configuracion:\n{str(e)}"
            )
            print(f"[CONFIGURATOR ERROR] Error guardando configuracion: {e}")

    def cargar_defaults(self):
        """Carga los valores por defecto en la UI"""
        try:
            self.ventana_config.valores_por_defecto_new()
            messagebox.showinfo(
                "Valores por Defecto",
                "Los valores por defecto han sido cargados exitosamente."
            )
            print("[CONFIGURATOR] Valores por defecto cargados")

        except Exception as e:
            messagebox.showerror(
                "Error al Cargar Defaults",
                f"No se pudieron cargar los valores por defecto:\n{str(e)}"
            )
            print(f"[CONFIGURATOR ERROR] Error cargando defaults: {e}")

    def probar_configuracion(self):
        """Guarda la configuracion y lanza el simulador para probarla"""
        try:
            # Primero guardar la configuracion
            self.guardar_configuracion()

            # Confirmar si quiere lanzar el simulador
            if messagebox.askyesno(
                "Probar Configuracion",
                "Configuracion guardada. Deseas lanzar el simulador ahora para probarla?"
            ):
                # Lanzar simulador con directorio de trabajo correcto
                import subprocess
                project_root = os.path.dirname(os.path.abspath(__file__))
                simulator_path = os.path.join(project_root, "run_simulator.py")
                subprocess.Popen([sys.executable, simulator_path], cwd=project_root)

                print(f"[CONFIGURATOR] Simulador lanzado desde: {project_root}")

        except Exception as e:
            messagebox.showerror(
                "Error al Probar",
                f"No se pudo lanzar el simulador:\n{str(e)}"
            )
            print(f"[CONFIGURATOR ERROR] Error probando configuracion: {e}")

    def salir(self):
        """Cierra el configurador"""
        if messagebox.askyesno(
            "Confirmar Salida",
            "Estas seguro de que deseas salir del configurador?"
        ):
            print("[CONFIGURATOR] Cerrando configurador")
            self.root.destroy()

    def _validar_configuracion_actual(self) -> bool:
        """Valida la configuracion actual de la UI"""
        try:
            # Usar el validador existente de VentanaConfiguracion
            total_ordenes = self.ventana_config.total_ordenes_var.get()
            pct_pequeno = self.ventana_config.pct_pequeno.get()
            pct_mediano = self.ventana_config.pct_mediano.get()
            pct_grande = self.ventana_config.pct_grande.get()
            vol_pequeno = self.ventana_config.vol_pequeno.get()
            vol_mediano = self.ventana_config.vol_mediano.get()
            vol_grande = self.ventana_config.vol_grande.get()
            capacidad_carro = self.ventana_config.capacidad_carro.get()
            op_terrestres = self.ventana_config.num_operarios_terrestres.get()
            montacargas = self.ventana_config.num_montacargas.get()

            # Validar configuracion de picking
            picking_valid = self.ventana_config._validar_configuracion_picking(
                total_ordenes, pct_pequeno, pct_mediano, pct_grande,
                vol_pequeno, vol_mediano, vol_grande, capacidad_carro,
                op_terrestres, montacargas, op_terrestres + montacargas
            )

            # Validar distribucion de OutboundStaging
            staging_valid = self.ventana_config._validar_staging_distribution()

            if not staging_valid:
                messagebox.showerror("Error de Configuracion",
                                   "La distribucion de Outbound Staging debe sumar exactamente 100%.")

            return picking_valid and staging_valid
        except Exception as e:
            messagebox.showerror("Error de Validacion", f"Error validando configuracion: {str(e)}")
            return False

    def _obtener_configuracion_ui(self) -> dict:
        """Obtiene la configuracion actual de la UI como diccionario"""
        # Obtener configuracion desde VentanaConfiguracion
        config = self.ventana_config.obtener_configuracion()

        # Anadir campos de compatibilidad
        config['tareas_zona_a'] = 0
        config['tareas_zona_b'] = 0
        config['num_operarios'] = config['num_operarios_total']

        # Convertir rutas a relativas
        config['layout_file'] = self._make_relative_path(config['layout_file'])
        config['sequence_file'] = self._make_relative_path(config['sequence_file'])

        return config

    def _make_relative_path(self, file_path: str) -> str:
        """Convierte rutas absolutas a relativas respecto al directorio del proyecto"""
        if not file_path:
            return file_path

        try:
            project_root = os.path.dirname(os.path.abspath(__file__))
            abs_path = os.path.abspath(file_path)

            # Si el archivo esta dentro del proyecto, convertir a relativa
            if abs_path.startswith(project_root):
                relative_path = os.path.relpath(abs_path, project_root)
                return relative_path.replace('\\', '/')  # Normalizar separadores para config.json
            else:
                # Si esta fuera del proyecto, mantener ruta absoluta
                return abs_path.replace('\\', '/')

        except (ValueError, OSError):
            # En caso de error, devolver la ruta original
            return file_path

    def ejecutar(self):
        """Ejecuta el configurador"""
        print("[CONFIGURATOR] Iniciando configurador independiente...")
        print("[CONFIGURATOR] Use 'Guardar Configuracion' para crear config.json")
        print("[CONFIGURATOR] Luego ejecute 'python run_simulator.py' para usar la configuracion")

        # Conectar boton de guardar
        for widget in self.ventana_config.parent.winfo_children():
            if isinstance(widget, ttk.Frame):
                for btn in widget.winfo_children():
                    if isinstance(btn, ttk.Button):
                        if "Guardar" in btn.cget('text'):
                            btn.config(command=self.guardar_configuracion)
                        elif "Defaults" in btn.cget('text'):
                            btn.config(command=self.cargar_defaults)
                        elif "Salir" in btn.cget('text'):
                            btn.config(command=self.salir)

        self.root.mainloop()


def main():
    """Funcion principal del configurador"""
    print("="*60)
    print("CONFIGURADOR DE SIMULACION - GEMELO DIGITAL")
    print("Herramienta independiente de configuracion")
    print("="*60)
    print()

    configurador = ConfiguradorSimulador()
    configurador.ejecutar()


if __name__ == "__main__":
    main()
