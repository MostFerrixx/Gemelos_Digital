# -*- coding: utf-8 -*-
"""
Punto de entrada principal del Digital Twin Warehouse Simulator.
Extraido de run_simulator.py para separar punto de entrada de libreria.
"""

import argparse
import os
import json
import time
import multiprocessing
import pygame

# Import de la clase principal del simulador
from run_simulator import SimuladorAlmacen


def ejecutar_modo_replay(jsonl_file_path):
    """
    Ejecuta el modo replay cargando y visualizando eventos desde un archivo .jsonl
    """
    import multiprocessing
    print(f"[REPLAY] Cargando archivo: {jsonl_file_path}")

    # Cargar todos los eventos del archivo .jsonl en memoria
    eventos = []
    simulation_start_event = None
    initial_work_orders = []
    total_work_orders_fijo = None

    try:
        with open(jsonl_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        event = json.loads(line)


                        if event.get('event_type') == 'SIMULATION_START':
                            simulation_start_event = event
                            initial_work_orders = event.get('initial_work_orders', [])
                            # BUGFIX: Leer total fijo de WorkOrders del evento SIMULATION_START
                            total_work_orders_fijo = event.get('total_work_orders', None)
                            if total_work_orders_fijo is not None:
                                print(f"[REPLAY] Encontrado total_work_orders fijo: {total_work_orders_fijo}")
                            else:
                                print(f"[REPLAY] WARNING: total_work_orders no encontrado en SIMULATION_START (replay antiguo)")
                            print(f"[REPLAY] Encontrado SIMULATION_START con {len(initial_work_orders)} WorkOrders iniciales")


                        else:
                            # BUGFIX: Incluir TODOS los eventos incluyendo SIMULATION_END
                            eventos.append(event)
                            if event.get('event_type') == 'SIMULATION_END':
                                print(f"[BUGFIX] SIMULATION_END incluido en eventos: {event}")

                    except json.JSONDecodeError as e:
                        print(f"[REPLAY] Error parseando linea: {e}")
                        continue

        print(f"[REPLAY] {len(eventos)} eventos cargados exitosamente")

    except Exception as e:
        print(f"[REPLAY ERROR] No se pudo cargar archivo de replay: {e}")
        return 1

    # Inicializar pygame
    pygame.init()

    # Crear ventana con espacio para dashboard
    warehouse_width = 960
    dashboard_width = 380
    window_width = warehouse_width + dashboard_width
    window_height = 1000
    window_size = (window_width, window_height)
    pantalla = pygame.display.set_mode(window_size)
    pygame.display.set_caption("Simulador de Almacen - Modo Replay")
    reloj = pygame.time.Clock()

    # REFACTOR V8.0: Inicializar IPC Manager para PyQt6 Dashboard
    from git.visualization.ipc_manager import create_ipc_manager
    ipc_manager = create_ipc_manager()
    dashboard_process_started = False
    print("[IPC-MANAGER] Inicializado para comunicacion con PyQt6 Dashboard")

    # Cargar configuracion desde el evento SIMULATION_START
    configuracion = simulation_start_event.get('config', {}) if simulation_start_event else {}

    # Inicializar arquitectura TMX basica (necesaria para renderizado)
    from simulation.layout_manager import LayoutManager
    from visualization.original_renderer import RendererOriginal
    from visualization.state import inicializar_estado, estado_visual

    # Cargar TMX
    tmx_file = os.path.join(os.path.dirname(__file__), "layouts", "WH1.tmx")
    layout_manager = LayoutManager(tmx_file)

    # Crear superficies
    virtual_surface = pygame.Surface((warehouse_width, warehouse_width))  # Superficie virtual para el mapa
    renderer = RendererOriginal(virtual_surface)

    # Inicializar estado visual basico
    inicializar_estado(None, None, configuracion, layout_manager)

    # FEATURE: Motor de Estado Continuo del Dashboard de Replay
    dashboard_wos_state = {}  # Estado persistente de WorkOrders para el dashboard
    print("[DASHBOARD-STATE] Motor de estado continuo inicializado")

    # Configurar estado inicial con WorkOrders si estan disponibles
    if initial_work_orders:
        for wo in initial_work_orders:
            estado_visual["work_orders"][wo['id']] = wo.copy()
            # FEATURE: Poblar el estado continuo del dashboard
            dashboard_wos_state[wo['id']] = wo.copy()
        print(f"[REPLAY] {len(initial_work_orders)} WorkOrders cargadas en estado inicial")
        print(f"[DASHBOARD-STATE] {len(dashboard_wos_state)} WorkOrders pobladas en estado continuo")

        print("=========================================\n")

    # Procesar primer evento para obtener posiciones iniciales de agentes
    agentes_iniciales = {}
    for evento in eventos[:10]:  # Solo mirar los primeros eventos
        if evento.get('type') == 'estado_agente':
            agent_id = evento.get('agent_id')
            data = evento.get('data', {})
            if agent_id and 'position' in data:
                agentes_iniciales[agent_id] = data

    # Configurar agentes en estado visual
    for agent_id, data in agentes_iniciales.items():
        estado_visual["operarios"][agent_id] = data.copy()

    print(f"[REPLAY] {len(agentes_iniciales)} agentes encontrados en estado inicial")
    print("[REPLAY] Iniciando bucle de visualizacion...")

    # Inicializar motor de playback
    playback_time = 0.0
    replay_speed = 1.0
    velocidades_permitidas = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]
    processed_event_indices = set()  # Trackear eventos ya procesados
    replay_finalizado = False  # BUGFIX: Control de finalizacion del replay

    print(f"[REPLAY] Motor de playback inicializado - {len(eventos)} eventos total")
    print(f"[REPLAY] Estado inicial: replay_finalizado = {replay_finalizado}")

    # REFACTOR V8.0: Control de dashboard PyQt6
    dashboard_visible = False

    def start_pyqt_dashboard():
        """Iniciar dashboard PyQt6 en proceso separado"""
        nonlocal dashboard_process_started
        if not dashboard_process_started:
            success = ipc_manager.start_ui_process()
            if success:
                dashboard_process_started = True
                print("[PYQT6-DASHBOARD] Proceso iniciado exitosamente")

                # Enviar metadata inicial
                metadata = {
                    'type': 'simulation_start',
                    'config': configuracion,
                    'total_work_orders': len(initial_work_orders) if initial_work_orders else 0
                }
                ipc_manager.send_simulation_metadata(metadata)

                # Enviar WorkOrders iniciales
                if initial_work_orders:
                    ipc_manager.send_batch_work_orders(initial_work_orders)
                    print(f"[PYQT6-DASHBOARD] {len(initial_work_orders)} WorkOrders iniciales enviadas")
            else:
                print("[PYQT6-DASHBOARD] Error iniciando proceso")

    # Placeholder para inicio del dashboard PyQt6 (se inicia al presionar 'O')
    print("[PYQT6-DASHBOARD] Dashboard listo para iniciarse (presiona 'O')")

    # Bucle principal de replay con motor temporal
    corriendo = True
    replay_pausado = False  # Control de pausa sincronizada del replay
    while corriendo:
        time_delta = reloj.tick(30) / 1000.0

        # Manejar eventos de pygame
        for event in pygame.event.get():
            # REFACTOR V8.0: Eventos para proceso principal (sin pygame_gui)
            if event.type == pygame.QUIT:
                corriendo = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    corriendo = False
                elif event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS:
                    # Aumentar velocidad al siguiente nivel
                    current_index = velocidades_permitidas.index(replay_speed) if replay_speed in velocidades_permitidas else 2
                    if current_index < len(velocidades_permitidas) - 1:
                        replay_speed = velocidades_permitidas[current_index + 1]
                        print(f"[REPLAY] Velocidad aumentada a {replay_speed:.2f}x")
                elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                    # Disminuir velocidad al nivel anterior
                    current_index = velocidades_permitidas.index(replay_speed) if replay_speed in velocidades_permitidas else 2
                    if current_index > 0:
                        replay_speed = velocidades_permitidas[current_index - 1]
                        print(f"[REPLAY] Velocidad disminuida a {replay_speed:.2f}x")
                elif event.key == pygame.K_SPACE:
                    # Toggle pausa sincronizada del replay
                    replay_pausado = not replay_pausado
                    print(f"[REPLAY] {'Pausado' if replay_pausado else 'Reanudado'}")
                elif event.key == pygame.K_o:
                    # BUGFIX V8.0: Manejador PyQt6 Dashboard con gestion de procesos
                    if ipc_manager.is_ui_process_alive():
                        # Proceso activo - terminarlo
                        print("[PYQT6-DASHBOARD] Cerrando dashboard...")
                        ipc_manager.stop_ui_process()
                        dashboard_process_started = False
                        print("[PYQT6-DASHBOARD] Dashboard cerrado")
                    else:
                        # Proceso inactivo - iniciarlo
                        print("[PYQT6-DASHBOARD] Iniciando dashboard...")
                        success = ipc_manager.start_ui_process()
                        if success:
                            dashboard_process_started = True
                            print("[PYQT6-DASHBOARD] Dashboard iniciado exitosamente")

                            # Enviar metadata inicial de simulacion
                            metadata = {
                                'type': 'simulation_start',
                                'config': configuracion,
                                'total_work_orders': len(initial_work_orders) if initial_work_orders else 0
                            }
                            ipc_manager.send_simulation_metadata(metadata)

                            # Enviar WorkOrders iniciales si existen
                            if initial_work_orders:
                                sent_count = ipc_manager.send_batch_work_orders(initial_work_orders)
                                print(f"[PYQT6-DASHBOARD] {sent_count} WorkOrders iniciales enviadas")
                        else:
                            print("[PYQT6-DASHBOARD] Error iniciando dashboard")
            # REMOVIDO: pygame_gui.UI_BUTTON_PRESSED - No necesario en PyQt6


        # REFACTOR ARQUITECTONICO: Procesar eventos ANTES de avanzar el tiempo
        # Obtener lote de eventos para el tiempo actual (solo si no está pausado)
        eventos_a_procesar = []
        if not replay_pausado:
            for i, evento in enumerate(eventos):
                if i not in processed_event_indices:
                    event_timestamp = evento.get('timestamp', 0.0)
                    # BUGFIX: Manejar timestamps None
                    if event_timestamp is None:
                        event_timestamp = 0.0
                    if event_timestamp <= playback_time:
                        eventos_a_procesar.append((i, evento))

        # Actualizar estado de agentes con eventos procesados
        for event_index, evento in eventos_a_procesar:
            processed_event_indices.add(event_index)

            # BUGFIX: Detectar evento SIMULATION_END y pausar replay
            if evento.get('event_type') == 'SIMULATION_END':
                replay_finalizado = True
                print(f"[BUGFIX] SIMULATION_END detectado en playback_time={playback_time:.3f}s")
                print(f"[BUGFIX] Replay pausado - replay_finalizado = {replay_finalizado}")

            if evento.get('type') == 'estado_agente':
                agent_id = evento.get('agent_id')
                event_data = evento.get('data', {})
                event_timestamp = evento.get('timestamp', 0.0)

                import time
                real_time = time.time()

                if agent_id and event_data:
                    # Inicializar agente si no existe
                    if agent_id not in estado_visual["operarios"]:
                        estado_visual["operarios"][agent_id] = {}

                    # CRITICO: Usar .update() para fusionar datos sin perder claves existentes
                    estado_visual["operarios"][agent_id].update(event_data)

                    # Extraer position si existe
                    if 'position' in event_data:
                        position = event_data['position']

                    # BUGFIX: Extraer WorkOrders anidadas en tour_details
                    tour_details = event_data.get('tour_details', [])
                    if tour_details:
                        # Inicializar diccionario work_orders si no existe
                        if 'work_orders' not in estado_visual:
                            estado_visual['work_orders'] = {}

                        # Extraer cada WorkOrder de la lista tour_details
                        for work_order in tour_details:
                            wo_id = work_order.get('id')
                            if wo_id:
                                estado_visual['work_orders'][wo_id] = work_order.copy()

            elif evento.get('type') == 'work_order_update':
                # Procesar actualizacion de Work Order
                work_order_data = evento.get('data', {})
                work_order_id = work_order_data.get('id')
                event_timestamp = evento.get('timestamp', 0.0)

                import time
                real_time = time.time()
                status = work_order_data.get('status', 'unknown')
                # BUGFIX: Manejar timestamp None
                if event_timestamp is None:
                    event_timestamp = 0.0

                if work_order_id:
                    # Actualizar Work Order en estado visual
                    if 'work_orders' not in estado_visual:
                        estado_visual['work_orders'] = {}
                    estado_visual['work_orders'][work_order_id] = work_order_data.copy()

                    # FEATURE: Actualizar estado continuo del dashboard
                    dashboard_wos_state[work_order_id] = work_order_data.copy()
                    print(f"[DASHBOARD-STATE] WO {work_order_id} actualizada: status={status}")

        # CODIGO ELIMINADO: Sistema de dashboard extirpado por contaminacion Tkinter

        # REFACTOR ARQUITECTONICO: Avanzar tiempo DESPUES de procesar eventos
        # BUGFIX: Solo avanzar tiempo si el replay NO ha finalizado y NO está pausado
        if not replay_finalizado and not replay_pausado:
            delta_time = reloj.get_time() / 1000.0  # Convertir ms a segundos
            playback_time += delta_time * replay_speed


        # Limpiar pantalla
        pantalla.fill((240, 240, 240))
        virtual_surface.fill((25, 25, 25))

        # Renderizar mapa TMX
        if hasattr(layout_manager, 'tmx_data') and layout_manager.tmx_data:
            renderer.renderizar_mapa_tmx(virtual_surface, layout_manager.tmx_data)

        # Renderizar agentes con posiciones actualizadas
        from visualization.original_renderer import renderizar_agentes
        if estado_visual.get("operarios"):
            # CRITICO: Convertir diccionario a lista para renderizar_agentes
            operarios_a_renderizar = []
            for agent_id, agent_data in estado_visual["operarios"].items():
                agente = agent_data.copy()
                agente['id'] = agent_id  # Asegurar que el ID este presente
                operarios_a_renderizar.append(agente)

            renderizar_agentes(virtual_surface, operarios_a_renderizar, layout_manager)

        # Escalar y mostrar superficie virtual del almacen
        scaled_warehouse = pygame.transform.smoothscale(virtual_surface, (warehouse_width, window_height))
        pantalla.blit(scaled_warehouse, (0, 0))

        # Renderizar Dashboard de Agentes
        from visualization.original_renderer import renderizar_dashboard

        # Preparar metricas para el dashboard - DUAL COUNTERS
        # Contar WorkOrders completadas segun contrato de renderizar_dashboard
        work_orders = estado_visual.get('work_orders', {})
        workorders_completadas = sum(1 for wo in work_orders.values() if wo.get('status') == 'staged')

        # Contar tareas completadas procesando los eventos acumulados hasta playback_time
        tareas_completadas = 0
        for evento in eventos:
            # BUGFIX: Validacion defensiva contra timestamp None que causaba TypeError
            timestamp = evento.get('timestamp', 0)
            if timestamp is None:
                timestamp = 0  # Fallback seguro

            if timestamp <= playback_time:
                if evento.get('type') == 'task_completed' or evento.get('type') == 'operation_completed':
                    tareas_completadas += 1

        # BUGFIX: Usar total fijo de WorkOrders si esta disponible
        total_wos_a_usar = total_work_orders_fijo if total_work_orders_fijo is not None else len(work_orders)

        metricas = {
            'tiempo': playback_time,
            'workorders_completadas': workorders_completadas,  # KPI principal
            'tareas_completadas': tareas_completadas,  # Metrica granular
            'total_wos': total_wos_a_usar
        }

        # Preparar operarios para el dashboard (convertir a formato esperado)
        operarios_dashboard = []
        for agent_id, agent_data in estado_visual.get('operarios', {}).items():
            operario = agent_data.copy()
            operario['id'] = agent_id
            operarios_dashboard.append(operario)

        # Renderizar dashboard en el lado derecho
        renderizar_dashboard(pantalla, warehouse_width, metricas, operarios_dashboard)

        # Mostrar informacion de replay en la parte superior del almacen
        font = pygame.font.Font(None, 20)
        info_text = font.render(f"REPLAY: Tiempo {playback_time:.2f}s | Velocidad: {replay_speed:.2f}x | Eventos {len(processed_event_indices)}/{len(eventos)}", True, (255, 255, 255))
        pantalla.blit(info_text, (10, 10))

        # Mostrar informacion de controles y dashboard
        controls_text = font.render("CONTROLES: +/- velocidad | SPACE pausa | O dashboard | ESC salir", True, (255, 255, 255))
        pantalla.blit(controls_text, (10, 35))

        # REFACTOR V8.0: IPC communication con PyQt6 Dashboard
        if dashboard_process_started and ipc_manager and not replay_pausado:
            # Enviar actualizaciones de WorkOrders al dashboard PyQt6
            for wo_id, wo_data in dashboard_wos_state.items():
                ipc_manager.send_work_order_delta(wo_data)

            # Verificar estado del proceso UI
            if not ipc_manager.is_ui_process_alive():
                dashboard_process_started = False
                print("[PYQT6-DASHBOARD] Proceso terminado inesperadamente")
        # REFACTOR V8.0: REMOVIDO - Logica de rendering pygame_gui dashboard
        # PyQt6 dashboard maneja su propia UI independientemente

        pygame.display.flip()

    # REFACTOR V8.0: Cleanup PyQt6 Dashboard
    if ipc_manager:
        print("[CLEANUP] Deteniendo dashboard PyQt6...")
        ipc_manager.cleanup()

    pygame.quit()
    print("[REPLAY] Modo replay terminado")
    return 0


def main():
    """Funcion principal - Modo automatizado con soporte headless"""
    # Configurar argparse
    parser = argparse.ArgumentParser(description='Digital Twin Warehouse Simulator')
    parser.add_argument('--headless', action='store_true',
                       help='Ejecuta la simulacion en modo headless (sin UI)')
    parser.add_argument('--replay', type=str, metavar='FILE.jsonl',
                       help='Ejecuta en modo Replay Viewer consumiendo un archivo .jsonl')
    args = parser.parse_args()

    print("="*60)
    print("SIMULADOR DE ALMACEN - GEMELO DIGITAL")
    print("Sistema de Navegacion Inteligente v2.6")

    if args.replay:
        print("Modo REPLAY VIEWER - Visualizacion de Archivo .jsonl")
        print(f"Archivo: {args.replay}")
    elif args.headless:
        print("Modo HEADLESS - Maxima Velocidad")
    else:
        print("Modo Visual - Con Interfaz Grafica")
    print("="*60)
    print()

    if args.replay:
        # MODO REPLAY VIEWER
        if not os.path.exists(args.replay):
            print(f"Error: Archivo de replay no encontrado: {args.replay}")
            return 1

        print(f"[SIMULATOR] Iniciando en modo replay viewer")
        return ejecutar_modo_replay(args.replay)

    elif args.headless:
        # MODO HEADLESS (existente)
        simulador = SimuladorAlmacen(headless_mode=True)
        simulador.ejecutar()
    else:
        # MODO VISUAL (existente)
        print("INSTRUCCIONES:")
        print("1. Use 'python configurator.py' para crear/modificar configuraciones")
        print("2. Use 'python main.py' para modo visual")
        print("3. Use 'python main.py --headless' para modo de maxima velocidad")
        print("4. Use 'python main.py --replay archivo.jsonl' para modo replay viewer")
        print()
        print("El simulador buscara 'config.json' en el directorio actual.")
        print("Si no existe, usara configuracion por defecto.")
        print()

        simulador = SimuladorAlmacen(headless_mode=False)
        simulador.ejecutar()


if __name__ == "__main__":
    main()