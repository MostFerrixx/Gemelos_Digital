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
        """Inicializa la ventana de configuracion"""
        self.parent = parent
        self.available_work_areas = []
        self.assignment_rules = {"GroundOperator": {}, "Forklift": {}}
        self.assignment_widgets = {"GroundOperator": [], "Forklift": []}
        self.fleet_groups = []  # Lista de grupos de flota creados

        # Crear notebook con pestanas
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Crear pestanas (5 tabs as per user specification)
        self.tab_carga = ttk.Frame(self.notebook)
        self.tab_estrategias = ttk.Frame(self.notebook)
        self.tab_flota = ttk.Frame(self.notebook)
        self.tab_layout_datos = ttk.Frame(self.notebook)
        self.tab_staging = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_carga, text="Carga de Trabajo")
        self.notebook.add(self.tab_estrategias, text="Estrategias")
        self.notebook.add(self.tab_flota, text="Flota de Agentes")
        self.notebook.add(self.tab_layout_datos, text="Layout y Datos")
        self.notebook.add(self.tab_staging, text="Outbound Staging")

        # Inicializar variables
        self._inicializar_variables()

        # Crear widgets en cada pestana
        self._crear_widgets_carga()
        self._crear_widgets_estrategias()
        self._crear_widgets_flota()
        self._crear_widgets_layout_datos()
        self._crear_widgets_staging()

        # Crear frame de botones en la parte inferior
        self._crear_botones_accion()

    def _inicializar_variables(self):
        """Inicializa todas las variables de tkinter"""
        # Carga de trabajo
        self.total_ordenes_var = tk.IntVar(value=300)
        self.pct_pequeno = tk.IntVar(value=60)
        self.pct_mediano = tk.IntVar(value=30)
        self.pct_grande = tk.IntVar(value=10)
        self.vol_pequeno = tk.IntVar(value=5)
        self.vol_mediano = tk.IntVar(value=25)
        self.vol_grande = tk.IntVar(value=80)

        # Recursos
        self.num_operarios_terrestres = tk.IntVar(value=1)
        self.num_montacargas = tk.IntVar(value=1)
        self.capacidad_montacargas = tk.IntVar(value=1000)
        self.capacidad_carro = tk.IntVar(value=150)
        self.tiempo_descarga_por_tarea = tk.IntVar(value=5)

        # Estrategias (2 tipos como especifico el usuario)
        self.dispatch_strategy_var = tk.StringVar(value="Optimizacion Global")
        self.tour_type_var = tk.StringVar(value="Tour Mixto (Multi-Destino)")

        # Layout
        self.layout_path_var = tk.StringVar(value="layouts/WH1.tmx")
        self.sequence_path_var = tk.StringVar(value="layouts/Warehouse_Logic.xlsx")
        self.map_scale_var = tk.DoubleVar(value=1.3)

        # Resolucion
        self.resolution_var = tk.StringVar(value="Pequena (800x800)")

        # Outbound Staging Distribution
        self.outbound_staging_vars = {
            str(i): tk.IntVar(value=100 if i == 1 else 0)
            for i in range(1, 8)
        }

        # Flota de Agentes - Grupos dinamicos
        self.fleet_groups = {
            'GroundOperator': [],  # Lista de diccionarios con info de cada grupo
            'Forklift': []
        }
        self.fleet_group_widgets = {
            'GroundOperator': [],  # Lista de widgets para cada grupo
            'Forklift': []
        }
        self.available_work_areas = []  # Se cargara desde sequence file

    def _crear_widgets_carga(self):
        """Crea widgets de la pestana Carga de Trabajo"""
        frame = ttk.LabelFrame(self.tab_carga, text="Configuracion de Ordenes", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Total de ordenes
        row = 0
        ttk.Label(frame, text="Total de Ordenes:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.total_ordenes_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)

        # Distribucion de tipos
        row += 1
        ttk.Label(frame, text="DISTRIBUCION DE TIPOS", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=4, pady=10)

        # Pequeno
        row += 1
        ttk.Label(frame, text="Ordenes Pequenas (%):").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.pct_pequeno, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, text="Volumen:").grid(row=row, column=2, sticky=tk.W, pady=5, padx=(10, 0))
        ttk.Entry(frame, textvariable=self.vol_pequeno, width=15).grid(row=row, column=3, sticky=tk.W, pady=5)

        # Mediano
        row += 1
        ttk.Label(frame, text="Ordenes Medianas (%):").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.pct_mediano, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, text="Volumen:").grid(row=row, column=2, sticky=tk.W, pady=5, padx=(10, 0))
        ttk.Entry(frame, textvariable=self.vol_mediano, width=15).grid(row=row, column=3, sticky=tk.W, pady=5)

        # Grande
        row += 1
        ttk.Label(frame, text="Ordenes Grandes (%):").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.pct_grande, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, text="Volumen:").grid(row=row, column=2, sticky=tk.W, pady=5, padx=(10, 0))
        ttk.Entry(frame, textvariable=self.vol_grande, width=15).grid(row=row, column=3, sticky=tk.W, pady=5)

        # Label de validacion
        row += 1
        self.label_validacion = ttk.Label(frame, text="", foreground="green")
        self.label_validacion.grid(row=row, column=0, columnspan=4, pady=10)

        # Validar porcentajes en tiempo real
        self.pct_pequeno.trace_add("write", lambda *args: self.validar_porcentajes())
        self.pct_mediano.trace_add("write", lambda *args: self.validar_porcentajes())
        self.pct_grande.trace_add("write", lambda *args: self.validar_porcentajes())

    def _crear_widgets_estrategias(self):
        """Crea widgets de la pestana Estrategias - Solo 2 estrategias"""
        frame = ttk.LabelFrame(self.tab_estrategias, text="Estrategias de Operacion", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        row = 0

        # Estrategia de Despacho
        ttk.Label(frame, text="Estrategia de Despacho:").grid(row=row, column=0, sticky=tk.W, pady=5)
        estrategias_despacho = [
            "Optimizacion Global",
            "Ejecucion de Plan (Filtro por Prioridad)"
        ]
        combo_despacho = ttk.Combobox(frame, textvariable=self.dispatch_strategy_var, values=estrategias_despacho, width=40)
        combo_despacho.grid(row=row, column=1, sticky=tk.W, pady=5)

        # Tipo de Tour de Picking
        row += 1
        ttk.Label(frame, text="Tipo de Tour de Picking:").grid(row=row, column=0, sticky=tk.W, pady=5)
        tipos_tour = [
            "Tour Mixto (Multi-Destino)",
            "Tour Simple (Un Destino)"
        ]
        combo_tour = ttk.Combobox(frame, textvariable=self.tour_type_var, values=tipos_tour, width=40)
        combo_tour.grid(row=row, column=1, sticky=tk.W, pady=5)

    def _crear_widgets_flota(self):
        """Crea widgets de la pestana Flota de Agentes con grupos dinamicos"""
        # Frame principal con scroll
        main_canvas = tk.Canvas(self.tab_flota)
        main_scrollbar = ttk.Scrollbar(self.tab_flota, orient=tk.VERTICAL, command=main_canvas.yview)
        self.flota_scrollable_frame = ttk.Frame(main_canvas)

        self.flota_scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )

        main_canvas.create_window((0, 0), window=self.flota_scrollable_frame, anchor=tk.NW)
        main_canvas.configure(yscrollcommand=main_scrollbar.set)

        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Titulo
        ttk.Label(self.flota_scrollable_frame, text="Configuracion de Flota de Agentes",
                 font=("Arial", 12, "bold"), foreground="blue").pack(pady=10)

        # Boton Generar Flota por Defecto
        ttk.Button(self.flota_scrollable_frame, text="Generar Flota por Defecto",
                  command=self._generar_flota_defecto).pack(pady=5)

        # Seccion Operarios Terrestres
        self.ground_operators_frame = ttk.LabelFrame(self.flota_scrollable_frame,
                                                     text="Operarios Terrestres", padding=10)
        self.ground_operators_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        ttk.Button(self.ground_operators_frame, text="+ Anadir Grupo",
                  command=lambda: self._anadir_grupo_flota('GroundOperator')).pack(anchor=tk.W, pady=5)

        self.ground_operators_container = ttk.Frame(self.ground_operators_frame)
        self.ground_operators_container.pack(fill=tk.BOTH, expand=True)

        # Seccion Montacargas
        self.forklifts_frame = ttk.LabelFrame(self.flota_scrollable_frame,
                                             text="Montacargas", padding=10)
        self.forklifts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        ttk.Button(self.forklifts_frame, text="+ Anadir Grupo",
                  command=lambda: self._anadir_grupo_flota('Forklift')).pack(anchor=tk.W, pady=5)

        self.forklifts_container = ttk.Frame(self.forklifts_frame)
        self.forklifts_container.pack(fill=tk.BOTH, expand=True)

    def _anadir_grupo_flota(self, agent_type):
        """Anade un nuevo grupo de agentes (Operarios Terrestres o Montacargas)"""
        # Determinar contenedor y valores por defecto
        if agent_type == 'GroundOperator':
            container = self.ground_operators_container
            default_capacity = 150
        else:  # Forklift
            container = self.forklifts_container
            default_capacity = 1000

        group_num = len(self.fleet_groups[agent_type]) + 1

        # Frame para el grupo
        group_frame = ttk.LabelFrame(container, text=f"Grupo {group_num}", padding=10)
        group_frame.pack(fill=tk.X, pady=5, padx=5)

        # Frame superior con parametros
        params_frame = ttk.Frame(group_frame)
        params_frame.pack(fill=tk.X)

        # Cantidad
        ttk.Label(params_frame, text="Cantidad:").grid(row=0, column=0, sticky=tk.W, padx=5)
        cantidad_var = tk.IntVar(value=2)
        cantidad_spin = ttk.Spinbox(params_frame, from_=1, to=50, textvariable=cantidad_var, width=10)
        cantidad_spin.grid(row=0, column=1, padx=5)

        # Capacidad
        ttk.Label(params_frame, text="Capacidad (L):").grid(row=0, column=2, sticky=tk.W, padx=5)
        capacidad_var = tk.IntVar(value=default_capacity)
        capacidad_spin = ttk.Spinbox(params_frame, from_=50, to=2000, textvariable=capacidad_var, width=10)
        capacidad_spin.grid(row=0, column=3, padx=5)

        # Tiempo Descarga
        ttk.Label(params_frame, text="Tiempo Descarga (s):").grid(row=0, column=4, sticky=tk.W, padx=5)
        tiempo_var = tk.IntVar(value=5)
        tiempo_spin = ttk.Spinbox(params_frame, from_=1, to=60, textvariable=tiempo_var, width=10)
        tiempo_spin.grid(row=0, column=5, padx=5)

        # Boton eliminar grupo
        ttk.Button(params_frame, text="x", width=3,
                  command=lambda: self._eliminar_grupo_flota(agent_type, group_num-1, group_frame)).grid(
                      row=0, column=6, padx=10)

        # Seccion de Prioridades de Work Area
        priorities_frame = ttk.LabelFrame(group_frame, text="Prioridades de Work Area", padding=5)
        priorities_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Boton para agregar prioridad
        ttk.Button(priorities_frame, text="+", width=3,
                  command=lambda: self._anadir_prioridad_wa(agent_type, group_num-1,
                                                            priorities_container)).pack(anchor=tk.W, pady=2)

        # Contenedor de prioridades
        priorities_container = ttk.Frame(priorities_frame)
        priorities_container.pack(fill=tk.BOTH, expand=True)

        # Guardar informacion del grupo
        group_data = {
            'frame': group_frame,
            'cantidad_var': cantidad_var,
            'capacidad_var': capacidad_var,
            'tiempo_var': tiempo_var,
            'priorities_container': priorities_container,
            'priorities': []  # Lista de {wa_var, priority_var, frame}
        }

        self.fleet_groups[agent_type].append(group_data)

    def _anadir_prioridad_wa(self, agent_type, group_idx, priorities_container):
        """Anade una fila de Work Area y Prioridad"""
        priority_frame = ttk.Frame(priorities_container)
        priority_frame.pack(fill=tk.X, pady=2)

        # Work Area dropdown
        ttk.Label(priority_frame, text="Work Area:").grid(row=0, column=0, sticky=tk.W, padx=5)
        wa_var = tk.StringVar()
        wa_combo = ttk.Combobox(priority_frame, textvariable=wa_var, width=15, state='readonly')
        wa_combo['values'] = self.available_work_areas if self.available_work_areas else ["1", "2", "3", "4", "5"]
        wa_combo.grid(row=0, column=1, padx=5)

        # Prioridad spinner
        ttk.Label(priority_frame, text="Prioridad:").grid(row=0, column=2, sticky=tk.W, padx=5)
        priority_var = tk.IntVar(value=1)
        priority_spin = ttk.Spinbox(priority_frame, from_=1, to=10, textvariable=priority_var, width=10)
        priority_spin.grid(row=0, column=3, padx=5)

        # Boton eliminar prioridad
        ttk.Button(priority_frame, text="x", width=3,
                  command=lambda: self._eliminar_prioridad_wa(agent_type, group_idx,
                                                              priority_frame)).grid(row=0, column=4, padx=5)

        # Guardar en el grupo
        priority_data = {
            'frame': priority_frame,
            'wa_var': wa_var,
            'priority_var': priority_var
        }
        self.fleet_groups[agent_type][group_idx]['priorities'].append(priority_data)

    def _eliminar_prioridad_wa(self, agent_type, group_idx, priority_frame):
        """Elimina una fila de prioridad de Work Area"""
        priority_frame.destroy()
        # Remover de la lista
        group = self.fleet_groups[agent_type][group_idx]
        group['priorities'] = [p for p in group['priorities'] if p['frame'] != priority_frame]

    def _eliminar_grupo_flota(self, agent_type, group_idx, group_frame):
        """Elimina un grupo completo de la flota"""
        group_frame.destroy()
        # Remover de la lista
        del self.fleet_groups[agent_type][group_idx]
        # Renumerar grupos restantes
        self._renumerar_grupos_flota(agent_type)

    def _renumerar_grupos_flota(self, agent_type):
        """Renumera los grupos despues de eliminar uno"""
        for idx, group in enumerate(self.fleet_groups[agent_type]):
            group['frame'].config(text=f"Grupo {idx + 1}")

    def _generar_flota_defecto(self):
        """Genera configuracion de flota por defecto"""
        # Limpiar grupos existentes
        for agent_type in ['GroundOperator', 'Forklift']:
            for group in list(self.fleet_groups[agent_type]):
                group['frame'].destroy()
            self.fleet_groups[agent_type].clear()

        # Crear 1 grupo de Operarios Terrestres
        self._anadir_grupo_flota('GroundOperator')

        # Crear 1 grupo de Montacargas
        self._anadir_grupo_flota('Forklift')

        messagebox.showinfo("Flota Generada", "Configuracion de flota por defecto generada exitosamente.")

    def _crear_widgets_asignacion(self):
        """Crea widgets de la pestana Asignacion de Recursos"""
        main_frame = ttk.Frame(self.tab_asignacion)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Titulo
        ttk.Label(main_frame, text="Asignacion de Prioridades por Nivel de WorkArea",
                 font=("Arial", 11, "bold")).pack(pady=10)

        # Descripcion
        desc = ttk.Label(main_frame, text="Configura la prioridad de cada tipo de agente para cada nivel.\nPrioridad 1 = Mayor prioridad, numeros mayores = menor prioridad.",
                        justify=tk.CENTER)
        desc.pack(pady=5)

        # Frame con scroll para las asignaciones
        canvas = tk.Canvas(main_frame, height=300)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.assignment_frame = ttk.Frame(canvas)

        self.assignment_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.assignment_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Generar Asignacion por Defecto",
                  command=self._generar_asignacion_defecto).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Limpiar Asignaciones",
                  command=self._limpiar_asignaciones).pack(side=tk.LEFT, padx=5)

        # Inicializar con asignacion por defecto
        self._generar_asignacion_defecto()

    def _crear_widgets_layout_datos(self):
        """Crea widgets de la pestana Layout y Datos segun screenshot original"""
        # SECCION 1: Seleccion de Archivo de Layout
        frame_layout = ttk.LabelFrame(self.tab_layout_datos, text="Seleccion de Archivo de Layout", padding=10)
        frame_layout.pack(fill=tk.X, padx=10, pady=(10, 5))

        ttk.Label(frame_layout, text="Archivo TMX:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        ttk.Entry(frame_layout, textvariable=self.layout_path_var, width=50).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Button(frame_layout, text="Seleccionar...", command=self._examinar_tmx).grid(row=0, column=2, padx=5)

        # SECCION 2: Gestion de Datos de Secuencia (CSV)
        frame_secuencia = ttk.LabelFrame(self.tab_layout_datos, text="Gestion de Datos de Secuencia (CSV)", padding=10)
        frame_secuencia.pack(fill=tk.X, padx=10, pady=5)

        # Archivo de Secuencia
        ttk.Label(frame_secuencia, text="Archivo de Secuencia:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        ttk.Entry(frame_secuencia, textvariable=self.sequence_path_var, width=50).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Button(frame_secuencia, text="Seleccionar...", command=self._examinar_sequence).grid(row=0, column=2, padx=5)

        # Botones de accion
        button_frame = ttk.Frame(frame_secuencia)
        button_frame.grid(row=1, column=0, columnspan=3, pady=10)

        ttk.Button(button_frame, text="Generar Plantilla desde TMX",
                  command=self._generar_plantilla_desde_tmx).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Poblar SKUs Aleatorios en CSV",
                  command=self._poblar_skus_aleatorios).pack(side=tk.LEFT, padx=5)

        # Texto explicativo
        help_text = (
            "• Generar Plantilla: Analiza el TMX y crea un CSV con ubicaciones de picking\n"
            "• Poblar SKUs: Rellena el CSV con SKUs y cantidades aleatorias"
        )
        help_label = ttk.Label(frame_secuencia, text=help_text, foreground="gray", justify=tk.LEFT)
        help_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5, padx=5)

        # SECCION 3: Configuracion de Ventana
        frame_ventana = ttk.LabelFrame(self.tab_layout_datos, text="Configuracion de Ventana", padding=10)
        frame_ventana.pack(fill=tk.X, padx=10, pady=5)

        # Resolucion con label descriptivo
        res_frame = ttk.Frame(frame_ventana)
        res_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(res_frame, text="Resolucion de Pantalla:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        resoluciones = ["Pequena (800x800)", "Mediana (1024x768)", "Grande (1280x1024)", "Extra Grande (1920x1080)"]
        combo = ttk.Combobox(res_frame, textvariable=self.resolution_var, values=resoluciones, width=25, state='readonly')
        combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(res_frame, text="(Tamano de ventana del simulador)", foreground="gray").pack(side=tk.LEFT, padx=5)

        # Texto explicativo
        help_res = "Pequena: Rendimiento optimo | Mediana: Balance | Grande: Mejor visualizacion"
        ttk.Label(frame_ventana, text=help_res, foreground="gray").pack(anchor=tk.W, padx=5, pady=(0, 5))

    def _generar_plantilla_desde_tmx(self):
        """Genera Warehouse_Logic.xlsx desde el archivo TMX"""
        tmx_file = self.layout_path_var.get()
        if not tmx_file or not os.path.exists(tmx_file):
            messagebox.showerror("Error", "Debe seleccionar un archivo TMX valido primero.")
            return

        try:
            # TODO: Implementar logica para parsear TMX y crear XLSX
            messagebox.showinfo("Generacion de Plantilla",
                              "Funcionalidad en desarrollo.\n\n"
                              "Creara Warehouse_Logic.xlsx con:\n"
                              "- Columnas de ubicaciones de picking\n"
                              "- Datos por defecto para el simulador\n"
                              "- Estructura lista para modificar")
        except Exception as e:
            messagebox.showerror("Error", f"Error generando plantilla: {e}")

    def _poblar_skus_aleatorios(self):
        """Pobla el CSV con SKUs y cantidades aleatorias"""
        csv_file = self.sequence_path_var.get()
        if not csv_file:
            messagebox.showerror("Error", "Debe seleccionar un archivo de secuencia primero.")
            return

        try:
            # TODO: Implementar logica para poblar CSV con datos aleatorios
            messagebox.showinfo("Poblar SKUs",
                              "Funcionalidad en desarrollo.\n\n"
                              "Rellenara el CSV con:\n"
                              "- SKUs aleatorios\n"
                              "- Cantidades aleatorias")
        except Exception as e:
            messagebox.showerror("Error", f"Error poblando SKUs: {e}")

    def _crear_widgets_staging(self):
        """Crea widgets de la pestana Outbound Staging"""
        frame = ttk.LabelFrame(self.tab_staging, text="Distribucion de Staging", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(frame, text="Distribucion porcentual de ordenes por zona de staging:",
                 font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=3, pady=10)

        for i in range(1, 8):
            row = i
            ttk.Label(frame, text=f"Staging {i}:").grid(row=row, column=0, sticky=tk.W, pady=5)
            ttk.Entry(frame, textvariable=self.outbound_staging_vars[str(i)], width=15).grid(
                row=row, column=1, sticky=tk.W, pady=5)
            ttk.Label(frame, text="%").grid(row=row, column=2, sticky=tk.W, pady=5)

            # Trace para validacion
            self.outbound_staging_vars[str(i)].trace_add("write",
                lambda *args: self._validar_staging_distribution())

        self.staging_validation_label = ttk.Label(frame, text="", foreground="green")
        self.staging_validation_label.grid(row=8, column=0, columnspan=3, pady=10)

    def _crear_botones_accion(self):
        """Crea botones de accion en la parte inferior"""
        button_frame = ttk.Frame(self.parent)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Guardar Configuracion",
                  command=self._guardar_callback).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cargar Valores por Defecto",
                  command=self.valores_por_defecto_new).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Salir",
                  command=self._salir_callback).pack(side=tk.RIGHT, padx=5)

    # ========================================================================
    # METODOS DE VALIDACION
    # ========================================================================

    def validar_porcentajes(self):
        """Valida que los porcentajes sumen 100%"""
        try:
            total = self.pct_pequeno.get() + self.pct_mediano.get() + self.pct_grande.get()
            if total == 100:
                self.label_validacion.config(text="OK: Suma 100%", foreground="green")
                return True
            else:
                self.label_validacion.config(text=f"ERROR: Suma {total}% (debe ser 100%)", foreground="red")
                return False
        except:
            self.label_validacion.config(text="ERROR: Valores invalidos", foreground="red")
            return False

    def actualizar_total(self):
        """Actualiza el total de recursos"""
        try:
            total = self.num_operarios_terrestres.get() + self.num_montacargas.get()
            self.label_total_recursos.config(text=f"Total de Recursos: {total}")
        except:
            self.label_total_recursos.config(text="Total de Recursos: ERROR")

    def _validar_staging_distribution(self):
        """Valida que la distribucion de staging sume 100%"""
        try:
            total = sum(var.get() for var in self.outbound_staging_vars.values())
            if total == 100:
                self.staging_validation_label.config(text="OK: Suma 100%", foreground="green")
                return True
            else:
                self.staging_validation_label.config(
                    text=f"ERROR: Suma {total}% (debe ser 100%)", foreground="red")
                return False
        except:
            self.staging_validation_label.config(text="ERROR: Valores invalidos", foreground="red")
            return False

    def _validar_configuracion_picking(self, total_ordenes, pct_pequeno, pct_mediano, pct_grande,
                                      vol_pequeno, vol_mediano, vol_grande, capacidad_carro,
                                      op_terrestres, montacargas, total_recursos):
        """Valida la configuracion de picking"""
        # Validacion basica
        if total_ordenes <= 0:
            messagebox.showerror("Error", "El total de ordenes debe ser mayor a 0")
            return False

        if pct_pequeno + pct_mediano + pct_grande != 100:
            messagebox.showerror("Error", "Los porcentajes deben sumar 100%")
            return False

        if capacidad_carro <= 0:
            messagebox.showerror("Error", "La capacidad del carro debe ser mayor a 0")
            return False

        if total_recursos <= 0:
            messagebox.showerror("Error", "Debe haber al menos un recurso")
            return False

        return True

    # ========================================================================
    # METODOS DE ARCHIVOS
    # ========================================================================

    def _examinar_tmx(self):
        """Abre dialogo para seleccionar archivo TMX"""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo TMX",
            filetypes=[("TMX Files", "*.tmx"), ("All Files", "*.*")]
        )
        if filename:
            self.layout_path_var.set(filename)

    def _examinar_sequence(self):
        """Abre dialogo para seleccionar archivo de secuencia"""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo de secuencia",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if filename:
            self.sequence_path_var.set(filename)

    # ========================================================================
    # METODOS DE ASIGNACION DE RECURSOS
    # ========================================================================

    def _generar_asignacion_defecto(self):
        """Genera asignacion de recursos por defecto"""
        # Limpiar asignaciones existentes
        self._limpiar_asignaciones()

        # Asignaciones por defecto
        default_assignments = {
            "GroundOperator": {1: 1},
            "Forklift": {1: 2, 2: 1, 3: 1, 4: 1, 5: 1}
        }

        self.assignment_rules = default_assignments
        self._update_assignment_display()

    def _limpiar_asignaciones(self):
        """Limpia todas las asignaciones"""
        for widget in self.assignment_frame.winfo_children():
            widget.destroy()
        self.assignment_widgets = {"GroundOperator": [], "Forklift": []}
        self.assignment_rules = {"GroundOperator": {}, "Forklift": {}}

    def _update_assignment_display(self):
        """Actualiza la visualizacion de asignaciones"""
        self._limpiar_asignaciones()

        row = 0
        for agent_type in ["GroundOperator", "Forklift"]:
            # Titulo del tipo de agente
            label_frame = ttk.LabelFrame(self.assignment_frame, text=agent_type, padding=10)
            label_frame.grid(row=row, column=0, sticky=tk.EW, padx=5, pady=5)
            row += 1

            # Encabezados
            ttk.Label(label_frame, text="Nivel", font=("Arial", 9, "bold")).grid(row=0, column=0, padx=5)
            ttk.Label(label_frame, text="Prioridad", font=("Arial", 9, "bold")).grid(row=0, column=1, padx=5)

            # Crear fila para cada nivel asignado
            agent_row = 1
            if agent_type in self.assignment_rules:
                for level, priority in sorted(self.assignment_rules[agent_type].items()):
                    level_var = tk.IntVar(value=level)
                    priority_var = tk.IntVar(value=priority)

                    ttk.Label(label_frame, text=f"Nivel {level}:").grid(row=agent_row, column=0, sticky=tk.W, padx=5, pady=2)
                    ttk.Entry(label_frame, textvariable=priority_var, width=10).grid(row=agent_row, column=1, padx=5, pady=2)

                    self.assignment_widgets[agent_type].append({
                        'level_var': level_var,
                        'priority_var': priority_var
                    })
                    agent_row += 1

    # ========================================================================
    # METODOS DE FLOTA
    # ========================================================================

    def _cargar_work_areas_automatico(self, sequence_file):
        """Carga WorkAreas desde el archivo de secuencia"""
        try:
            if not os.path.exists(sequence_file):
                raise FileNotFoundError(f"Archivo no encontrado: {sequence_file}")

            # Leer WorkAreas del archivo Excel
            import openpyxl
            wb = openpyxl.load_workbook(sequence_file, read_only=True, data_only=True)

            # Buscar hoja Warehouse_Logic
            if 'Warehouse_Logic' in wb.sheetnames:
                ws = wb['Warehouse_Logic']
                work_areas = set()

                # Leer WorkAreas desde la columna WorkArea
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if row and len(row) > 2:
                        work_area = row[2]  # Columna C
                        if work_area:
                            work_areas.add(str(work_area))

                self.available_work_areas = sorted(list(work_areas))
                print(f"[VENTANA_CONFIG] WorkAreas cargadas: {self.available_work_areas}")
            else:
                # Si no hay hoja, usar valores por defecto
                self.available_work_areas = ["Area_1", "Area_2", "Area_3"]
                print("[VENTANA_CONFIG] WorkAreas por defecto cargadas")

            wb.close()

        except Exception as e:
            print(f"[VENTANA_CONFIG ERROR] Error cargando WorkAreas: {e}")
            # Usar valores por defecto en caso de error
            self.available_work_areas = ["Area_1", "Area_2", "Area_3"]

    def _poblar_ui_flota(self, grupos):
        """Pobla la UI de flota con grupos existentes desde config cargado"""
        # Limpiar grupos actuales
        for agent_type in ['GroundOperator', 'Forklift']:
            for group in list(self.fleet_groups[agent_type]):
                group['frame'].destroy()
            self.fleet_groups[agent_type].clear()

        # Recrear grupos desde config
        for grupo in grupos:
            agent_type = grupo['agent_type']
            self._anadir_grupo_flota(agent_type)

            # Obtener el grupo recien creado
            group = self.fleet_groups[agent_type][-1]

            # Setear valores
            group['cantidad_var'].set(grupo['cantidad'])
            group['capacidad_var'].set(grupo['capacidad'])
            group['tiempo_var'].set(grupo['tiempo_descarga'])

            # Agregar prioridades
            for wa, priority in grupo['work_area_priorities'].items():
                self._anadir_prioridad_wa(agent_type, len(self.fleet_groups[agent_type])-1,
                                         group['priorities_container'])
                # Setear valores de la prioridad recien creada
                priority_data = group['priorities'][-1]
                priority_data['wa_var'].set(str(wa))
                priority_data['priority_var'].set(priority)

    # ========================================================================
    # METODOS DE VALORES POR DEFECTO
    # ========================================================================

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

        # Estrategias (solo 2)
        self.dispatch_strategy_var.set("Optimizacion Global")
        self.tour_type_var.set("Tour Mixto (Multi-Destino)")

        # Layout
        self.layout_path_var.set("layouts/WH1.tmx")
        self.sequence_path_var.set("layouts/Warehouse_Logic.xlsx")
        self.map_scale_var.set(1.3)
        self.resolution_var.set("Pequena (800x800)")

        # Outbound Staging
        for i in range(1, 8):
            self.outbound_staging_vars[str(i)].set(100 if i == 1 else 0)

        # Asignacion de recursos
        self._generar_asignacion_defecto()

        # Validaciones
        self.validar_porcentajes()
        self.actualizar_total()
        self._validar_staging_distribution()

        print("[CONFIGURATOR] Valores por defecto cargados")

    def obtener_configuracion(self):
        """Obtiene la configuracion actual como diccionario"""
        # Sincronizar assignment_rules desde widgets
        for agent_type, widget_rows in self.assignment_widgets.items():
            self.assignment_rules[agent_type] = {}
            for row in widget_rows:
                level = row['level_var'].get()
                priority = row['priority_var'].get()
                self.assignment_rules[agent_type][level] = priority

        # Construir agent_types desde fleet_groups (nueva estructura)
        agent_types = []

        # Procesar Operarios Terrestres
        for group in self.fleet_groups['GroundOperator']:
            cantidad = group['cantidad_var'].get()
            capacidad = group['capacidad_var'].get()
            tiempo_descarga = group['tiempo_var'].get()

            # Construir diccionario de prioridades de Work Area
            work_area_priorities = {}
            for priority_data in group['priorities']:
                wa = priority_data['wa_var'].get()
                priority = priority_data['priority_var'].get()
                if wa:  # Solo agregar si se selecciono un WA
                    work_area_priorities[int(wa)] = priority

            # Crear agentes individuales
            for _ in range(cantidad):
                agent_types.append({
                    'type': 'GroundOperator',
                    'capacity': capacidad,
                    'discharge_time': tiempo_descarga,
                    'work_area_priorities': work_area_priorities.copy()
                })

        # Procesar Montacargas
        for group in self.fleet_groups['Forklift']:
            cantidad = group['cantidad_var'].get()
            capacidad = group['capacidad_var'].get()
            tiempo_descarga = group['tiempo_var'].get()

            # Construir diccionario de prioridades de Work Area
            work_area_priorities = {}
            for priority_data in group['priorities']:
                wa = priority_data['wa_var'].get()
                priority = priority_data['priority_var'].get()
                if wa:  # Solo agregar si se selecciono un WA
                    work_area_priorities[int(wa)] = priority

            # Crear agentes individuales
            for _ in range(cantidad):
                agent_types.append({
                    'type': 'Forklift',
                    'capacity': capacidad,
                    'discharge_time': tiempo_descarga,
                    'work_area_priorities': work_area_priorities.copy()
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
            'tour_type': self.tour_type_var.get(),
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

    # ========================================================================
    # CALLBACKS (stubs - seran conectados por ConfiguradorSimulador)
    # ========================================================================

    def _guardar_callback(self):
        """Placeholder para guardar"""
        print("[VENTANA] Guardar callback")

    def _probar_callback(self):
        """Placeholder para probar"""
        print("[VENTANA] Probar callback")

    def _salir_callback(self):
        """Placeholder para salir"""
        self.parent.quit()


class ConfiguradorSimulador:
    """Configurador independiente del simulador con funcionalidad de guardado"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Configurador de Simulacion - Gemelo Digital")
        self.root.geometry("700x600")
        self.root.resizable(True, True)

        # Centrar ventana
        self._centrar_ventana()

        # Crear el configurador principal pasando la ventana raiz
        self.ventana_config = VentanaConfiguracion(self.root)

        # CORRECCION: Diferir carga hasta que UI este completamente lista
        self.root.after(100, self._cargar_configuracion_existente)

        print("[CONFIGURATOR] Configurador independiente inicializado")

    def _centrar_ventana(self):
        """Centra la ventana en la pantalla"""
        self.root.update_idletasks()
        ancho_ventana = 700
        alto_ventana = 600
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

            # Estrategias (2 tipos)
            self.ventana_config.dispatch_strategy_var.set(config.get('dispatch_strategy', 'Optimizacion Global'))
            self.ventana_config.tour_type_var.set(config.get('tour_type', 'Tour Mixto (Multi-Destino)'))

            # Layout y archivos
            self.ventana_config.layout_path_var.set(config.get('layout_file', 'layouts/WH1.tmx'))
            self.ventana_config.sequence_path_var.set(config.get('sequence_file', 'layouts/Warehouse_Logic.xlsx'))
            self.ventana_config.map_scale_var.set(config.get('map_scale', 1.3))
            self.ventana_config.resolution_var.set(config.get('selected_resolution_key', 'Pequena (800x800)'))

            # Asignacion de recursos
            assignment_rules = config.get('assignment_rules', {
                "GroundOperator": {1: 1},
                "Forklift": {1: 2, 2: 1, 3: 1, 4: 1, 5: 1}
            })
            self.ventana_config.assignment_rules = assignment_rules
            self.ventana_config._update_assignment_display()

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

            # Inicializacion inteligente
            self._inicializacion_inteligente(config)

        except Exception as e:
            print(f"[CONFIGURATOR ERROR] Error poblando UI desde config: {e}")
            import traceback
            traceback.print_exc()

    def _inicializacion_inteligente(self, config):
        """Inicializacion inteligente: Carga WorkAreas automaticamente"""
        try:
            print("[CONFIGURATOR] Iniciando inicializacion inteligente...")

            # PASO 1: Cargar WorkAreas automaticamente
            sequence_file = self.ventana_config.sequence_path_var.get()
            if sequence_file and os.path.exists(sequence_file):
                try:
                    print(f"[CONFIGURATOR] Cargando WorkAreas desde: {sequence_file}")
                    self.ventana_config._cargar_work_areas_automatico(sequence_file)
                    print(f"[CONFIGURATOR] WorkAreas cargadas: {self.ventana_config.available_work_areas}")
                except Exception as e:
                    print(f"[CONFIGURATOR] ADVERTENCIA - Error cargando WorkAreas: {e}")

            # PASO 2: Generar flota por defecto si no existe
            agent_types = config.get('agent_types', [])
            if not agent_types and self.ventana_config.available_work_areas:
                print("[CONFIGURATOR] Generando flota por defecto silenciosa...")
                try:
                    config_defecto = self.ventana_config._generar_config_defecto()
                    self.ventana_config._limpiar_todos_los_grupos()
                    for group_config in config_defecto:
                        self.ventana_config._crear_grupo_desde_config(group_config)
                    print("[CONFIGURATOR] Flota por defecto generada")
                except Exception as e:
                    print(f"[CONFIGURATOR] Error generando flota: {e}")

        except Exception as e:
            print(f"[CONFIGURATOR ERROR] Error en inicializacion inteligente: {e}")

    def _agrupar_agentes_para_ui(self, agent_types_list):
        """Agrupa agent_types del JSON en formato para _poblar_ui_flota"""
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
                f"Ahora puedes ejecutar 'python run_simulator.py' directamente."
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
            # Validaciones basicas
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

        # Convertir rutas a relativas
        config['layout_file'] = self._make_relative_path(config['layout_file'])
        config['sequence_file'] = self._make_relative_path(config['sequence_file'])

        return config

    def _make_relative_path(self, file_path: str) -> str:
        """Convierte rutas absolutas a relativas"""
        if not file_path:
            return file_path

        try:
            project_root = os.path.dirname(os.path.abspath(__file__))
            abs_path = os.path.abspath(file_path)

            if abs_path.startswith(project_root):
                relative_path = os.path.relpath(abs_path, project_root)
                return relative_path.replace('\\', '/')
            else:
                return abs_path.replace('\\', '/')

        except (ValueError, OSError):
            return file_path

    def ejecutar(self):
        """Ejecuta el configurador"""
        print("[CONFIGURATOR] Iniciando configurador independiente...")
        print("[CONFIGURATOR] Use 'Guardar Configuracion' para crear config.json")

        # Conectar callbacks
        self.ventana_config._guardar_callback = self.guardar_configuracion
        self.ventana_config._salir_callback = self.salir

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
