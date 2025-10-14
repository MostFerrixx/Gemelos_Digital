# -*- coding: utf-8 -*-
"""
Script para inspeccionar el contenido de archivos Excel generados por el sistema.
Diagnostica problemas de datos faltantes en modo headless.
"""

import pandas as pd
import os
import sys
from pathlib import Path

def inspect_excel_file(excel_path):
    """
    Inspecciona un archivo Excel y muestra información detallada sobre su contenido.
    """
    print(f"=" * 70)
    print(f"INSPECCION DE ARCHIVO EXCEL: {excel_path}")
    print(f"=" * 70)
    
    if not os.path.exists(excel_path):
        print(f"ERROR: Archivo no encontrado: {excel_path}")
        return False
    
    try:
        # Leer todas las hojas del Excel
        excel_file = pd.ExcelFile(excel_path)
        sheet_names = excel_file.sheet_names
        
        print(f"Hojas encontradas: {len(sheet_names)}")
        for i, sheet in enumerate(sheet_names, 1):
            print(f"  {i}. {sheet}")
        
        print("\n" + "-" * 50)
        
        # Inspeccionar cada hoja
        for sheet_name in sheet_names:
            print(f"\nHOJA: {sheet_name}")
            print("-" * 30)
            
            try:
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                
                print(f"Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
                print(f"Columnas: {list(df.columns)}")
                
                # Mostrar primeras filas
                if not df.empty:
                    print("\nPrimeras 5 filas:")
                    print(df.head().to_string())
                    
                    # Verificar valores nulos
                    null_counts = df.isnull().sum()
                    if null_counts.sum() > 0:
                        print(f"\nValores nulos por columna:")
                        for col, count in null_counts.items():
                            if count > 0:
                                print(f"  {col}: {count} valores nulos")
                    else:
                        print("\nNo hay valores nulos")
                        
                    # Verificar tipos de datos
                    print(f"\nTipos de datos:")
                    for col, dtype in df.dtypes.items():
                        print(f"  {col}: {dtype}")
                        
                else:
                    print("HOJA VACIA - No hay datos")
                    
            except Exception as e:
                print(f"ERROR leyendo hoja {sheet_name}: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERROR general al leer Excel: {e}")
        return False

def find_latest_excel():
    """
    Encuentra el archivo Excel más reciente en el directorio output.
    """
    output_dir = Path("output")
    if not output_dir.exists():
        print("ERROR: Directorio 'output' no encontrado")
        return None
    
    excel_files = list(output_dir.rglob("*.xlsx"))
    if not excel_files:
        print("ERROR: No se encontraron archivos Excel en 'output'")
        return None
    
    # Ordenar por fecha de modificación
    latest_file = max(excel_files, key=lambda f: f.stat().st_mtime)
    return str(latest_file)

def main():
    """
    Función principal del script de inspección.
    """
    print("INSPECTOR DE ARCHIVOS EXCEL - DIAGNOSTICO DE DATOS FALTANTES")
    print("=" * 70)
    
    # Buscar el archivo Excel más reciente
    latest_excel = find_latest_excel()
    if not latest_excel:
        return 1
    
    print(f"Archivo más reciente encontrado: {latest_excel}")
    
    # Inspeccionar el archivo
    success = inspect_excel_file(latest_excel)
    
    if success:
        print("\n" + "=" * 70)
        print("INSPECCION COMPLETADA")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print("INSPECCION FALLIDA")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())