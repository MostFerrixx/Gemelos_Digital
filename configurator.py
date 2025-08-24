# -*- coding: utf-8 -*-
"""
Configurador del Simulador de Almacén - Separación de configuración y ejecución.
Interfaz gráfica independiente para configurar parámetros de simulación.
"""

import sys
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Añadir path al git submodule
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))

from config.window_config import VentanaConfiguracion

class ConfiguradorSimulador:
    """Configurador independiente del simulador con funcionalidad de guardado"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Configurador de Simulación - Gemelo Digital")
        self.root.geometry("650x550")
        self.root.resizable(True, True)
        
        # Centrar ventana
        self._centrar_ventana()
        
        # Crear el configurador principal pasando la ventana raíz
        self.ventana_config = VentanaConfiguracion(self.root)
        
        # Reemplazar los botones originales con los nuevos
        self._modificar_botones()
        
        # Intentar cargar configuración existente al inicio
        self._cargar_configuracion_existente()
        
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
        """Carga configuración existente de config.json al iniciar"""
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        
        if os.path.exists(config_path):
            try:
                print(f"[CONFIGURATOR] Cargando configuración desde: {config_path}")
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Sanitizar assignment_rules: convertir claves str a int
                if 'assignment_rules' in config and config['assignment_rules']:
                    sanitized_rules = {}
                    for agent_type, rules in config['assignment_rules'].items():
                        sanitized_rules[agent_type] = {int(k): v for k, v in rules.items()}
                    config['assignment_rules'] = sanitized_rules
                    print("[CONFIGURATOR] assignment_rules sanitizadas: claves str → int")
                
                self._poblar_ui_desde_config(config)
                print("[CONFIGURATOR] Configuración cargada exitosamente en UI")
                
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
            
            # Estrategias
            self.ventana_config.strategy_var.set(config.get('strategy', 'Zoning and Snake'))
            self.ventana_config.batching_strategy_var.set(config.get('batching_strategy', 'Orden por Orden (Línea Base)'))
            self.ventana_config.dispatch_strategy_var.set(config.get('dispatch_strategy', 'Ejecución de Plan (Filtro por Prioridad)'))
            
            # Layout y archivos
            self.ventana_config.layout_path_var.set(config.get('layout_file', 'layouts/WH1.tmx'))
            self.ventana_config.sequence_path_var.set(config.get('sequence_file', 'layouts/Warehouse_Logic.xlsx'))
            
            # Resolución
            self.ventana_config.resolution_var.set(config.get('selected_resolution_key', 'Pequeña (800x800)'))
            
            # Asignación de recursos
            assignment_rules = config.get('assignment_rules', {
                "GroundOperator": {1: 1},
                "Forklift": {1: 2, 2: 1, 3: 1, 4: 1, 5: 1}
            })
            self.ventana_config.assignment_rules = assignment_rules
            self.ventana_config._update_assignment_display()
            
            # Actualizar validaciones y resúmenes
            self.ventana_config.validar_porcentajes()
            self.ventana_config.actualizar_total()
            
        except Exception as e:
            print(f"[CONFIGURATOR ERROR] Error poblando UI desde config: {e}")
            raise
    
    def _modificar_botones(self):
        """Modifica los botones del configurador para añadir funcionalidad de guardado"""
        # Limpiar frame de botones existente
        for widget in self.ventana_config.bottom_frame.winfo_children():
            if isinstance(widget, ttk.Frame):
                for btn_widget in widget.winfo_children():
                    if isinstance(btn_widget, ttk.Button):
                        btn_widget.destroy()
        
        # Crear nuevo frame de botones
        frame_botones = ttk.Frame(self.ventana_config.bottom_frame)
        frame_botones.pack(pady=10)
        
        # Botón guardar configuración
        btn_guardar = ttk.Button(frame_botones, text="Guardar Configuración", 
                                command=self.guardar_configuracion, width=20)
        btn_guardar.pack(side=tk.LEFT, padx=5)
        
        # Botón cargar defaults
        btn_defaults = ttk.Button(frame_botones, text="Cargar Defaults", 
                                 command=self.cargar_defaults, width=15)
        btn_defaults.pack(side=tk.LEFT, padx=5)
        
        # Botón probar configuración (lanza simulador)
        btn_probar = ttk.Button(frame_botones, text="Probar Configuración", 
                               command=self.probar_configuracion, width=18)
        btn_probar.pack(side=tk.LEFT, padx=5)
        
        # Botón salir
        btn_salir = ttk.Button(frame_botones, text="Salir", 
                              command=self.salir, width=10)
        btn_salir.pack(side=tk.LEFT, padx=5)
    
    def guardar_configuracion(self):
        """Guarda la configuración actual en config.json"""
        try:
            # Validar configuración antes de guardar
            if not self._validar_configuracion_actual():
                return
            
            # Obtener configuración de la UI
            config = self._obtener_configuracion_ui()
            
            # Guardar en archivo JSON
            config_path = os.path.join(os.path.dirname(__file__), "config.json")
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            messagebox.showinfo(
                "Configuración Guardada", 
                f"La configuración se ha guardado exitosamente en:\n{config_path}\n\n"
                f"Ahora puedes ejecutar 'python run_simulator.py' directamente "
                f"para usar esta configuración automáticamente."
            )
            print(f"[CONFIGURATOR] Configuración guardada en: {config_path}")
            
        except Exception as e:
            messagebox.showerror(
                "Error al Guardar", 
                f"No se pudo guardar la configuración:\n{str(e)}"
            )
            print(f"[CONFIGURATOR ERROR] Error guardando configuración: {e}")
    
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
        """Guarda la configuración y lanza el simulador para probarla"""
        try:
            # Primero guardar la configuración
            self.guardar_configuracion()
            
            # Confirmar si quiere lanzar el simulador
            if messagebox.askyesno(
                "Probar Configuración", 
                "Configuración guardada. ¿Deseas lanzar el simulador ahora para probarla?"
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
            print(f"[CONFIGURATOR ERROR] Error probando configuración: {e}")
    
    def salir(self):
        """Cierra el configurador"""
        if messagebox.askyesno(
            "Confirmar Salida", 
            "¿Estás seguro de que deseas salir del configurador?"
        ):
            print("[CONFIGURATOR] Cerrando configurador")
            self.root.destroy()
    
    def _validar_configuracion_actual(self) -> bool:
        """Valida la configuración actual de la UI"""
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
            
            return self.ventana_config._validar_configuracion_picking(
                total_ordenes, pct_pequeno, pct_mediano, pct_grande,
                vol_pequeno, vol_mediano, vol_grande, capacidad_carro,
                op_terrestres, montacargas, op_terrestres + montacargas
            )
        except Exception as e:
            messagebox.showerror("Error de Validación", f"Error validando configuración: {str(e)}")
            return False
    
    def _obtener_configuracion_ui(self) -> dict:
        """Obtiene la configuración actual de la UI como diccionario"""
        # Sincronizar reglas de asignación desde widgets
        temp_rules = {"GroundOperator": {}, "Forklift": {}}
        for agent_type, widget_rows in self.ventana_config.assignment_widgets.items():
            for row in widget_rows:
                level = row['level_var'].get()
                priority = row['priority_var'].get()
                temp_rules[agent_type][level] = priority
        self.ventana_config.assignment_rules = temp_rules
        
        # Construir diccionario de configuración completo
        config = {
            # Configuración de tareas de picking
            'total_ordenes': self.ventana_config.total_ordenes_var.get(),
            'distribucion_tipos': {
                'pequeno': {
                    'porcentaje': self.ventana_config.pct_pequeno.get(), 
                    'volumen': self.ventana_config.vol_pequeno.get()
                },
                'mediano': {
                    'porcentaje': self.ventana_config.pct_mediano.get(), 
                    'volumen': self.ventana_config.vol_mediano.get()
                },
                'grande': {
                    'porcentaje': self.ventana_config.pct_grande.get(), 
                    'volumen': self.ventana_config.vol_grande.get()
                }
            },
            'capacidad_carro': self.ventana_config.capacidad_carro.get(),
            
            # Configuración de estrategias
            'strategy': self.ventana_config.strategy_var.get(),
            'batching_strategy': self.ventana_config.batching_strategy_var.get(),
            'dispatch_strategy': self.ventana_config.dispatch_strategy_var.get(),
            
            # Configuración de layout (convertir a rutas relativas)
            'layout_file': self._make_relative_path(self.ventana_config.layout_path_var.get()),
            'sequence_file': self._make_relative_path(self.ventana_config.sequence_path_var.get()),
            
            # Configuración de ventana
            'selected_resolution_key': self.ventana_config.resolution_var.get(),
            
            # Configuración de operarios
            'num_operarios_terrestres': self.ventana_config.num_operarios_terrestres.get(),
            'num_montacargas': self.ventana_config.num_montacargas.get(),
            'num_operarios_total': self.ventana_config.num_operarios_terrestres.get() + self.ventana_config.num_montacargas.get(),
            'capacidad_montacargas': self.ventana_config.capacidad_montacargas.get(),
            
            # Configuración de asignación de recursos
            'assignment_rules': self.ventana_config.assignment_rules.copy(),
            
            # Compatibilidad con código existente
            'tareas_zona_a': 0,
            'tareas_zona_b': 0,
            'num_operarios': self.ventana_config.num_operarios_terrestres.get() + self.ventana_config.num_montacargas.get()
        }
        
        return config
    
    def _make_relative_path(self, file_path: str) -> str:
        """Convierte rutas absolutas a relativas respecto al directorio del proyecto"""
        if not file_path:
            return file_path
        
        try:
            project_root = os.path.dirname(os.path.abspath(__file__))
            abs_path = os.path.abspath(file_path)
            
            # Si el archivo está dentro del proyecto, convertir a relativa
            if abs_path.startswith(project_root):
                relative_path = os.path.relpath(abs_path, project_root)
                return relative_path.replace('\\', '/')  # Normalizar separadores para config.json
            else:
                # Si está fuera del proyecto, mantener ruta absoluta
                return abs_path.replace('\\', '/')
                
        except (ValueError, OSError):
            # En caso de error, devolver la ruta original
            return file_path
    
    def ejecutar(self):
        """Ejecuta el configurador"""
        print("[CONFIGURATOR] Iniciando configurador independiente...")
        print("[CONFIGURATOR] Use 'Guardar Configuración' para crear config.json")
        print("[CONFIGURATOR] Luego ejecute 'python run_simulator.py' para usar la configuración")
        self.root.mainloop()


def main():
    """Función principal del configurador"""
    print("="*60)
    print("CONFIGURADOR DE SIMULACION - GEMELO DIGITAL")
    print("Herramienta independiente de configuración")
    print("="*60)
    print()
    
    configurador = ConfiguradorSimulador()
    configurador.ejecutar()


if __name__ == "__main__":
    main()