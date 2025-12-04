#!/usr/bin/env python3
"""
Server Manager for Gemelos Digital
Provides advanced server management functionality
"""

import os
import sys
import time
import signal
import socket
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
PROJECT_ROOT = Path(__file__).parent
SERVER_SCRIPT = PROJECT_ROOT / "web_prototype" / "server.py"
PID_FILE = PROJECT_ROOT / "server.pid"
LOG_DIR = PROJECT_ROOT / "logs"
SERVER_LOG = LOG_DIR / "server.log"
ERROR_LOG = LOG_DIR / "server_errors.log"
SERVER_PORT = 8000
SERVER_HOST = "localhost"


class ServerManager:
    """Manages the web server lifecycle"""
    
    def __init__(self):
        self.pid_file = PID_FILE
        self.log_dir = LOG_DIR
        self.server_log = SERVER_LOG
        self.error_log = ERROR_LOG
        
    def is_port_available(self, port):
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def get_pid(self):
        """Get the PID from the PID file"""
        if not self.pid_file.exists():
            return None
        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return None
    
    def is_running(self):
        """Check if the server is running"""
        pid = self.get_pid()
        if pid is None:
            return False
        
        # Check if process exists
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def start(self, open_browser=False):
        """Start the server"""
        print("="*70)
        print("  GEMELOS DIGITAL - Iniciar Servidor Web")
        print("="*70)
        print()
        
        # Check if already running
        if self.is_running():
            pid = self.get_pid()
            print(f"[ADVERTENCIA] El servidor ya esta ejecutandose (PID: {pid})")
            print(f"URL: http://{SERVER_HOST}:{SERVER_PORT}")
            return False
        
        # Check if port is available
        if not self.is_port_available(SERVER_PORT):
            print(f"[ERROR] El puerto {SERVER_PORT} ya esta en uso")
            print("Detén el proceso que esta usando el puerto o cambia el puerto del servidor")
            return False
        
        # Create log directory
        self.log_dir.mkdir(exist_ok=True)
        
        # Start server
        print(f"[INFO] Iniciando servidor en segundo plano...")
        print(f"[INFO] Script: {SERVER_SCRIPT}")
        print(f"[INFO] Logs: {self.server_log}")
        print()
        
        try:
            # Open log files
            log_f = open(self.server_log, 'a', encoding='utf-8')
            err_f = open(self.error_log, 'a', encoding='utf-8')
            
            # Log startup time
            log_f.write(f"\n{'='*70}\n")
            log_f.write(f"Server started at {datetime.now()}\n")
            log_f.write(f"{'='*70}\n\n")
            log_f.flush()
            
            # Start process (platform-specific)
            if sys.platform == 'win32':
                # Windows: use pythonw.exe for no console
                python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
                if not os.path.exists(python_exe):
                    python_exe = sys.executable
                
                process = subprocess.Popen(
                    [python_exe, str(SERVER_SCRIPT)],
                    stdout=log_f,
                    stderr=err_f,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            else:
                # Unix/Linux/Mac
                process = subprocess.Popen(
                    [sys.executable, str(SERVER_SCRIPT)],
                    stdout=log_f,
                    stderr=err_f,
                    start_new_session=True
                )
            
            # Save PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # Wait a moment to ensure startup
            time.sleep(2)
            
            # Verify it started
            if self.is_running():
                print(f"[EXITO] Servidor iniciado exitosamente!")
                print()
                print(f"  PID:        {process.pid}")
                print(f"  URL:        http://{SERVER_HOST}:{SERVER_PORT}")
                print(f"  Config:     http://{SERVER_HOST}:{SERVER_PORT}/web_configurator/")
                print(f"  Logs:       {self.server_log}")
                print(f"  Errores:    {self.error_log}")
                print()
                
                if open_browser:
                    import webbrowser
                    webbrowser.open(f"http://{SERVER_HOST}:{SERVER_PORT}/web_configurator/")
                    print("[INFO] Navegador abierto")
                
                return True
            else:
                print("[ERROR] El servidor se detuvo inesperadamente")
                print(f"Verifica los logs en: {self.error_log}")
                return False
                
        except Exception as e:
            print(f"[ERROR] No se pudo iniciar el servidor: {e}")
            return False
    
    def stop(self):
        """Stop the server"""
        print("="*70)
        print("  GEMELOS DIGITAL - Detener Servidor Web")
        print("="*70)
        print()
        
        pid = self.get_pid()
        if pid is None:
            print("[INFO] No hay servidor ejecutandose")
            return True
        
        if not self.is_running():
            print(f"[ADVERTENCIA] El proceso PID {pid} no esta ejecutandose")
            print("Limpiando archivo PID...")
            self.pid_file.unlink(missing_ok=True)
            return True
        
        print(f"[INFO] Deteniendo servidor (PID: {pid})...")
        
        try:
            # Send termination signal
            if sys.platform == 'win32':
                # Windows: use taskkill
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                             capture_output=True, check=False)
            else:
                # Unix: send SIGTERM
                os.kill(pid, signal.SIGTERM)
                
                # Wait for graceful shutdown
                for _ in range(10):
                    if not self.is_running():
                        break
                    time.sleep(0.5)
                
                # Force kill if still running
                if self.is_running():
                    os.kill(pid, signal.SIGKILL)
            
            # Clean up PID file
            self.pid_file.unlink(missing_ok=True)
            
            print("[EXITO] Servidor detenido exitosamente")
            return True
            
        except Exception as e:
            print(f"[ERROR] No se pudo detener el servidor: {e}")
            return False
    
    def restart(self, open_browser=False):
        """Restart the server"""
        print("="*70)
        print("  GEMELOS DIGITAL - Reiniciar Servidor Web")
        print("="*70)
        print()
        
        self.stop()
        print()
        print("[INFO] Esperando 2 segundos...")
        time.sleep(2)
        print()
        return self.start(open_browser)
    
    def status(self):
        """Show server status"""
        print("="*70)
        print("  GEMELOS DIGITAL - Estado del Servidor Web")
        print("="*70)
        print()
        
        pid = self.get_pid()
        
        if pid is None:
            print("[ESTADO] DETENIDO")
            print()
            print("El servidor no esta ejecutandose.")
            return False
        
        if not self.is_running():
            print("[ESTADO] ERROR - Proceso no encontrado")
            print()
            print(f"El archivo PID existe pero el proceso {pid} no esta ejecutandose.")
            print("Esto puede ocurrir si el servidor se cerro inesperadamente.")
            return False
        
        print("[ESTADO] EJECUTANDOSE")
        print()
        print(f"  PID:         {pid}")
        print(f"  URL:         http://{SERVER_HOST}:{SERVER_PORT}")
        print(f"  Config URL:  http://{SERVER_HOST}:{SERVER_PORT}/web_configurator/")
        
        # Get process info
        try:
            import psutil
            process = psutil.Process(pid)
            print(f"  CPU:         {process.cpu_percent(interval=0.1):.1f}%")
            print(f"  Memoria:     {process.memory_info().rss / 1024 / 1024:.1f} MB")
            print(f"  Iniciado:    {datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S')}")
        except ImportError:
            pass
        
        print()
        return True
    
    def logs(self, lines=20, follow=False):
        """Show server logs"""
        if not self.server_log.exists():
            print("[INFO] No hay logs disponibles")
            return
        
        if follow:
            # Tail -f equivalent
            print(f"[INFO] Siguiendo logs (Ctrl+C para salir)...")
            print("="*70)
            try:
                with open(self.server_log, 'r', encoding='utf-8') as f:
                    # Go to end
                    f.seek(0, 2)
                    while True:
                        line = f.readline()
                        if line:
                            print(line, end='')
                        else:
                            time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n[INFO] Detenido")
        else:
            # Show last N lines
            with open(self.server_log, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                for line in all_lines[-lines:]:
                    print(line, end='')


def main():
    parser = argparse.ArgumentParser(
        description='Gemelos Digital - Server Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python server_manager.py start           Iniciar servidor
  python server_manager.py start --browser Iniciar y abrir navegador
  python server_manager.py stop            Detener servidor
  python server_manager.py restart         Reiniciar servidor
  python server_manager.py status          Ver estado
  python server_manager.py logs            Ver ultimas 20 lineas de log
  python server_manager.py logs -n 50      Ver ultimas 50 lineas de log
  python server_manager.py logs --follow   Seguir logs en tiempo real
        """
    )
    
    parser.add_argument('command', 
                       choices=['start', 'stop', 'restart', 'status', 'logs'],
                       help='Comando a ejecutar')
    parser.add_argument('--browser', '-b', action='store_true',
                       help='Abrir navegador automaticamente (solo para start/restart)')
    parser.add_argument('--lines', '-n', type=int, default=20,
                       help='Numero de lineas a mostrar (solo para logs)')
    parser.add_argument('--follow', '-f', action='store_true',
                       help='Seguir logs en tiempo real (solo para logs)')
    
    args = parser.parse_args()
    
    manager = ServerManager()
    
    if args.command == 'start':
        success = manager.start(open_browser=args.browser)
        sys.exit(0 if success else 1)
    
    elif args.command == 'stop':
        success = manager.stop()
        sys.exit(0 if success else 1)
    
    elif args.command == 'restart':
        success = manager.restart(open_browser=args.browser)
        sys.exit(0 if success else 1)
    
    elif args.command == 'status':
        success = manager.status()
        sys.exit(0 if success else 1)
    
    elif args.command == 'logs':
        manager.logs(lines=args.lines, follow=args.follow)
        sys.exit(0)


if __name__ == '__main__':
    main()
