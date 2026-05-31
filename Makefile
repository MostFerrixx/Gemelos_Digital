# Makefile para Gemelo Digital - Comandos Convenientes
# NOTA: las GUI de escritorio (visualizador Pygame, dashboard PyQt6, configurador
# Tkinter) fueron deprecadas y archivadas en _legacy/gui_escritorio/.
# La GUI vigente es la web (web_prototype, http://localhost:8000).

.PHONY: help sim web clean

help:
	@echo "=== GEMELO DIGITAL - COMANDOS DISPONIBLES ==="
	@echo ""
	@echo "  make sim    - Generar replay (.jsonl) + reportes Excel/heatmap (headless)"
	@echo "  make web    - Iniciar la GUI web (FastAPI, http://localhost:8000)"
	@echo "  make clean  - Limpiar archivos temporales"
	@echo ""

# Simulacion headless (genera replay .jsonl + reportes)
sim:
	@echo "Generando archivo de replay..."
	python entry_points/run_generate_replay.py

# GUI web (configurador + runner + viewer en el navegador)
web:
	@echo "Iniciando servidor web en http://localhost:8000 ..."
	python server_manager.py start --browser

# Limpiar archivos temporales
clean:
	@echo "Limpiando archivos temporales..."
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist src\__pycache__ rmdir /s /q src\__pycache__
	@if exist *.pyc del /q *.pyc
	@echo "Limpieza completada"
