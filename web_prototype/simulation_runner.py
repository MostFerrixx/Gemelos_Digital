import asyncio
import subprocess
import threading
import os
import sys
import json
import time
from typing import Optional, Dict, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor

class SimulationRunner:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SimulationRunner, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._is_running = False
        self._current_process: Optional[subprocess.Popen] = None
        self._process_lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)
        
        # Configuration
        self.PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.TIMEOUT_SECONDS = 600  # 10 minutes
        self.PYTHON_EXECUTABLE = sys.executable

    def is_running(self) -> bool:
        """Check if a simulation is currently running"""
        return self._is_running

    async def run_simulation_async(self) -> AsyncGenerator[Dict, None]:
        """
        Execute simulation asynchronously and yield log events.
        Enforces singleton execution (only one simulation at a time).
        """
        async with self._process_lock:
            if self._is_running:
                yield {
                    "type": "error", 
                    "message": "System busy: A simulation is already running",
                    "timestamp": time.time()
                }
                return

            self._is_running = True
            
        try:
            yield {
                "type": "status", 
                "status": "starting", 
                "message": "Initializing simulation environment...",
                "timestamp": time.time()
            }

            # Prepare command
            script_path = os.path.join(self.PROJECT_ROOT, "entry_points", "run_generate_replay.py")
            cmd = [self.PYTHON_EXECUTABLE, script_path]
            
            # Start process
            process = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,  # Line buffered
                    cwd=self.PROJECT_ROOT,
                    encoding='utf-8',
                    errors='replace' # Handle potential encoding issues gracefully
                )
            )
            
            self._current_process = process
            
            yield {
                "type": "status", 
                "status": "running", 
                "message": "Simulation process started (PID: {})".format(process.pid),
                "timestamp": time.time()
            }

            # Stream output
            start_time = time.time()
            generated_file = None
            
            # We need to read stdout in a non-blocking way or use a thread
            # Since we are in an async generator, we can use run_in_executor for reading lines
            # But simpler approach for line-by-line streaming from subprocess in asyncio:
            
            while True:
                # Check for timeout
                if time.time() - start_time > self.TIMEOUT_SECONDS:
                    process.terminate()
                    yield {
                        "type": "error", 
                        "message": "Simulation timed out after {} seconds".format(self.TIMEOUT_SECONDS),
                        "timestamp": time.time()
                    }
                    break

                # Read line (non-blocking check)
                # Note: readline() is blocking, so we run it in executor
                line = await asyncio.get_event_loop().run_in_executor(
                    self._executor, 
                    process.stdout.readline
                )
                
                if line:
                    # Clean line
                    clean_line = line.strip()
                    
                    # Try to detect JSONL output file path from logs
                    # Convention: "Exito: Archivos generados en output/" or similar
                    # Or we can look for specific log pattern if added to run_live_simulation
                    # For now, we stream everything
                    
                    yield {
                        "type": "log", 
                        "content": clean_line,
                        "level": "info", # Default level
                        "timestamp": time.time()
                    }
                    
                    # Simple heuristic for file detection if printed to stdout
                    if ".jsonl" in clean_line and "output" in clean_line:
                        # Try to extract path if it looks like a path
                        parts = clean_line.split()
                        for part in parts:
                            if part.endswith(".jsonl") and ("/" in part or "\\" in part):
                                generated_file = part
                                break

                # Check if process finished
                if process.poll() is not None:
                    # Read remaining output
                    rest = await asyncio.get_event_loop().run_in_executor(
                        self._executor, 
                        process.stdout.read
                    )
                    if rest:
                        for l in rest.splitlines():
                            yield {
                                "type": "log", 
                                "content": l.strip(),
                                "level": "info",
                                "timestamp": time.time()
                            }
                    break
            
            return_code = process.returncode
            
            if return_code == 0:
                # If we didn't detect file from logs, try to find the latest one
                if not generated_file:
                    generated_file = self._find_latest_replay()

                yield {
                    "type": "complete",
                    "status": "success",
                    "message": "Simulation completed successfully",
                    "file": generated_file,
                    "timestamp": time.time()
                }
            else:
                yield {
                    "type": "error",
                    "message": f"Simulation failed with exit code {return_code}",
                    "timestamp": time.time()
                }

        except Exception as e:
            yield {
                "type": "error",
                "message": f"Internal error: {str(e)}",
                "timestamp": time.time()
            }
            if self._current_process and self._current_process.poll() is None:
                self._current_process.terminate()
                
        finally:
            self._is_running = False
            self._current_process = None

    def cancel_current_simulation(self):
        """Force cancel the running simulation"""
        if self._current_process and self._current_process.poll() is None:
            self._current_process.terminate()
            # Give it a moment to terminate gracefully
            try:
                self._current_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._current_process.kill()
            
        self._is_running = False

    def _find_latest_replay(self) -> Optional[str]:
        """Find the most recently created replay file in output directory"""
        output_dir = os.path.join(self.PROJECT_ROOT, "output")
        if not os.path.exists(output_dir):
            return None
            
        # Find latest simulation folder
        sim_dirs = [d for d in os.listdir(output_dir) if d.startswith("simulation_")]
        if not sim_dirs:
            return None
            
        latest_sim = max(sim_dirs, key=lambda d: os.path.join(output_dir, d))
        sim_path = os.path.join(output_dir, latest_sim)
        
        # Find replay file in that folder
        for f in os.listdir(sim_path):
            if f.startswith("replay_") and f.endswith(".jsonl"):
                # Return relative path from project root
                return os.path.join("output", latest_sim, f).replace("\\", "/")
                
        return None
