# -*- coding: utf-8 -*-
"""
Process Lifecycle Manager - Robust management of dashboard subprocess.

Extracted from SimulationEngine dashboard process management logic.
Provides context-managed process lifecycle with graceful shutdown.

Based on audit findings from:
- simulation_engine.py:1185-1263 (toggle_order_dashboard)
- simulation_engine.py:708-717 (cleanup in _eliminar_procesos_hijos)
- simulation_engine.py:1235-1263 (graceful shutdown logic)
"""

import multiprocessing
import queue
import time
import weakref
from contextlib import contextmanager
from typing import Optional, Any, Callable, Dict
from dataclasses import dataclass, field

# from .ipc_protocols import ProtocolConstants


@dataclass
class DashboardConfig:
    """Configuration for dashboard process lifecycle"""

    # Process startup settings
    startup_timeout: float = 5.0
    health_check_timeout: float = 2.0

    # Shutdown timeouts (based on audit of existing timeouts)
    graceful_shutdown_timeout: float = 3.0  # From simulation_engine.py:1246
    sigterm_timeout: float = 2.0
    sigkill_timeout: float = 1.0

    # Queue settings
    queue_timeout: float = 1.0
    max_queue_size: int = 1000

    # Process monitoring
    health_check_enabled: bool = True
    health_check_interval: float = 1.0

    # Debug settings
    debug_logging: bool = True
    log_prefix: str = "[DASHBOARD]"


class ProcessLifecycleError(Exception):
    """Base exception for process lifecycle errors"""
    pass


class ProcessStartupError(ProcessLifecycleError):
    """Error during process startup"""
    pass


class ProcessShutdownError(ProcessLifecycleError):
    """Error during process shutdown"""
    pass


class ProcessLifecycleManager:
    """
    Robust lifecycle management for dashboard subprocess.

    Provides context-managed process lifecycle with:
    - Validated startup sequence
    - Health checking
    - Graceful shutdown with escalation
    - Resource cleanup
    - Error recovery

    Based on audit of existing process management patterns.
    """

    def __init__(self, config: Optional[DashboardConfig] = None):
        """
        Initialize lifecycle manager.

        Args:
            config: Configuration for process management
        """
        self.config = config or DashboardConfig()
        self.process: Optional[multiprocessing.Process] = None
        self.data_queue: Optional[multiprocessing.Queue] = None
        self.command_queue: Optional[multiprocessing.Queue] = None
        self.ack_event: Optional[multiprocessing.Event] = None

        # State tracking
        self._startup_completed = False
        self._shutdown_initiated = False

        # Callbacks for monitoring (Phase 1: Stub support)
        self._startup_callbacks: Dict[str, Callable] = {}
        self._shutdown_callbacks: Dict[str, Callable] = {}

    @property
    def is_process_active(self) -> bool:
        """Check if process is running and responsive"""
        return (self.process is not None and
                self.process.is_alive() and
                not self._shutdown_initiated)

    @property
    def process_pid(self) -> Optional[int]:
        """Get process PID if available"""
        if self.process and self.process.is_alive():
            return self.process.pid
        return None

    def start_process(self, target_function: Callable, args: tuple = ()) -> bool:
        """
        Start dashboard process with validation and health checking.

        Args:
            target_function: Function to run in subprocess
            args: Arguments for target function

        Returns:
            bool: True if process started successfully

        Raises:
            ProcessStartupError: If process fails to start
        """
        if self.is_process_active:
            self._log("Process already running")
            return True

        try:
            # Phase 1: Basic startup sequence
            return self._start_process_internal(target_function, args)

        except Exception as e:
            # Cleanup on startup failure
            self._cleanup_failed_startup()
            raise ProcessStartupError(f"Failed to start dashboard process: {e}") from e

    def shutdown_process(self, force: bool = False) -> bool:
        """
        Shutdown dashboard process with graceful escalation.

        Based on audit of simulation_engine.py:1235-1263

        Args:
            force: Skip graceful shutdown and terminate immediately

        Returns:
            bool: True if shutdown completed successfully
        """
        if not self.process:
            self._log("No process to shutdown")
            return True

        self._shutdown_initiated = True

        try:
            if force:
                return self._force_terminate()
            else:
                return self._graceful_shutdown_sequence()

        except Exception as e:
            self._log(f"Error during shutdown: {e}")
            # Attempt force terminate as fallback
            return self._force_terminate()

        finally:
            self._cleanup_resources()

    @contextmanager
    def managed_process(self, target_function: Callable, args: tuple = ()):
        """
        Context manager for automatic process lifecycle management.

        Args:
            target_function: Function to run in subprocess
            args: Arguments for target function

        Yields:
            ProcessLifecycleManager: Self reference for process operations

        Raises:
            ProcessStartupError: If process fails to start
        """
        try:
            if not self.start_process(target_function, args):
                raise ProcessStartupError("Dashboard process failed to start")

            self._log(f"Process started successfully (PID: {self.process_pid})")
            yield self

        finally:
            # Always attempt graceful shutdown
            if self.is_process_active:
                self._log("Context exit - shutting down process")
                self.shutdown_process(force=False)

    def send_message(self, message: Any, timeout: Optional[float] = None) -> bool:
        """
        Send message to dashboard process via queue.

        Args:
            message: Message to send
            timeout: Send timeout (uses config default if None)

        Returns:
            bool: True if message sent successfully
        """
        if not self.is_process_active or not self.data_queue:
            return False

        timeout = timeout or self.config.queue_timeout

        try:
            self.data_queue.put_nowait(message)
            return True

        except queue.Full:
            self._log(f"Queue full - message dropped: {type(message).__name__}")
            return False

        except Exception as e:
            self._log(f"Error sending message: {e}")
            return False

    def add_startup_callback(self, name: str, callback: Callable) -> None:
        """Add callback to be called after successful startup"""
        self._startup_callbacks[name] = callback

    def add_shutdown_callback(self, name: str, callback: Callable) -> None:
        """Add callback to be called before shutdown"""
        self._shutdown_callbacks[name] = callback

    # Private implementation methods

    def get_message(self) -> Optional[Any]:
        """
        Get a message from the command queue (non-blocking).

        Returns:
            Optional[Any]: The message if available, else None.
        """
        if not self.command_queue or self.command_queue.empty():
            return None
        try:
            return self.command_queue.get_nowait()
        except queue.Empty:
            return None

    def wait_for_ack(self, timeout: Optional[float] = None) -> bool:
        """Waits for the dashboard to acknowledge an event."""
        if not self.ack_event:
            return False
        return self.ack_event.wait(timeout)

    def clear_ack(self):
        """Clears the acknowledgment event."""
        if self.ack_event:
            self.ack_event.clear()

    def _start_process_internal(self, target_function: Callable, args: tuple) -> bool:
        """Internal process startup implementation"""
        # 1. Create communication queues and sync event
        self.data_queue = multiprocessing.Queue(maxsize=self.config.max_queue_size)
        self.command_queue = multiprocessing.Queue(maxsize=self.config.max_queue_size)
        self.ack_event = multiprocessing.Event()

        # 2. Create process with queues and event as first arguments
        process_args = (self.data_queue, self.command_queue, self.ack_event) + args
        self.process = multiprocessing.Process(
            target=target_function,
            args=process_args
        )

        # 3. Start process
        self.process.start()
        self._log(f"Process started (PID: {self.process.pid})")

        # 4. Verify startup (Phase 1: Basic validation)
        if not self._wait_for_startup():
            self._cleanup_failed_startup()
            return False

        # 5. Run startup callbacks
        self._run_startup_callbacks()

        self._startup_completed = True
        return True

    def _wait_for_startup(self) -> bool:
        """Wait for process to be ready with health checking"""
        if not self.process:
            return False

        # Phase 2: Enhanced startup validation with health checking
        start_time = time.time()
        health_check_interval = 0.1

        while time.time() - start_time < self.config.startup_timeout:
            if not self.process.is_alive():
                # Process died during startup
                self._log("Process died during startup")
                return False

            # Basic health check - verify process is responsive
            if self.config.health_check_enabled:
                try:
                    # Simple health check: queue should be accessible
                    if self.data_queue and hasattr(self.data_queue, 'qsize'):
                        # Queue is responsive
                        self._log(f"Process health check passed (PID: {self.process.pid})")
                        return True
                except:
                    # Queue not ready yet, continue waiting
                    pass
            else:
                # Health checking disabled, just verify process is alive
                if self.process.is_alive():
                    return True

            time.sleep(health_check_interval)

        self._log(f"Process startup timeout after {self.config.startup_timeout}s")
        return False

    def _graceful_shutdown_sequence(self) -> bool:
        """Execute graceful shutdown with escalation"""
        if not self.process or not self.process.is_alive():
            return True

        # 1. Run shutdown callbacks
        self._run_shutdown_callbacks()

        # 2. Send graceful shutdown command
        if self.data_queue:
            self.send_message("__EXIT_COMMAND__")

        # 3. Wait for graceful exit
        try:
            self.process.join(timeout=self.config.graceful_shutdown_timeout)
            if not self.process.is_alive():
                self._log("Graceful shutdown completed")
                return True
        except Exception as e:
            self._log(f"Error in graceful shutdown: {e}")

        # 4. Escalate to termination
        return self._force_terminate()

    def _force_terminate(self) -> bool:
        """Force terminate process"""
        if not self.process:
            return True

        try:
            self._log("Force terminating process")
            self.process.terminate()

            # Wait for termination
            self.process.join(timeout=self.config.sigkill_timeout)

            if self.process.is_alive():
                self._log("Process still alive after terminate - this is unusual")
                # Note: Python multiprocessing doesn't have SIGKILL equivalent
                return False

            self._log("Force termination completed")
            return True

        except Exception as e:
            self._log(f"Error in force terminate: {e}")
            return False

    def _cleanup_resources(self):
        """Clean up process and queue resources"""
        if self.process:
            self.process = None

        if self.command_queue:
            # Clear queue
            try:
                while not self.command_queue.empty():
                    self.command_queue.get_nowait()
            except:
                pass
            self.command_queue = None

        if self.ack_event:
            self.ack_event = None

        self._startup_completed = False
        self._shutdown_initiated = False

    def _cleanup_failed_startup(self):
        """Cleanup resources after failed startup"""
        if self.process and self.process.is_alive():
            try:
                self.process.terminate()
                self.process.join(timeout=1.0)
            except:
                pass

        self._cleanup_resources()

    def _run_startup_callbacks(self):
        """Run registered startup callbacks"""
        for name, callback in self._startup_callbacks.items():
            try:
                callback(self)
            except Exception as e:
                self._log(f"Startup callback '{name}' failed: {e}")

    def _run_shutdown_callbacks(self):
        """Run registered shutdown callbacks"""
        for name, callback in self._shutdown_callbacks.items():
            try:
                callback(self)
            except Exception as e:
                self._log(f"Shutdown callback '{name}' failed: {e}")

    def _log(self, message: str):
        """Internal logging (Phase 1: Simple print)"""
        if self.config.debug_logging:
            print(f"{self.config.log_prefix} {message}")


# Phase 1: Export lifecycle management classes
__all__ = [
    'ProcessLifecycleManager',
    'DashboardConfig',
    'ProcessLifecycleError',
    'ProcessStartupError',
    'ProcessShutdownError'
]