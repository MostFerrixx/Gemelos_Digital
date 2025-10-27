# Makefile para Gemelo Digital - Comandos Convenientes
# Mantiene organizacion clara con comandos cortos

.PHONY: help sim replay config clean

# Comando por defecto: mostrar ayuda
help:
	@echo "=== GEMELO DIGITAL - COMANDOS DISPONIBLES ==="
	@echo ""
	@echo "  make sim          - Generar archivo de replay para visualizacion"
	@echo "  make replay FILE=<archivo.jsonl> - Ver replay de simulacion"
	@echo "  make config       - Abrir configurador de simulacion"
	@echo "  make clean        - Limpiar archivos temporales"
	@echo ""
	@echo "Ejemplos:"
	@echo "  make sim"
	@echo "  make replay FILE=output/simulation_20250115_120000/replay_events_20250115_120000.jsonl"
	@echo ""

# Simulacion (genera replay)
sim:
	@echo "Generando archivo de replay..."
	python entry_points/run_generate_replay.py

# Nota: Para visualizar, usar replay:
#   make replay FILE=output/simulation_*/replay_*.jsonl

# Replay viewer
replay:
ifndef FILE
	@echo "Error: Debes especificar FILE=<archivo.jsonl>"
	@echo "Ejemplo: make replay FILE=output/simulation_*/replay_events_*.jsonl"
	@exit 1
endif
	@echo "Ejecutando replay viewer..."
	python entry_points/run_replay_viewer.py $(FILE)

# Configurador
config:
	@echo "Abriendo configurador..."
	python configurator.py

# Limpiar archivos temporales
clean:
	@echo "Limpiando archivos temporales..."
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist src\__pycache__ rmdir /s /q src\__pycache__
	@if exist *.pyc del /q *.pyc
	@echo "Limpieza completada"

