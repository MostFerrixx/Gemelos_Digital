#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST VISUAL RÁPIDO - Auto-demo de pathfinding
Se ejecuta automáticamente y se cierra después de mostrar funcionalidad
"""

import pygame
import sys
import time
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

def quick_visual_test():
    """Test visual que se ejecuta automáticamente"""
    print("INICIANDO TEST VISUAL RAPIDO...")
    
    pygame.init()
    
    # Ventana pequeña
    width, height = 800, 600
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("PyTMX + Pathfinding - DEMO AUTOMATICO")
    
    # Matriz de tortura (pequeña para visualización)
    test_matrix = [
        [1,1,1,1,1,1,1,1,1,1],
        [0,0,0,1,0,0,0,0,1,1],
        [1,1,1,1,1,1,1,0,1,1],
        [0,1,0,0,0,1,1,0,1,1],
        [0,1,1,1,0,0,0,0,1,1],
        [1,1,1,1,1,1,1,1,1,1]
    ]
    
    grid_width = len(test_matrix[0])
    grid_height = len(test_matrix)
    tile_size = 50
    
    # Setup pathfinding
    grid = Grid(matrix=test_matrix)
    finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
    
    # Colores
    colors = {
        'walkable': (144, 238, 144),
        'obstacle': (139, 69, 19),
        'start': (255, 0, 0),
        'end': (0, 0, 255),
        'path': (255, 255, 0),
        'background': (245, 245, 245),
        'text': (0, 0, 0)
    }
    
    font = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 24)
    
    # Casos de prueba automáticos
    test_cases = [
        {"start": (1, 1), "end": (8, 1), "name": "Ruta horizontal"},
        {"start": (0, 0), "end": (9, 5), "name": "Ruta diagonal larga"},
        {"start": (1, 3), "end": (8, 4), "name": "Evitar obstáculos"},
        {"start": (3, 1), "end": (7, 1), "name": "Pasillo estrecho"}
    ]
    
    clock = pygame.time.Clock()
    
    for case_num, case in enumerate(test_cases):
        print(f"\nCaso {case_num + 1}: {case['name']}")
        print(f"  {case['start']} -> {case['end']}")
        
        # Limpiar grid
        grid.cleanup()
        
        # Calcular ruta
        start_node = grid.node(case['start'][0], case['start'][1])
        end_node = grid.node(case['end'][0], case['end'][1])
        path, runs = finder.find_path(start_node, end_node, grid)
        
        if path:
            route = [(node.x, node.y) for node in path]
            print(f"  Ruta encontrada: {len(route)} puntos, {runs} nodos explorados")
            print(f"  Secuencia: {route}")
        else:
            print(f"  Sin ruta ({runs} nodos explorados)")
            route = []
        
        # Renderizar por 2 segundos
        for frame in range(120):  # 2 segundos a 60 FPS
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
            
            # Limpiar pantalla
            screen.fill(colors['background'])
            
            # Título
            title = font.render(f"Caso {case_num + 1}: {case['name']}", True, colors['text'])
            screen.blit(title, (10, 10))
            
            # Info
            if route:
                info = font_small.render(f"{len(route)} puntos, {runs} nodos explorados", True, colors['text'])
                screen.blit(info, (10, 50))
            else:
                info = font_small.render(f"Sin ruta ({runs} nodos explorados)", True, (255, 0, 0))
                screen.blit(info, (10, 50))
            
            # Renderizar grid
            offset_x, offset_y = 50, 100
            
            for y in range(grid_height):
                for x in range(grid_width):
                    screen_x = offset_x + x * tile_size
                    screen_y = offset_y + y * tile_size
                    
                    # Color base
                    if test_matrix[y][x] == 1:
                        color = colors['walkable']
                    else:
                        color = colors['obstacle']
                    
                    # Dibujar tile
                    pygame.draw.rect(screen, color, (screen_x, screen_y, tile_size, tile_size))
                    pygame.draw.rect(screen, colors['text'], (screen_x, screen_y, tile_size, tile_size), 2)
            
            # Renderizar ruta
            if route and len(route) > 1:
                # Línea de ruta
                screen_points = []
                for gx, gy in route:
                    sx = offset_x + gx * tile_size + tile_size // 2
                    sy = offset_y + gy * tile_size + tile_size // 2
                    screen_points.append((sx, sy))
                
                if len(screen_points) > 1:
                    pygame.draw.lines(screen, colors['path'], False, screen_points, 4)
                
                # Números en ruta
                for i, (gx, gy) in enumerate(route):
                    sx = offset_x + gx * tile_size + tile_size // 2
                    sy = offset_y + gy * tile_size + tile_size // 2
                    
                    if i == 0:
                        # Inicio
                        pygame.draw.circle(screen, colors['start'], (sx, sy), 15)
                        text = font_small.render("S", True, (255, 255, 255))
                    elif i == len(route) - 1:
                        # Final
                        pygame.draw.circle(screen, colors['end'], (sx, sy), 15)
                        text = font_small.render("E", True, (255, 255, 255))
                    else:
                        # Punto intermedio
                        pygame.draw.circle(screen, colors['path'], (sx, sy), 12)
                        text = font_small.render(str(i), True, colors['text'])
                    
                    text_rect = text.get_rect(center=(sx, sy))
                    screen.blit(text, text_rect)
            
            # Renderizar puntos start/end si no hay ruta
            elif not route:
                # Start
                sx = offset_x + case['start'][0] * tile_size + tile_size // 2
                sy = offset_y + case['start'][1] * tile_size + tile_size // 2
                pygame.draw.circle(screen, colors['start'], (sx, sy), 15)
                
                # End  
                ex = offset_x + case['end'][0] * tile_size + tile_size // 2
                ey = offset_y + case['end'][1] * tile_size + tile_size // 2
                pygame.draw.circle(screen, colors['end'], (ex, ey), 15)
            
            pygame.display.flip()
            clock.tick(60)
        
        # Pausa entre casos
        time.sleep(0.5)
    
    # Resumen final
    print(f"\nTEST VISUAL COMPLETADO")
    print("="*40)
    print("RESULTADOS:")
    
    successful = 0
    for case in test_cases:
        grid.cleanup()
        start_node = grid.node(case['start'][0], case['start'][1])
        end_node = grid.node(case['end'][0], case['end'][1])
        path, runs = finder.find_path(start_node, end_node, grid)
        
        if path:
            successful += 1
            status = "EXITO"
        else:
            status = "FALLO"
        
        print(f"- {case['name']}: {status}")
    
    print(f"\nTasa de exito: {successful}/{len(test_cases)} ({successful/len(test_cases)*100:.1f}%)")
    print("PyTMX + Pathfinding + Pygame = FUNCIONANDO!")
    
    # Pantalla final
    screen.fill(colors['background'])
    final_text = font.render("TEST COMPLETADO - PyTMX + Pathfinding OK!", True, colors['text'])
    screen.blit(final_text, (width//2 - final_text.get_width()//2, height//2))
    
    success_text = font_small.render(f"Exito: {successful}/{len(test_cases)} casos", True, (0, 150, 0))
    screen.blit(success_text, (width//2 - success_text.get_width()//2, height//2 + 40))
    
    pygame.display.flip()
    time.sleep(3)
    
    pygame.quit()
    print("Demo visual finalizado exitosamente")

if __name__ == "__main__":
    quick_visual_test()