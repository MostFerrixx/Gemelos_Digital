# Makefile para Gemelo Digital - Comandos Convenientes
# Mantiene organizacion clara con comandos cortos

.PHONY: help sim sim-visual replay config test clean

# Comando por defecto: mostrar ayuda
help:
	@echo "=== GEMELO DIGITAL - COMANDOS DISPONIBLES ==="
	@echo ""
	@echo "  make sim          - Ejecutar simulacion headless (sin UI)"
	@echo "  make sim-visual   - Ejecutar simulacion con interfaz grafica"
	@echo "  make replay FILE=<archivo.jsonl> - Ver replay de simulacion"
	@echo "  make config       - Abrir configurador de simulacion"
	@echo "  make test         - Ejecutar test rapido (3 ordenes)"
	@echo "  make clean        - Limpiar archivos temporales"
	@echo ""
	@echo "Ejemplos:"
	@echo "  make sim"
	@echo "  make replay FILE=output/simulation_20250115_120000/replay_events_20250115_120000.jsonl"
	@echo ""

# Simulacion headless (sin UI)
sim:
	@echo "Ejecutando simulacion headless..."
	python entry_points/run_live_simulation.py --headless

# Simulacion con interfaz grafica
sim-visual:
	@echo "Ejecutando simulacion con interfaz grafica..."
	python entry_points/run_live_simulation.py

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

# Test rapido
test:
	@echo "Ejecutando test rapido (3 ordenes)..."
	python test_quick_jsonl.py

# Limpiar archivos temporales
clean:
	@echo "Limpiando archivos temporales..."
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist src\__pycache__ rmdir /s /q src\__pycache__
	@if exist *.pyc del /q *.pyc
	@echo "Limpieza completada"

