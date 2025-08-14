#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VENTANA DE CONFIGURACIÓN MEJORADA - Con selector de layouts dinámicos
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os

# Importar dependencias
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

from config.settings import *
from dynamic_layout_loader import DynamicLayoutLoader

class EnhancedConfigWindow:
    """Ventana de configuración con selector de layouts dinámicos"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Configuración de Simulación - Layouts Dinámicos")
        
        # Configurar ventana
        self.root.geometry("700x800")
        self.root.resizable(True, True)
        self.root.minsize(650, 750)
        
        # Centrar ventana
        self._center_window()
        
        # Variables de configuración
        self._init_variables()
        
        # Inicializar loader de layouts
        self.layout_loader = DynamicLayoutLoader()
        
        # Variables para layouts
        self.selected_layout_path = tk.StringVar()
        self.available_layouts = []
        
        self.resultado = None
        
        # Crear interfaz
        self._create_interface()
        
        # Cargar layouts disponibles
        self._load_available_layouts()
    
    def _center_window(self):
        """Centrar ventana en pantalla"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.root.winfo_screenheight() // 2) - (800 // 2)
        self.root.geometry(f"+{x}+{y}")
    
    def _init_variables(self):
        """Inicializar variables de configuración"""
        # Variables originales del simulador
        self.total_tareas_picking = tk.IntVar(value=300)
        self.pct_pequeno = tk.IntVar(value=60)
        self.pct_mediano = tk.IntVar(value=30)
        self.pct_grande = tk.IntVar(value=10)
        self.vol_pequeno = tk.IntVar(value=5)
        self.vol_mediano = tk.IntVar(value=25)
        self.vol_grande = tk.IntVar(value=80)
        self.capacidad_carro = tk.IntVar(value=150)
        self.num_operarios_terrestres = tk.IntVar(value=4)
        self.num_montacargas = tk.IntVar(value=2)
        
        # Variables para layouts dinámicos
        self.use_dynamic_layout = tk.BooleanVar(value=True)
        self.layout_info_text = tk.StringVar(value="Selecciona un layout...")
    
    def _create_interface(self):
        """Crear interfaz completa"""
        
        # Frame principal con scroll
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Título
        title = tk.Label(main_frame, 
                        text="CONFIGURACIÓN DE SIMULACIÓN",
                        font=("Arial", 18, "bold"), 
                        fg="navy")
        title.pack(pady=(0, 20))
        
        # Notebook para organizar en tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Layout del Almacén
        self._create_layout_tab()
        
        # Tab 2: Configuración de Simulación
        self._create_simulation_tab()
        
        # Tab 3: Operarios y Recursos
        self._create_resources_tab()
        
        # Botones principales
        self._create_main_buttons(main_frame)
    
    def _create_layout_tab(self):
        """Crear tab de selección de layout"""
        
        layout_frame = ttk.Frame(self.notebook)
        self.notebook.add(layout_frame, text="📐 Layout del Almacén")
        
        # Frame principal
        main_layout_frame = ttk.LabelFrame(layout_frame, text="Seleccionar Layout de Almacén", padding="15")
        main_layout_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Opción: usar layout dinámico
        dynamic_check = ttk.Checkbutton(main_layout_frame, 
                                       text="Usar layout personalizado (TMX)",
                                       variable=self.use_dynamic_layout,
                                       command=self._toggle_dynamic_layout)
        dynamic_check.pack(anchor=tk.W, pady=(0, 15))
        
        # Frame para selector de layout
        self.layout_selector_frame = ttk.Frame(main_layout_frame)
        self.layout_selector_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Label y dropdown
        layout_label = ttk.Label(self.layout_selector_frame, text="Layout disponible:")
        layout_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Frame para dropdown y botones
        dropdown_frame = ttk.Frame(self.layout_selector_frame)
        dropdown_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.layout_dropdown = ttk.Combobox(dropdown_frame, 
                                          textvariable=self.selected_layout_path,
                                          state="readonly",
                                          width=50)
        self.layout_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.layout_dropdown.bind("<<ComboboxSelected>>", self._on_layout_selected)
        
        # Botones de gestión
        buttons_frame = ttk.Frame(dropdown_frame)
        buttons_frame.pack(side=tk.RIGHT)
        
        refresh_btn = ttk.Button(buttons_frame, text="🔄", width=3,
                               command=self._refresh_layouts)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        browse_btn = ttk.Button(buttons_frame, text="📁", width=3,
                              command=self._browse_layout_file)
        browse_btn.pack(side=tk.LEFT)
        
        # Información del layout seleccionado
        info_frame = ttk.LabelFrame(main_layout_frame, text="Información del Layout", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.layout_info_display = tk.Text(info_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar_info = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.layout_info_display.yview)
        self.layout_info_display.configure(yscrollcommand=scrollbar_info.set)
        
        self.layout_info_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_info.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enlaces útiles
        links_frame = ttk.LabelFrame(main_layout_frame, text="Enlaces Útiles", padding="10")
        links_frame.pack(fill=tk.X, pady=(10, 0))
        
        link1 = tk.Label(links_frame, text="📖 Documentación de Tiles", 
                        fg="blue", cursor="hand2")
        link1.pack(anchor=tk.W)
        link1.bind("<Button-1>", self._open_tiles_documentation)
        
        link2 = tk.Label(links_frame, text="🔧 Crear Nuevo Layout en Tiled", 
                        fg="blue", cursor="hand2")
        link2.pack(anchor=tk.W)
        link2.bind("<Button-1>", self._open_tiled_tutorial)
    
    def _create_simulation_tab(self):
        """Crear tab de configuración de simulación"""
        
        sim_frame = ttk.Frame(self.notebook)
        self.notebook.add(sim_frame, text="⚙️ Simulación")
        
        # Frame para tareas
        tareas_frame = ttk.LabelFrame(sim_frame, text="Configuración de Tours de Picking", padding="15")
        tareas_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Total de tareas
        ttk.Label(tareas_frame, text="Total de tareas de picking:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Spinbox(tareas_frame, from_=50, to=1000, textvariable=self.total_tareas_picking, width=10).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Distribución de tipos
        ttk.Label(tareas_frame, text="Distribución de tipos:").grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        
        types_frame = ttk.Frame(tareas_frame)
        types_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        ttk.Label(types_frame, text="Pequeño (%):").grid(row=0, column=0, sticky=tk.W)
        ttk.Spinbox(types_frame, from_=0, to=100, textvariable=self.pct_pequeno, width=8).grid(row=0, column=1, padx=5)
        
        ttk.Label(types_frame, text="Mediano (%):").grid(row=0, column=2, sticky=tk.W, padx=(15, 0))
        ttk.Spinbox(types_frame, from_=0, to=100, textvariable=self.pct_mediano, width=8).grid(row=0, column=3, padx=5)
        
        ttk.Label(types_frame, text="Grande (%):").grid(row=0, column=4, sticky=tk.W, padx=(15, 0))
        ttk.Spinbox(types_frame, from_=0, to=100, textvariable=self.pct_grande, width=8).grid(row=0, column=5, padx=5)
        
        # Volúmenes
        vol_frame = ttk.Frame(tareas_frame)
        vol_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        ttk.Label(vol_frame, text="Volumen pequeño:").grid(row=0, column=0, sticky=tk.W)
        ttk.Spinbox(vol_frame, from_=1, to=50, textvariable=self.vol_pequeno, width=8).grid(row=0, column=1, padx=5)
        
        ttk.Label(vol_frame, text="Volumen mediano:").grid(row=0, column=2, sticky=tk.W, padx=(15, 0))
        ttk.Spinbox(vol_frame, from_=10, to=100, textvariable=self.vol_mediano, width=8).grid(row=0, column=3, padx=5)
        
        ttk.Label(vol_frame, text="Volumen grande:").grid(row=0, column=4, sticky=tk.W, padx=(15, 0))
        ttk.Spinbox(vol_frame, from_=50, to=200, textvariable=self.vol_grande, width=8).grid(row=0, column=5, padx=5)
    
    def _create_resources_tab(self):
        """Crear tab de recursos y operarios"""
        
        resources_frame = ttk.Frame(self.notebook)
        self.notebook.add(resources_frame, text="👥 Recursos")
        
        # Frame operarios
        operarios_frame = ttk.LabelFrame(resources_frame, text="Operarios y Equipamiento", padding="15")
        operarios_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Operarios terrestres
        ttk.Label(operarios_frame, text="Operarios terrestres:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Spinbox(operarios_frame, from_=1, to=20, textvariable=self.num_operarios_terrestres, width=10).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Montacargas
        ttk.Label(operarios_frame, text="Montacargas:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Spinbox(operarios_frame, from_=1, to=10, textvariable=self.num_montacargas, width=10).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # Capacidad carro
        ttk.Label(operarios_frame, text="Capacidad carro (litros):").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Spinbox(operarios_frame, from_=50, to=500, textvariable=self.capacidad_carro, width=10).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
    
    def _create_main_buttons(self, parent):
        """Crear botones principales"""
        
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        # Botón Cancelar
        cancel_btn = ttk.Button(buttons_frame, text="Cancelar", 
                              command=self._cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Botón Iniciar Simulación
        start_btn = ttk.Button(buttons_frame, text="Iniciar Simulación",
                             command=self._start_simulation)
        start_btn.pack(side=tk.RIGHT)
        
        # Botón Vista previa
        preview_btn = ttk.Button(buttons_frame, text="Vista Previa Layout",
                               command=self._preview_layout)
        preview_btn.pack(side=tk.LEFT)
    
    def _load_available_layouts(self):
        """Cargar layouts disponibles"""
        
        try:
            # ARREGLO: Inicializar pygame.display antes de cargar TMX
            import pygame
            if not pygame.get_init():
                pygame.init()
            
            # Verificar si ya hay un display activo
            try:
                pygame.display.get_surface()
            except:
                # Crear display temporal para cargar TMX
                pygame.display.set_mode((100, 100))
                print("   pygame.display inicializado para carga TMX")
                
            self.available_layouts = self.layout_loader.get_layouts_list_for_ui()
            
            # Actualizar dropdown
            layout_names = [layout['display_name'] for layout in self.available_layouts]
            self.layout_dropdown['values'] = layout_names
            
            if layout_names:
                self.layout_dropdown.set(layout_names[0])
                self._on_layout_selected(None)
            else:
                self.layout_info_text.set("No se encontraron layouts disponibles")
                self._update_layout_info("No hay layouts disponibles en la carpeta 'layouts'.\n\n"
                                       "Para comenzar:\n"
                                       "1. Crea layouts usando Tiled\n"
                                       "2. Guárdalos en la carpeta 'layouts'\n"
                                       "3. Haz clic en el botón de actualizar")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando layouts: {e}")
    
    def _on_layout_selected(self, event):
        """Manejar selección de layout"""
        
        selected_display = self.layout_dropdown.get()
        
        # Buscar layout correspondiente
        selected_layout = None
        for layout in self.available_layouts:
            if layout['display_name'] == selected_display:
                selected_layout = layout
                break
        
        if selected_layout:
            self.selected_layout_path.set(selected_layout['path'])
            
            # Actualizar información
            info_text = f"Layout: {selected_layout['filename']}\\n"
            info_text += f"Descripción: {selected_layout['description']}\\n"
            info_text += f"Válido: {'Sí' if selected_layout['valid'] else 'No'}\\n"
            
            if not selected_layout['valid'] and 'error' in selected_layout:
                info_text += f"Error: {selected_layout['error']}\\n"
            
            info_text += f"Ruta: {selected_layout['path']}"
            
            self._update_layout_info(info_text)
    
    def _update_layout_info(self, text):
        """Actualizar display de información del layout"""
        
        self.layout_info_display.config(state=tk.NORMAL)
        self.layout_info_display.delete(1.0, tk.END)
        self.layout_info_display.insert(1.0, text)
        self.layout_info_display.config(state=tk.DISABLED)
    
    def _refresh_layouts(self):
        """Refrescar lista de layouts"""
        
        self._load_available_layouts()
        messagebox.showinfo("Actualizado", "Lista de layouts actualizada")
    
    def _browse_layout_file(self):
        """Abrir explorador para seleccionar archivo TMX"""
        
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo TMX",
            filetypes=[("Archivos TMX", "*.tmx"), ("Todos los archivos", "*.*")],
            initialdir="layouts"
        )
        
        if file_path:
            # Copiar archivo a carpeta layouts si no está ahí
            if not file_path.startswith(os.path.abspath("layouts")):
                import shutil
                filename = os.path.basename(file_path)
                dest_path = os.path.join("layouts", filename)
                
                try:
                    shutil.copy2(file_path, dest_path)
                    messagebox.showinfo("Copiado", f"Layout copiado a: {dest_path}")
                    self._refresh_layouts()
                except Exception as e:
                    messagebox.showerror("Error", f"Error copiando archivo: {e}")
            else:
                self._refresh_layouts()
    
    def _toggle_dynamic_layout(self):
        """Activar/desactivar selector de layout dinámico"""
        
        if self.use_dynamic_layout.get():
            self.layout_selector_frame.pack(fill=tk.X, pady=(0, 15))
        else:
            self.layout_selector_frame.pack_forget()
    
    def _preview_layout(self):
        """Mostrar vista previa del layout seleccionado"""
        
        if not self.use_dynamic_layout.get():
            messagebox.showinfo("Vista Previa", "Vista previa disponible solo para layouts dinámicos")
            return
        
        layout_path = self.selected_layout_path.get()
        if not layout_path:
            messagebox.showwarning("Advertencia", "Selecciona un layout primero")
            return
        
        # Aquí se podría integrar una vista previa visual
        messagebox.showinfo("Vista Previa", f"Vista previa de layout:\\n{layout_path}\\n\\n(Funcionalidad de vista previa en desarrollo)")
    
    def _open_tiles_documentation(self, event):
        """Abrir documentación de tiles"""
        
        docs_path = "docs/TILES_REFERENCE.md"
        if os.path.exists(docs_path):
            try:
                os.startfile(docs_path)  # Windows
            except:
                messagebox.showinfo("Documentación", f"Documentación disponible en: {docs_path}")
        else:
            messagebox.showinfo("Documentación", "Documentación no encontrada")
    
    def _open_tiled_tutorial(self, event):
        """Abrir tutorial de Tiled"""
        
        tutorial_text = """Tutorial Rápido - Crear Layout en Tiled:

1. Descarga e instala Tiled (https://www.mapeditor.org/)
2. Abre Tiled y crea un nuevo mapa
3. Importa el tileset: tilesets/warehouse_tileset.tsx
4. Pinta tu layout usando los tiles
5. Agrega objetos para puntos especiales (picking, depot)
6. Guarda como archivo TMX en la carpeta 'layouts'
7. Refresca la lista en el simulador

¡Tu layout personalizado estará listo para usar!"""
        
        messagebox.showinfo("Tutorial Tiled", tutorial_text)
    
    def _start_simulation(self):
        """Iniciar simulación con configuración actual"""
        
        # Validar configuración
        if self.use_dynamic_layout.get() and not self.selected_layout_path.get():
            messagebox.showwarning("Advertencia", "Selecciona un layout para continuar")
            return
        
        # Recopilar configuración
        # Crear configuración en formato esperado por AlmacenMejorado
        config = {
            'use_dynamic_layout': self.use_dynamic_layout.get(),
            'selected_layout_path': self.selected_layout_path.get(),
            'total_tareas_picking': self.total_tareas_picking.get(),  # Nombre correcto para AlmacenMejorado
            'distribucion_tipos': {
                'pequeno': {
                    'porcentaje': self.pct_pequeno.get(),
                    'volumen': self.vol_pequeno.get()
                },
                'mediano': {
                    'porcentaje': self.pct_mediano.get(),
                    'volumen': self.vol_mediano.get()
                },
                'grande': {
                    'porcentaje': self.pct_grande.get(),
                    'volumen': self.vol_grande.get()
                }
            },
            'capacidad_carro': self.capacidad_carro.get(),
            'num_operarios_terrestres': self.num_operarios_terrestres.get(),
            'num_montacargas': self.num_montacargas.get()
        }
        
        self.resultado = config
        self.root.quit()
    
    def _cancel(self):
        """Cancelar configuración"""
        
        self.resultado = None
        self.root.quit()
    
    def mostrar(self):
        """Mostrar ventana y retornar configuración"""
        
        self.root.mainloop()
        self.root.destroy()
        return self.resultado

def main():
    """Testing de la ventana de configuración mejorada"""
    
    print("Testing Enhanced Config Window...")
    
    window = EnhancedConfigWindow()
    result = window.mostrar()
    
    if result:
        print("Configuración seleccionada:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print("Configuración cancelada")
    
    return result

if __name__ == "__main__":
    main()