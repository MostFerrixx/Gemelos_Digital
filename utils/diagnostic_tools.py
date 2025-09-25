"""
Herramientas de diagnostico para el Sistema de Simulacion V10.0.1+
Extraido de SimulationEngine para reducir acoplamiento.

Este modulo contiene funciones de diagnostico independientes que pueden
ser reutilizadas sin depender directamente de la clase SimulationEngine.
"""


def diagnosticar_route_calculator(almacen):
    """Metodo de diagnostico para el RouteCalculator V2.6"""
    print("\n--- DIAGNOSTICO DEL CALCULADOR DE RUTAS V2.6 ---")
    if not almacen or not almacen.dispatcher:
        print("El almacen o el dispatcher no estan listos.")
        return

    # Tomar la posicion inicial del primer depot como punto de partida
    start_pos = almacen.data_manager.outbound_staging_locations[1]
    print(f"Punto de partida para el diagnostico: Depot en {start_pos}")

    # V2.6: Analizar tareas de la lista maestra en lugar de lineas pendientes
    if hasattr(almacen.dispatcher, 'lista_maestra_work_orders') and almacen.dispatcher.lista_maestra_work_orders:
        total_work_orders = len(almacen.dispatcher.lista_maestra_work_orders)
        sample_size = min(10, total_work_orders)
        print(f"Analizando {sample_size} WorkOrders de {total_work_orders} en la lista maestra...")

        for i in range(sample_size):
            work_order = almacen.dispatcher.lista_maestra_work_orders[i]
            print(f"  WorkOrder {i+1}: Seq {work_order.pick_sequence}, SKU {work_order.sku.id}, Pos {work_order.ubicacion}")
    else:
        print("No hay tareas en la lista maestra para diagnosticar")

    print("V2.6: RouteCalculator integrado con DataManager y AssignmentCostCalculator")
    print("-------------------------------------------\n")


# Funciones de conveniencia para futuros diagnosticos
def ejecutar_diagnosticos_completos(almacen, configuracion=None):
    """Ejecuta todos los diagnosticos disponibles"""
    diagnosticar_route_calculator(almacen)
    # Espacio para futuros diagnosticos adicionales


def diagnosticar_componente_personalizado(componente, nombre_componente="Componente"):
    """Template para diagnosticos de componentes personalizados"""
    print(f"\n--- DIAGNOSTICO DE {nombre_componente.upper()} ---")
    if not componente:
        print(f"El {nombre_componente} no esta disponible.")
        return

    print(f"  [EXITO] {nombre_componente} detectado correctamente.")
    print(f"------------------------------------\n")