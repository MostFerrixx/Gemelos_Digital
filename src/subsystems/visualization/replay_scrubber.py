# -*- coding: utf-8 -*-
"""
ReplayScrubber - Componente de UI para la barra de progreso del replay.

Este modulo define la clase ReplayScrubber, un componente de UI custom
hecho con Pygame nativo para permitir al usuario saltar a cualquier punto
en el tiempo de la simulacion de replay.

Caracteristicas:
- Barra de progreso visual.
- Manija (thumb) arrastrable.
- Muestra el tiempo actual y total.
- Envia un evento custom de Pygame cuando el usuario busca un nuevo tiempo.
"""

import pygame

# Evento custom para notificar al motor de replay que se debe buscar un nuevo tiempo.
# Se usara pygame.event.post() para enviarlo.
REPLAY_SEEK_EVENT = pygame.USEREVENT + 1

class ReplayScrubber:
    """
    Una barra de progreso (scrubber) para el ReplayViewer.
    Permite al usuario visualizar el progreso y saltar a un tiempo especifico.
    """
    def __init__(self, x: int, y: int, width: int, height: int,
                 font: pygame.font.Font,
                 colors: dict):
        """
        Inicializa el componente Scrubber.

        Args:
            x (int): Posicion X del componente.
            y (int): Posicion Y del componente.
            width (int): Ancho del componente.
            height (int): Alto del componente.
            font (pygame.font.Font): Fuente para renderizar el texto del tiempo.
            colors (dict): Paleta de colores a usar para el renderizado.
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.thumb_rect = pygame.Rect(x, y - 5, 10, height + 10)
        self.font = font
        self.colors = colors

        self.min_time = 0.0
        self.max_time = 1.0
        self.current_time = 0.0

        self.dragging = False  # Estado para saber si el usuario esta arrastrando el thumb

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Maneja los eventos de mouse para el scrubber.
        Detecta clics y arrastres en la barra o el thumb.

        Args:
            event (pygame.event.Event): El evento de Pygame a procesar.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                self.dragging = True
                self._update_time_from_pos(event.pos)
                self._post_seek_event()

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.dragging:
                self.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self._update_time_from_pos(event.pos)
                self._post_seek_event()

    def _update_time_from_pos(self, pos: tuple[int, int]) -> None:
        """
        Calcula y actualiza el tiempo actual basado en la posicion del mouse.

        Args:
            pos (tuple[int, int]): La posicion (x, y) del cursor del mouse.
        """
        # Calcula el tiempo basado en la posicion X del click dentro del rectangulo
        relative_x = pos[0] - self.rect.x
        progress = max(0.0, min(1.0, relative_x / self.rect.width))
        self.current_time = self.min_time + progress * (self.max_time - self.min_time)

    def _post_seek_event(self) -> None:
        """
        Crea y postea el evento custom REPLAY_SEEK_EVENT con el tiempo objetivo.
        """
        seek_event = pygame.event.Event(REPLAY_SEEK_EVENT, {'target_time': self.current_time})
        pygame.event.post(seek_event)

    def update(self, current_time: float, max_time: float) -> None:
        """
        Actualiza el estado del scrubber con los tiempos de la simulacion.

        Args:
            current_time (float): El tiempo de reproduccion actual.
            max_time (float): El tiempo total de la simulacion.
        """
        self.max_time = max(1.0, max_time) # Evitar division por cero
        if not self.dragging:
            self.current_time = max(self.min_time, min(self.max_time, current_time))

    def draw(self, surface: pygame.Surface) -> None:
        """
        Dibuja el componente scrubber en la superficie dada.

        Args:
            surface (pygame.Surface): La superficie de Pygame donde dibujar.
        """
        # Fondo de la barra
        pygame.draw.rect(surface, self.colors['surface_0'], self.rect, border_radius=5)
        pygame.draw.rect(surface, self.colors['border_primary'], self.rect, width=1, border_radius=5)

        # Barra de progreso
        progress_ratio = (self.current_time - self.min_time) / (self.max_time - self.min_time)
        progress_width = int(self.rect.width * progress_ratio)
        progress_rect = pygame.Rect(self.rect.x, self.rect.y, progress_width, self.rect.height)
        pygame.draw.rect(surface, self.colors['accent_blue'], progress_rect, border_radius=5)

        # Thumb (manija)
        thumb_x = self.rect.x + progress_width - (self.thumb_rect.width / 2)
        self.thumb_rect.centerx = self.rect.x + progress_width
        self.thumb_rect.centery = self.rect.centery
        pygame.draw.rect(surface, self.colors['text_primary'], self.thumb_rect, border_radius=3)
        pygame.draw.rect(surface, self.colors['accent_purple'], self.thumb_rect, width=2, border_radius=3)

        # Texto de tiempo
        def format_time(seconds):
            mins, secs = divmod(int(seconds), 60)
            return f"{mins:02d}:{secs:02d}"

        current_time_text = format_time(self.current_time)
        max_time_text = format_time(self.max_time)

        time_str = f"{current_time_text} / {max_time_text}"
        time_surface = self.font.render(time_str, True, self.colors['text_secondary'])
        time_rect = time_surface.get_rect(centerx=self.rect.centerx, y=self.rect.bottom + 5)
        surface.blit(time_surface, time_rect)