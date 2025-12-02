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
            
            # Prepare environment
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

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
                    errors='replace', # Handle potential encoding issues gracefully
                    env=env
                )
            )
            
            self._current_process = process
            
            yield {
                "type": "status", 
                "status": "running", 
                "message": "Simulation process started (PID: {})".format(process.pid),
                "timestamp": time.time()
            }

            # Stream output with batching
            start_time = time.time()
            generated_file = None
            log_buffer = []
            last_flush_time = time.time()
            BATCH_SIZE = 1000
            FLUSH_INTERVAL = 0.5  # seconds
            
            # Helper to schedule a read
            def read_line_task():
                return process.stdout.readline()

            pending_read = None

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

                # Ensure we have a pending read task
                if pending_read is None:
                    pending_read = asyncio.get_event_loop().run_in_executor(
                        self._executor, 
                        read_line_task
                    )

                # Wait for read OR timeout
                try:
                    # Wait for the EXISTING future
                    line = await asyncio.wait_for(asyncio.shield(pending_read), timeout=0.05)
                    # If we get here, the read completed
                    pending_read = None # Clear so we schedule a new one next time
                except asyncio.TimeoutError:
                    line = None # Read not done yet, keep waiting for same future

                if line:
                    clean_line = line.strip()
                    if clean_line:
                        # Add to buffer
                        log_buffer.append({
                            "content": clean_line,
                            "level": "info"
                        })
                        
                        # File detection logic
                        if ".jsonl" in clean_line and "output" in clean_line:
                            parts = clean_line.split()
                            for part in parts:
                                if part.endswith(".jsonl") and ("/" in part or "\\" in part):
                                    generated_file = part
                                    break
                elif line == '': # EOF - stdout closed
                     break

                # Flush buffer if full or time elapsed
                current_time = time.time()
                if log_buffer and (len(log_buffer) >= BATCH_SIZE or (current_time - last_flush_time) >= FLUSH_INTERVAL):
                    yield {
                        "type": "log_batch",
                        "content": log_buffer,
                        "timestamp": current_time
                    }
                    log_buffer = []
                    last_flush_time = current_time

            # Flush any remaining logs in buffer
            if log_buffer:
                yield {
                    "type": "log_batch",
                    "content": log_buffer,
                    "timestamp": time.time()
                }

            # CRITICAL: Wait for process to fully terminate before reading returncode
            # If we just saw EOF, process might still be alive doing cleanup
            if process.poll() is None:
                # Process still running, wait for it
                await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    process.wait
                )

            
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
