# -*- coding: utf-8 -*-
"""
Visualization Renderer - Renderizado Pygame de mapas TMX, agentes y UI

FASE 2: IMPLEMENTACION COMPLETA
Renderiza todos los elementos visuales leyendo estado_visual y layout_manager.
Implementa renderizado manual de tiles para evitar bugs de layout_manager.

Autor: Claude Code (Implementacion V11)
Estado: PRODUCTION - Implementacion completa
"""

import pygame
from typing import Optional, List, Dict, Any, Tuple

# Importar colores desde config (relative import dentro de src/)
from ..config.colors import (
    COLOR_AGENTE_TERRESTRE,
    COLOR_AGENTE_MONTACARGAS,
    COLOR_AGENTE_IDLE,
    COLOR_AGENTE_TRABAJANDO,
    COLOR_AGENTE_MOVIENDO,
    COLOR_TAREA_PENDIENTE,
    COLOR_TAREA_ASIGNADA,
    COLOR_TAREA_EN_PROGRESO,
    COLOR_TAREA_COMPLETADA,
    COLOR_DASHBOARD_BG,
    COLOR_DASHBOARD_TEXTO,
    COLOR_DASHBOARD_BORDE,
    COLOR_DASHBOARD_HIGHLIGHT,
    COLOR_FONDO_OSCURO,
    COLOR_EXITO,
    COLOR_ADVERTENCIA,
    COLOR_ERROR,
    COLOR_PUNTO_PICKING,
    COLOR_DEPOT
)


# =============================================================================
# CLASE PRINCIPAL DE RENDERIZADO
# =============================================================================

class RendererOriginal:
    """
    Renderer principal para visualizacion de simulacion con Pygame.

    Lee estado_visual y layout_manager para renderizar todos los elementos.
    Implementa renderizado manual de tiles para evitar bugs potenciales.

    Atributos:
        surface: pygame.Surface donde se renderiza (virtual surface)
        font_small: Font pequena (16px)
        font_medium: Font mediana (20px)
        font_large: Font grande (24px)
        tmx_cache_surface: Cache del mapa TMX renderizado
        tmx_cached: Flag indicando si el cache es valido
    """

    def __init__(self, surface: pygame.Surface):
        """
        Inicializa el renderer con una superficie virtual.

        Args:
            surface: pygame.Surface donde se renderizara
        """
        self.surface = surface

        # Inicializar fuentes con manejo de errores
        self._inicializar_fuentes()

        # Cache para renderizado de TMX (optimizacion)
        self.tmx_cache_surface = None
        self.tmx_cached = False

        print("[RENDERER] RendererOriginal inicializado (PRODUCTION)")

    def _inicializar_fuentes(self):
        """
        Inicializa las fuentes de Pygame con manejo de errores.

        Intenta crear fuentes de diferentes tamanos. Si falla, usa None
        y los metodos de renderizado usaran fallbacks.
        """
        try:
            self.font_small = pygame.font.Font(None, 16)
            self.font_medium = pygame.font.Font(None, 20)
            self.font_large = pygame.font.Font(None, 24)
            print("[RENDERER] Fuentes inicializadas correctamente")
        except Exception as e:
            print(f"[RENDERER] Advertencia: No se pudieron inicializar fuentes: {e}")
            self.font_small = None
            self.font_medium = None
            self.font_large = None

    def renderizar_mapa_tmx(self, surface: pygame.Surface, tmx_data) -> None:
        """
        Renderiza el mapa TMX de fondo en la superficie usando renderizado manual.

        IMPORTANTE: Implementa renderizado manual tile-por-tile para evitar
        dependencias de layout_manager.render() que podria tener bugs.

        Optimizacion: Usa cache para evitar re-renderizar el mapa cada frame.
        El cache solo se invalida si cambia el tamano de la superficie.

        Args:
            surface: pygame.Surface de destino
            tmx_data: Datos TMX cargados por pytmx (pytmx.TiledMap)

        Manejo de errores:
            - Si tmx_data es None: Llena con color de fondo
            - Si hay error renderizando: Llena con color de fondo

        BUGFIX 2025-10-04: Corregido uso de layer index en vez de layer.id
        """
        # Validar tmx_data
        if not tmx_data:
            print("[RENDERER] Advertencia: tmx_data es None, llenando con fondo")
            surface.fill(COLOR_FONDO_OSCURO)
            return

        try:
            # Optimizacion: Si ya tenemos cache valido, usarlo
            if self.tmx_cached and self.tmx_cache_surface:
                surface.blit(self.tmx_cache_surface, (0, 0))
                return

            # Renderizado manual tile por tile
            # Acceso directo a pytmx sin intermediarios

            # Limpiar superficie primero
            surface.fill(COLOR_FONDO_OSCURO)

            # FIX 2: Contador de tiles dibujados para diagnostico
            tiles_dibujados = 0
            total_tiles = 0

            # FIX 1: Usar enumerate() para obtener indice correcto de capa
            for layer_idx, layer in enumerate(tmx_data.visible_layers):
                # Solo procesar capas de tiles (no object layers)
                if not hasattr(layer, 'data'):
                    continue

                # Iterar todo el grid
                for y in range(tmx_data.height):
                    for x in range(tmx_data.width):
                        total_tiles += 1
                        try:
                            # BUGFIX: Usar layer_idx (indice) en vez de layer.id
                            tile_image = tmx_data.get_tile_image(x, y, layer_idx)

                            if tile_image:
                                # Calcular posicion pixel (esquina superior izquierda)
                                pixel_x = x * tmx_data.tilewidth
                                pixel_y = y * tmx_data.tileheight

                                # Blit tile a la superficie
                                surface.blit(tile_image, (pixel_x, pixel_y))
                                tiles_dibujados += 1

                        except Exception as e:
                            # FIX 2: Log de errores en modo debug (primera capa solo)
                            if layer_idx == 0 and tiles_dibujados == 0:
                                print(f"[RENDERER] Error en tile ({x},{y}): {e}")

            # FIX 2: Logging de tiles dibujados
            print(f"[RENDERER] Tiles dibujados: {tiles_dibujados}/{total_tiles}")

            # FIX 3: Validar que la superficie NO este vacia antes de cachear
            if tiles_dibujados > 0 and not self._is_surface_empty(surface):
                # Crear cache del mapa renderizado
                self.tmx_cache_surface = surface.copy()
                self.tmx_cached = True
                print("[RENDERER] Mapa TMX renderizado exitosamente - Cache creado")
            else:
                # FIX 3: No cachear superficie vacia
                print(f"[RENDERER] ADVERTENCIA: Superficie TMX vacia ({tiles_dibujados} tiles), NO se cachea")
                self.tmx_cached = False

        except Exception as e:
            # Fallback en caso de error general
            print(f"[RENDERER] Error renderizando TMX: {e}")
            surface.fill(COLOR_FONDO_OSCURO)

    def _is_surface_empty(self, surface: pygame.Surface) -> bool:
        """
        Verifica si una superficie esta completamente vacia (solo fondo oscuro).

        FIX 3: Previene cachear superficies negras/vacias.

        Args:
            surface: pygame.Surface a verificar

        Returns:
            True si la superficie esta vacia, False si tiene contenido
        """
        try:
            # Muestrear algunos pixeles en diferentes posiciones
            width = surface.get_width()
            height = surface.get_height()

            sample_points = [
                (0, 0),
                (width // 4, height // 4),
                (width // 2, height // 2),
                (3 * width // 4, 3 * height // 4),
                (width - 1, height - 1)
            ]

            for x, y in sample_points:
                if 0 <= x < width and 0 <= y < height:
                    color = surface.get_at((x, y))
                    # Si algun pixel NO es el fondo oscuro, hay contenido
                    if color[:3] != COLOR_FONDO_OSCURO:
                        return False

            return True
        except Exception:
            # Si falla la verificacion, asumir que tiene contenido
            return False

    def actualizar_escala(self, width: int, height: int) -> None:
        """
        Actualiza la escala de renderizado cuando cambia tamano de ventana.

        Invalida el cache del mapa TMX para forzar re-renderizado.

        Args:
            width: Nuevo ancho de ventana
            height: Nuevo alto de ventana
        """
        # Invalidar cache de TMX
        self.tmx_cached = False
        self.tmx_cache_surface = None

        print(f"[RENDERER] Escala actualizada a {width}x{height}, cache invalidado")


# =============================================================================
# FUNCIONES DE RENDERIZADO DE NIVEL MODULO
# =============================================================================

def renderizar_agentes(surface: pygame.Surface,
                      agentes_list: List[Dict[str, Any]],
                      layout_manager) -> None:
    """
    Renderiza la lista de agentes (operarios) en la superficie.

    Lee los datos de agentes desde estado_visual["operarios"].values()
    y los dibuja como circulos con colores segun tipo y status.

    Args:
        surface: pygame.Surface de destino
        agentes_list: Lista de dicts con datos de agentes (desde estado_visual)
        layout_manager: LayoutManager para conversiones grid<->pixel (no usado actualmente,
                       ya que estado_visual provee coordenadas pixel directamente)

    Estructura esperada de cada agente:
        {
            "id": str,
            "x": int,  # Posicion pixel X
            "y": int,  # Posicion pixel Y
            "tipo": str,  # "terrestre" | "montacargas"
            "status": str,  # "idle" | "working" | "traveling"
            "direccion_x": int,  # -1, 0, 1
            "direccion_y": int,  # -1, 0, 1
            "accion": str  # Descripcion legible
        }

    Colores:
        - Terrestre: Naranja (COLOR_AGENTE_TERRESTRE)
        - Montacargas: Azul (COLOR_AGENTE_MONTACARGAS)
        - Idle: Gris (COLOR_AGENTE_IDLE)
        - Working: Verde (COLOR_AGENTE_TRABAJANDO)
        - Traveling: Amarillo (COLOR_AGENTE_MOVIENDO)
    """
    # Validar entrada
    if not agentes_list:
        return

    # Inicializar fuente para IDs
    try:
        font = pygame.font.Font(None, 16)
    except:
        font = None

    # Renderizar cada agente
    for agente in agentes_list:
        try:
            # Obtener posicion pixel
            x = agente.get('x', 100)
            y = agente.get('y', 100)

            # Obtener tipo y status
            tipo = agente.get('tipo', 'terrestre')
            status = agente.get('status', 'idle')
            agent_id = agente.get('id', 'Unknown')

            # Determinar color segun tipo y status
            color = _determinar_color_agente(tipo, status)

            # Dibujar agente como circulo
            radio = 8
            pygame.draw.circle(surface, color, (int(x), int(y)), radio)

            # Dibujar borde negro para mejor visibilidad
            pygame.draw.circle(surface, (0, 0, 0), (int(x), int(y)), radio, 1)

            # Dibujar direccion si esta en movimiento
            direccion_x = agente.get('direccion_x', 0)
            direccion_y = agente.get('direccion_y', 0)

            if direccion_x != 0 or direccion_y != 0:
                # Dibujar pequena flecha indicando direccion
                flecha_len = 12
                end_x = int(x + direccion_x * flecha_len)
                end_y = int(y + direccion_y * flecha_len)
                pygame.draw.line(surface, (255, 255, 255),
                               (int(x), int(y)), (end_x, end_y), 2)

            # Dibujar ID del agente encima
            if font:
                # Convertir ID largo a formato corto para display
                if 'GroundOp-' in agent_id:
                    # GroundOp-01 -> GO1
                    number = agent_id.replace('GroundOp-', '').lstrip('0') or '1'
                    id_corto = f"GO{number}"
                elif 'Forklift-' in agent_id:
                    # Forklift-01 -> FL1  
                    number = agent_id.replace('Forklift-', '').lstrip('0') or '1'
                    id_corto = f"FL{number}"
                else:
                    # Fallback: mostrar solo ultimos caracteres del ID para no saturar
                    id_corto = agent_id.split('_')[-1] if '_' in agent_id else agent_id[-2:]
                texto = font.render(id_corto, True, (255, 255, 255))
                texto_rect = texto.get_rect(center=(int(x), int(y) - 15))

                # Fondo semi-transparente para mejor legibilidad
                fondo_rect = texto_rect.inflate(4, 2)
                pygame.draw.rect(surface, (0, 0, 0), fondo_rect)

                surface.blit(texto, texto_rect)

        except Exception as e:
            # Si falla un agente individual, continuar con el siguiente
            print(f"[RENDERER] Error renderizando agente: {e}")
            continue


def renderizar_rutas_tours(surface: pygame.Surface,
                           estado_visual: Dict[str, Any],
                           layout_manager) -> None:
    """
    Renderiza las rutas de tours asignados a cada operario.
    
    Dibuja:
    - Marcadores en los puntos de picking (ubicaciones de WOs)
    - Lineas punteadas semi-transparentes conectando los puntos en orden
    - Solo muestra rutas de operarios que estan trabajando en tours
    
    Args:
        surface: pygame.Surface donde dibujar
        estado_visual: Estado visual global
        layout_manager: LayoutManager para conversion grid->pixel
    """
    # Validar entrada
    if not estado_visual or not layout_manager:
        return
    
    operarios = estado_visual.get("operarios", {})
    work_orders = estado_visual.get("work_orders", {})
    
    # Colores para diferentes tipos de agentes
    COLOR_TERRESTRE = (255, 165, 0)  # Naranja
    COLOR_MONTACARGAS = (100, 150, 255)  # Azul
    
    # Renderizar ruta para cada operario que tiene tour asignado
    for agent_id, agente in operarios.items():
        try:
            # Verificar si tiene tour asignado y WOs
            wo_ids = agente.get('work_orders_asignadas', [])
            if not wo_ids:
                continue
            
            # Solo mostrar rutas de operarios que estan trabajando (comentar temporalmente para debug)
            # if agente.get('status') not in ['working', 'moving', 'picking']:
            #     continue
            
            # DEBUG: Solo mostrar info una vez por agente para no llenar logs
            if not hasattr(renderizar_rutas_tours, '_debug_state'):
                renderizar_rutas_tours._debug_state = {}
            
            if agent_id not in renderizar_rutas_tours._debug_state:
                # Debug: logging reducido
                renderizar_rutas_tours._debug_state[agent_id] = True
            
            # Extraer ubicaciones de las WOs
            ubicaciones = []
            for wo_id in wo_ids:
                if wo_id in work_orders:
                    wo = work_orders[wo_id]
                    
                    # Obtener ubicacion (puede ser grid o pixel)
                    if 'ubicacion' in wo:
                        ubicacion = wo['ubicacion']
                    elif 'location' in wo:
                        ubicacion = wo['location']
                    else:
                        continue
                    
                    # Convertir a pixel si es grid
                    # Manejar tanto listas como tuplas
                    if isinstance(ubicacion, (tuple, list)) and len(ubicacion) == 2:
                        grid_x, grid_y = ubicacion[0], ubicacion[1]
                        
                        # Convertir grid a pixel
                        pixel_x, pixel_y = _convertir_grid_a_pixel_seguro(
                            layout_manager, grid_x, grid_y)
                        ubicaciones.append((pixel_x, pixel_y))
            
            # Eliminar ubicaciones duplicadas (varias WOs en la misma ubicacion)
            ubicaciones_unicas = []
            for loc in ubicaciones:
                if loc not in ubicaciones_unicas:
                    ubicaciones_unicas.append(loc)
            
            # Validar que hay ubicaciones
            if len(ubicaciones_unicas) < 1:
                continue  # No hay ubicaciones
            
            ubicaciones = ubicaciones_unicas  # Usar ubicaciones unicas
            
            # Determinar color segun tipo de agente
            tipo = agente.get('tipo', 'terrestre')
            color_agente = COLOR_TERRESTRE if tipo == 'terrestre' else COLOR_MONTACARGAS
            
            # Dibujar lineas punteadas conectando los puntos (solo si hay mas de 1 ubicacion)
            if len(ubicaciones) > 1:
                for i in range(len(ubicaciones) - 1):
                    x1, y1 = ubicaciones[i]
                    x2, y2 = ubicaciones[i + 1]
                    
                    # Dibujar linea punteada directamente
                    _dibujar_linea_punteada_directo(surface, (int(x1), int(y1)), 
                                                   (int(x2), int(y2)), color_agente, 2, 8)
            
            # Dibujar marcadores en cada punto de picking
            for i, (px, py) in enumerate(ubicaciones):
                # Circulo mas grande para el punto actual si hay info de current_task
                current_task = agente.get('current_task')
                is_current = (i < len(wo_ids) and wo_ids[i] == current_task)
                
                radio = 10 if is_current else 6
                color_marcador = (255, 255, 0) if is_current else color_agente  # Amarillo para actual
                
                # Dibujar marcador
                pygame.draw.circle(surface, color_marcador, (int(px), int(py)), radio)
                pygame.draw.circle(surface, (0, 0, 0), (int(px), int(py)), radio, 2)
                
                # Numero de secuencia del punto
                if i < 10:  # Solo mostrar numeros del 0-9 para no saturar
                    try:
                        font = pygame.font.Font(None, 14)
                        texto = font.render(str(i), True, (255, 255, 255))
                        texto_rect = texto.get_rect(center=(int(px), int(py)))
                        surface.blit(texto, texto_rect)
                    except:
                        pass
        
        except Exception as e:
            # Si falla una ruta individual, continuar con las otras
            print(f"[RENDERER] Error renderizando ruta: {e}")
            continue


def _dibujar_linea_punteada_directo(surface: pygame.Surface,
                                    punto_inicio: Tuple[int, int],
                                    punto_fin: Tuple[int, int],
                                    color: Tuple[int, int, int],
                                    grosor: int = 2,
                                    segmento: int = 8) -> None:
    """
    Dibuja una linea punteada directamente en la superficie pygame.
    Version simplificada sin transparencia para mejor rendimiento.
    
    Args:
        surface: Superficie donde dibujar
        punto_inicio: Coordenadas (x, y) del inicio
        punto_fin: Coordenadas (x, y) del fin
        color: Color RGB
        grosor: Grosor de la linea
        segmento: Longitud de cada segmento punteado
    """
    x1, y1 = punto_inicio
    x2, y2 = punto_fin
    
    # Calcular vector de direccion
    dx = x2 - x1
    dy = y2 - y1
    longitud = int((dx**2 + dy**2)**0.5)
    
    if longitud == 0:
        return
    
    # Normalizar direccion
    dx_norm = dx / longitud * segmento
    dy_norm = dy / longitud * segmento
    
    # Dibujar segmentos punteados
    distancia = 0
    dibujar_segmento = True  # Alterna entre dibujar y saltar
    
    while distancia < longitud:
        # Calcular posicion actual
        x_actual = int(x1 + dx / longitud * distancia)
        y_actual = int(y1 + dy / longitud * distancia)
        
        # Calcular posicion del siguiente segmento
        siguiente_distancia = min(distancia + segmento, longitud)
        x_sig = int(x1 + dx / longitud * siguiente_distancia)
        y_sig = int(y1 + dy / longitud * siguiente_distancia)
        
        # Dibujar o saltar segun el estado
        if dibujar_segmento:
            pygame.draw.line(surface, color, (x_actual, y_actual), (x_sig, y_sig), grosor)
        
        distancia = siguiente_distancia
        dibujar_segmento = not dibujar_segmento  # Alternar


def renderizar_tareas_pendientes(surface: pygame.Surface,
                                 tareas_list: List[Any],
                                 layout_manager) -> None:
    """
    Renderiza marcadores de WorkOrders pendientes en el mapa.

    Solo renderiza WorkOrders que NO estan completadas.
    Usa colores diferentes segun el status de la WO.

    Args:
        surface: pygame.Surface de destino
        tareas_list: Lista de WorkOrders (pueden ser objetos o dicts)
        layout_manager: LayoutManager para conversion grid->pixel

    Colores segun status:
        - pending: Amarillo (COLOR_TAREA_PENDIENTE)
        - assigned: Naranja (COLOR_TAREA_ASIGNADA)
        - in_progress: Azul claro (COLOR_TAREA_EN_PROGRESO)
        - completed: NO se renderiza
    """
    # Validar entrada
    if not tareas_list or not layout_manager:
        return

    # Inicializar fuente pequena para IDs
    try:
        font = pygame.font.Font(None, 12)
    except:
        font = None

    # Contador para limitar renderizado (optimizacion)
    max_tareas_renderizar = 200
    count = 0

    # Renderizar cada WorkOrder
    for tarea in tareas_list:
        # Limite de optimizacion
        if count >= max_tareas_renderizar:
            break

        try:
            # Obtener datos de la tarea (compatible con objetos y dicts)
            if hasattr(tarea, 'status'):
                # Es un objeto WorkOrder
                status = tarea.status
                location = tarea.location if hasattr(tarea, 'location') else (0, 0)
                wo_id = tarea.id if hasattr(tarea, 'id') else 'WO-???'
            else:
                # Es un dict
                status = tarea.get('status', 'released')
                location = tarea.get('location', (0, 0))
                wo_id = tarea.get('id', 'WO-???')

            # No renderizar tareas completadas (staged)
            if status == 'staged':
                continue

            # Convertir posicion grid a pixel
            grid_x, grid_y = location
            pixel_x, pixel_y = _convertir_grid_a_pixel_seguro(layout_manager, grid_x, grid_y)

            # Determinar color segun status
            if status == 'released':
                color = COLOR_TAREA_PENDIENTE
            elif status == 'assigned':
                color = COLOR_TAREA_ASIGNADA
            elif status == 'in_progress':
                color = COLOR_TAREA_EN_PROGRESO
            else:
                color = COLOR_TAREA_PENDIENTE  # Fallback

            # Dibujar marcador como pequeno cuadrado
            tamano = 6
            rect = pygame.Rect(pixel_x - tamano//2, pixel_y - tamano//2, tamano, tamano)
            pygame.draw.rect(surface, color, rect)

            # Borde negro para visibilidad
            pygame.draw.rect(surface, (0, 0, 0), rect, 1)

            count += 1

        except Exception as e:
            # Si falla una tarea, continuar con la siguiente
            continue


def renderizar_dashboard(pantalla: pygame.Surface,
                        offset_x: int,
                        metricas_dict: Dict[str, Any],
                        operarios_list: List[Dict[str, Any]]) -> None:
    """
    Renderiza el panel lateral de dashboard con metricas en tiempo real.

    REFACTORED V11: Esta funcion ahora delega a DashboardOriginal.
    Mantenida por compatibilidad con codigo existente.

    Dibuja directamente en la pantalla principal (no en virtual_surface)
    en la posicion offset_x (lado derecho de la ventana).

    Args:
        pantalla: pygame.Surface principal (ventana completa)
        offset_x: Posicion X donde empieza el panel (ancho del area de simulacion)
        metricas_dict: Dict con metricas globales (estado_visual["metricas"])
        operarios_list: Lista de operarios (estado_visual["operarios"].values())

    Estructura esperada de metricas_dict:
        {
            "tiempo_simulacion": float,
            "workorders_completadas": int,
            "tareas_completadas": int,
            "operarios_idle": int,
            "operarios_working": int,
            "operarios_traveling": int,
            "utilizacion_promedio": float
        }

    Layout:
        - Panel de 400px de ancho
        - Fondo blanco (COLOR_DASHBOARD_BG)
        - Texto negro (COLOR_DASHBOARD_TEXTO)
        - Secciones: Titulo, Metricas Globales, Estado Operarios, Controles
    """
    # REFACTOR V11: Delegacion a DashboardOriginal
    # Crear instancia singleton en primer uso
    if not hasattr(renderizar_dashboard, '_dashboard_instance'):
        from .dashboard import DashboardOriginal
        renderizar_dashboard._dashboard_instance = DashboardOriginal()
        print("[RENDERER] Dashboard delegando a DashboardOriginal (REFACTOR V11)")

    # Reconstruir estado_visual desde parametros legacy
    # (para compatibilidad con codigo que llama con firma antigua)
    # Handle both dict and string operarios_list
    operarios_dict = {}
    for i, op in enumerate(operarios_list):
        if isinstance(op, dict):
            operarios_dict[op.get('id', f'op_{i}')] = op
        else:
            # If op is a string, create a simple dict structure
            operarios_dict[f'op_{i}'] = {'id': f'op_{i}', 'name': str(op)}

    estado_visual = {
        'metricas': metricas_dict,
        'operarios': operarios_dict
    }

    # Delegar renderizado a clase DashboardOriginal
    renderizar_dashboard._dashboard_instance.renderizar(pantalla, estado_visual, offset_x)


def renderizar_diagnostico_layout(surface: pygame.Surface, layout_manager) -> None:
    """
    Renderiza grid de diagnostico del layout para debugging.

    Muestra:
        - Grid de celdas con colores segun walkability
        - Puntos de picking en cyan
        - Coordenadas de grid cada 5 celdas

    Args:
        surface: pygame.Surface de destino
        layout_manager: LayoutManager con datos del grid

    Uso:
        Activar con tecla especial en modo debug
    """
    # Validar entrada
    if not layout_manager:
        return

    try:
        # Inicializar fuente para coordenadas
        try:
            font = pygame.font.Font(None, 12)
        except:
            font = None

        # Iterar todo el grid
        for y in range(layout_manager.grid_height):
            for x in range(layout_manager.grid_width):
                # Calcular posicion pixel
                pixel_x = x * layout_manager.tile_width
                pixel_y = y * layout_manager.tile_height

                # Determinar color segun walkability
                if layout_manager.is_walkable(x, y):
                    # Walkable: verde claro semi-transparente
                    color = (0, 255, 0, 50)
                else:
                    # Blocked: rojo claro semi-transparente
                    color = (255, 0, 0, 50)

                # Dibujar rectangulo de celda
                rect = pygame.Rect(pixel_x, pixel_y,
                                  layout_manager.tile_width,
                                  layout_manager.tile_height)
                pygame.draw.rect(surface, color[:3], rect)

                # Borde de celda
                pygame.draw.rect(surface, (100, 100, 100), rect, 1)

                # Dibujar coordenadas cada 5 celdas
                if font and x % 5 == 0 and y % 5 == 0:
                    texto = font.render(f"{x},{y}", True, (200, 200, 200))
                    surface.blit(texto, (pixel_x + 2, pixel_y + 2))

        # Dibujar puntos de picking
        for picking_point in layout_manager.picking_points:
            pixel_pos = picking_point.get('pixel_position', (0, 0))
            pygame.draw.circle(surface, COLOR_PUNTO_PICKING, pixel_pos, 5)
            pygame.draw.circle(surface, (0, 0, 0), pixel_pos, 5, 1)

    except Exception as e:
        print(f"[RENDERER] Error en renderizado de diagnostico: {e}")


# =============================================================================
# FUNCIONES AUXILIARES PRIVADAS
# =============================================================================

def _determinar_color_agente(tipo: str, status: str) -> Tuple[int, int, int]:
    """
    Determina el color de un agente segun su status (igual que el dashboard).

    Args:
        tipo: Tipo de agente ("terrestre" | "montacargas") - NO USADO
        status: Status del agente ("idle" | "moving" | "picking" | "lifting" | "unloading" | "working")

    Returns:
        Tupla RGB (r, g, b)

    Logica de colores (igual que dashboard):
        - moving (En ruta): Verde claro #A6E3A1
        - picking (Picking): Azul claro #89B4FA  
        - lifting (Elevando): Púrpura claro #CBA6F7
        - unloading (Descargando): Rosa/Rojo claro #F38BA8
        - idle (Inactivo): Gris #808080
        - working (Trabajando): Naranja #FF9800
    """
    # Colores del dashboard por status
    status_colors = {
        'moving': (166, 227, 161),    # #A6E3A1 - Verde claro (En ruta)
        'picking': (137, 180, 250),   # #89B4FA - Azul claro (Picking)
        'lifting': (203, 166, 247),   # #CBA6F7 - Púrpura claro (Elevando)
        'unloading': (243, 139, 168), # #F38BA8 - Rosa/Rojo claro (Descargando)
        'discharging': (243, 139, 168), # #F38BA8 - Mismo que unloading
        'idle': (128, 128, 128),      # #808080 - Gris (Inactivo)
        'working': (255, 152, 0),     # #FF9800 - Naranja (Trabajando)
        'traveling': (166, 227, 161), # #A6E3A1 - Mismo que moving
        'waiting': (128, 128, 128),   # #808080 - Gris (Esperando)
        'error': (255, 0, 0),         # #FF0000 - Rojo (Error)
    }
    
    # Retornar color segun status, fallback a gris si no se encuentra
    return status_colors.get(status.lower(), status_colors['idle'])


def _convertir_grid_a_pixel_seguro(layout_manager,
                                   grid_x: int,
                                   grid_y: int) -> Tuple[int, int]:
    """
    Convierte coordenadas grid a pixel con validacion defensiva.

    Implementa multiples niveles de validacion para evitar errores:
        1. Valida que layout_manager no sea None
        2. Valida limites del grid
        3. Valida resultado de la conversion
        4. Provee fallback en caso de error

    Args:
        layout_manager: LayoutManager para conversion
        grid_x: Coordenada X en grid
        grid_y: Coordenada Y en grid

    Returns:
        Tupla (pixel_x, pixel_y)
        En caso de error: (100, 100) como posicion default segura
    """
    # Validacion 1: layout_manager existe
    if not layout_manager:
        return (100, 100)

    try:
        # Validacion 2: Clamp a limites del grid
        grid_x = max(0, min(grid_x, layout_manager.grid_width - 1))
        grid_y = max(0, min(grid_y, layout_manager.grid_height - 1))

        # Conversion usando metodo de layout_manager
        pixel_x, pixel_y = layout_manager.grid_to_pixel(grid_x, grid_y)

        # Validacion 3: Resultado es valido
        if pixel_x < 0 or pixel_y < 0:
            return (100, 100)

        if pixel_x > layout_manager.pixel_width or pixel_y > layout_manager.pixel_height:
            return (100, 100)

        return (pixel_x, pixel_y)

    except Exception as e:
        # Fallback en caso de cualquier error
        print(f"[RENDERER] Error en conversion grid->pixel: {e}")
        return (100, 100)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Clase principal
    'RendererOriginal',

    # Funciones de renderizado
    'renderizar_agentes',
    'renderizar_rutas_tours',
    'renderizar_tareas_pendientes',
    'renderizar_dashboard',
    'renderizar_diagnostico_layout'
]


print("[OK] Modulo 'subsystems.visualization.renderer' cargado (PRODUCTION - Implementacion completa)")
