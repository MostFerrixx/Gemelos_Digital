#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANÁLISIS DE CÓDIGO LEGACY - Identificar qué puede eliminarse
"""

import os
import sys
import ast
import re
from pathlib import Path

class LegacyAnalyzer:
    """Analizador de código legacy para identificar eliminaciones seguras"""
    
    def __init__(self, base_path="git"):
        self.base_path = base_path
        self.analysis_results = {}
        self.dependency_graph = {}
        self.safe_to_remove = []
        self.requires_attention = []
        
    def analyze_file(self, file_path):
        """Analizar un archivo Python"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Contar líneas
            lines = content.split('\n')
            total_lines = len(lines)
            code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
            
            # Buscar patrones de código legacy
            legacy_patterns = {
                'astar_implementations': len(re.findall(r'class.*A.*Star|def.*a.*star', content, re.IGNORECASE)),
                'pathfinding_functions': len(re.findall(r'def.*path.*find|def.*calcular.*ruta', content, re.IGNORECASE)),
                'grid_classes': len(re.findall(r'class.*Grid|class.*Nodo', content, re.IGNORECASE)),
                'navigation_logic': len(re.findall(r'navegacion|navigation|routing', content, re.IGNORECASE)),
                'strict_lane_system': len(re.findall(r'strict.*lane|carril.*estricto', content, re.IGNORECASE)),
            }
            
            # Verificar importaciones
            imports = re.findall(r'^from .* import .*|^import .*', content, re.MULTILINE)
            
            analysis = {
                'file_path': file_path,
                'total_lines': total_lines,
                'code_lines': code_lines,
                'legacy_patterns': legacy_patterns,
                'imports': imports,
                'has_astar': legacy_patterns['astar_implementations'] > 0,
                'has_pathfinding': legacy_patterns['pathfinding_functions'] > 0,
                'complexity_score': sum(legacy_patterns.values())
            }
            
            return analysis
            
        except Exception as e:
            return {'error': str(e), 'file_path': file_path}
    
    def analyze_codebase(self):
        """Analizar toda la base de código"""
        print("ANÁLISIS DE CÓDIGO LEGACY")
        print("="*50)
        
        python_files = []
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        print(f"Analizando {len(python_files)} archivos Python...")
        
        total_lines = 0
        legacy_candidates = []
        
        for file_path in python_files:
            analysis = self.analyze_file(file_path)
            
            if 'error' not in analysis:
                self.analysis_results[file_path] = analysis
                total_lines += analysis['total_lines']
                
                # Identificar candidatos para eliminación
                if analysis['complexity_score'] > 5:
                    legacy_candidates.append(analysis)
        
        # Ordenar por complejidad (más complejo = más legacy)
        legacy_candidates.sort(key=lambda x: x['complexity_score'], reverse=True)
        
        print(f"\nRESUMEN GENERAL:")
        print(f"- Total archivos: {len(python_files)}")
        print(f"- Total líneas: {total_lines}")
        print(f"- Candidatos legacy: {len(legacy_candidates)}")
        
        return legacy_candidates
    
    def identify_safe_removals(self):
        """Identificar qué puede eliminarse de forma segura"""
        
        print(f"\n{'='*60}")
        print("IDENTIFICACIÓN DE ELIMINACIONES SEGURAS")
        print("="*60)
        
        legacy_candidates = self.analyze_codebase()
        
        print(f"\nARCHIVOS CON ALTO CONTENIDO LEGACY:")
        print("-" * 40)
        
        for i, analysis in enumerate(legacy_candidates[:10], 1):  # Top 10
            file_name = os.path.basename(analysis['file_path'])
            complexity = analysis['complexity_score']
            lines = analysis['total_lines']
            
            print(f"{i:2d}. {file_name:25} - {lines:4d} líneas - Score: {complexity}")
            
            # Detalles de patrones legacy
            patterns = analysis['legacy_patterns']
            if patterns['astar_implementations'] > 0:
                print(f"    🔍 A* implementations: {patterns['astar_implementations']}")
            if patterns['pathfinding_functions'] > 0:
                print(f"    🛤️  Pathfinding functions: {patterns['pathfinding_functions']}")
            if patterns['grid_classes'] > 0:
                print(f"    📊 Grid classes: {patterns['grid_classes']}")
            if patterns['strict_lane_system'] > 0:
                print(f"    🚧 Strict lane system: {patterns['strict_lane_system']}")
        
        return legacy_candidates
    
    def generate_removal_recommendations(self):
        """Generar recomendaciones de eliminación"""
        
        legacy_candidates = self.identify_safe_removals()
        
        print(f"\n{'='*60}")
        print("RECOMENDACIONES DE ELIMINACIÓN")
        print("="*60)
        
        # Categorizar archivos
        high_priority_removal = []
        medium_priority_removal = []
        requires_careful_review = []
        
        for analysis in legacy_candidates:
            file_name = os.path.basename(analysis['file_path'])
            complexity = analysis['complexity_score']
            lines = analysis['total_lines']
            
            # Criterios de eliminación
            if complexity > 10 and lines > 500:
                high_priority_removal.append((file_name, analysis))
            elif complexity > 5 and lines > 200:
                medium_priority_removal.append((file_name, analysis))
            elif complexity > 0:
                requires_careful_review.append((file_name, analysis))
        
        print(f"\n🔥 ALTA PRIORIDAD - Eliminación Inmediata ({len(high_priority_removal)} archivos):")
        total_lines_high = 0
        for file_name, analysis in high_priority_removal:
            total_lines_high += analysis['total_lines']
            print(f"   - {file_name} ({analysis['total_lines']} líneas)")
        
        print(f"\n⚠️  MEDIA PRIORIDAD - Revisar y Eliminar ({len(medium_priority_removal)} archivos):")
        total_lines_medium = 0
        for file_name, analysis in medium_priority_removal:
            total_lines_medium += analysis['total_lines']
            print(f"   - {file_name} ({analysis['total_lines']} líneas)")
        
        print(f"\n🧐 REVISAR CUIDADOSAMENTE ({len(requires_careful_review)} archivos):")
        total_lines_review = 0
        for file_name, analysis in requires_careful_review:
            total_lines_review += analysis['total_lines']
            print(f"   - {file_name} ({analysis['total_lines']} líneas)")
        
        total_removable = total_lines_high + total_lines_medium
        total_all = sum(analysis['total_lines'] for analysis in self.analysis_results.values())
        
        print(f"\n{'='*60}")
        print("RESUMEN DE ELIMINACIÓN POTENCIAL")
        print("="*60)
        print(f"Líneas eliminables inmediatamente: {total_lines_high:,}")
        print(f"Líneas eliminables tras revisión: {total_lines_medium:,}")
        print(f"Total líneas eliminables: {total_removable:,}")
        print(f"Total líneas codebase: {total_all:,}")
        print(f"Reducción potencial: {(total_removable/total_all)*100:.1f}%")
        
        return {
            'high_priority': high_priority_removal,
            'medium_priority': medium_priority_removal,
            'review_required': requires_careful_review,
            'stats': {
                'total_removable_lines': total_removable,
                'total_codebase_lines': total_all,
                'reduction_percentage': (total_removable/total_all)*100
            }
        }
    
    def create_removal_plan(self):
        """Crear plan detallado de eliminación"""
        
        recommendations = self.generate_removal_recommendations()
        
        plan = f"""
# PLAN DE ELIMINACIÓN DE CÓDIGO LEGACY

## Fase 1: Eliminación Inmediata (SEGURA)
**Estimado: {recommendations['stats']['total_removable_lines']:,} líneas eliminables**

"""
        
        for file_name, analysis in recommendations['high_priority']:
            plan += f"### {file_name}\n"
            plan += f"- **Líneas:** {analysis['total_lines']}\n"
            plan += f"- **Complejidad legacy:** {analysis['complexity_score']}\n"
            plan += f"- **Razón:** Alto contenido A*/pathfinding legacy\n"
            plan += f"- **Acción:** Eliminar completamente (reemplazado por sistema mejorado)\n\n"
        
        plan += f"## Fase 2: Eliminación Tras Revisión\n\n"
        
        for file_name, analysis in recommendations['medium_priority']:
            plan += f"### {file_name}\n"
            plan += f"- **Líneas:** {analysis['total_lines']}\n"
            plan += f"- **Acción:** Revisar dependencias, luego eliminar\n\n"
        
        plan += f"""
## Fase 3: Testing de Regresión
- Ejecutar suite completa de tests
- Verificar que simulador funciona correctamente
- Confirmar que no hay funcionalidad perdida

## Beneficios Esperados
- **Reducción de código:** {recommendations['stats']['reduction_percentage']:.1f}%
- **Eliminación de complejidad legacy**
- **Mantenimiento más simple**
- **Codebase más limpio y enfocado**
"""
        
        with open('PLAN_ELIMINACION_LEGACY.md', 'w', encoding='utf-8') as f:
            f.write(plan)
        
        print(f"\n📋 Plan detallado guardado: PLAN_ELIMINACION_LEGACY.md")
        
        return recommendations

def main():
    """Ejecutar análisis completo"""
    print("="*70)
    print("ANALIZADOR DE CÓDIGO LEGACY")
    print("="*70)
    
    analyzer = LegacyAnalyzer()
    recommendations = analyzer.create_removal_plan()
    
    print(f"\n✅ ANÁLISIS COMPLETADO")
    print(f"Revisa el archivo PLAN_ELIMINACION_LEGACY.md para detalles completos")
    
    return analyzer

if __name__ == "__main__":
    analyzer = main()