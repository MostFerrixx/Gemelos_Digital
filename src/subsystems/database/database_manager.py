# -*- coding: utf-8 -*-
"""
Database Manager Module - SQLite Connection Manager
Digital Twin Warehouse Simulator

Singleton pattern for managing SQLite connections with optimal settings
for a desktop simulation application.

Author: Digital Twin Warehouse Team
Version: V1.0
"""

import os
import sqlite3
import threading
from typing import Optional
from contextlib import contextmanager


class DatabaseManager:
    """
    Singleton Database Manager for SQLite warehouse database.
    
    Provides optimized connection settings with WAL mode for
    concurrent reads during simulation.
    
    Usage:
        db = DatabaseManager.get_instance()
        with db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM sku_catalog")
    """
    
    _instance: Optional['DatabaseManager'] = None
    _lock = threading.Lock()
    
    # Default database path (relative to project root)
    DEFAULT_DB_NAME = "warehouse.db"
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize DatabaseManager (private - use get_instance()).
        
        Args:
            db_path: Path to SQLite database file. If None, uses default.
        """
        if db_path is None:
            # Default: project root / warehouse.db
            project_root = self._get_project_root()
            db_path = os.path.join(project_root, self.DEFAULT_DB_NAME)
        
        self.db_path = os.path.abspath(db_path)
        self._local = threading.local()
        self._initialized = False
        
        print(f"[DATABASE] Manager initialized with path: {self.db_path}")
    
    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> 'DatabaseManager':
        """
        Get or create the singleton DatabaseManager instance.
        
        Args:
            db_path: Optional path to database (only used on first call)
            
        Returns:
            DatabaseManager singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton (for testing purposes)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close_all()
                cls._instance = None
    
    @staticmethod
    def _get_project_root() -> str:
        """Get project root directory (3 levels up from this file)."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # src/subsystems/database -> go up 3 levels
        return os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    
    def _get_thread_connection(self) -> sqlite3.Connection:
        """Get or create connection for current thread."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = self._create_connection()
        return self._local.connection
    
    def _create_connection(self, readonly: bool = False) -> sqlite3.Connection:
        """
        Create a new optimized SQLite connection.
        
        Args:
            readonly: If True, open in read-only mode
            
        Returns:
            Configured sqlite3.Connection
        """
        if readonly:
            # Read-only URI mode
            uri = f"file:{self.db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        else:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # Apply performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")       # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")     # Faster, still safe
        conn.execute("PRAGMA cache_size=-64000")      # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")      # Temp tables in RAM
        conn.execute("PRAGMA foreign_keys=ON")        # Enforce FK constraints
        
        # Enable dict-like row access
        conn.row_factory = sqlite3.Row
        
        return conn
    
    @contextmanager
    def get_connection(self, readonly: bool = False):
        """
        Context manager for database connections.
        
        For write operations, commits on success, rollbacks on exception.
        
        Args:
            readonly: If True, use read-only connection
            
        Yields:
            sqlite3.Connection
            
        Example:
            with db.get_connection() as conn:
                conn.execute("INSERT INTO ...")
        """
        if readonly:
            # Create fresh read-only connection
            conn = self._create_connection(readonly=True)
            try:
                yield conn
            finally:
                conn.close()
        else:
            # Use thread-local connection for writes
            conn = self._get_thread_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a single SQL statement.
        
        Args:
            sql: SQL statement
            params: Query parameters
            
        Returns:
            sqlite3.Cursor with results
        """
        conn = self._get_thread_connection()
        return conn.execute(sql, params)
    
    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        """
        Execute SQL statement for multiple parameter sets.
        
        Args:
            sql: SQL statement with placeholders
            params_list: List of parameter tuples
            
        Returns:
            sqlite3.Cursor
        """
        conn = self._get_thread_connection()
        return conn.executemany(sql, params_list)
    
    def commit(self):
        """Commit current transaction."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.commit()
    
    def close_all(self):
        """Close all thread-local connections."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    def database_exists(self) -> bool:
        """Check if database file exists."""
        return os.path.exists(self.db_path)
    
    def initialize_schema(self, schema_path: Optional[str] = None):
        """
        Initialize database with schema from SQL file.
        
        Args:
            schema_path: Path to schema.sql file. If None, uses default.
        """
        if schema_path is None:
            schema_path = os.path.join(
                os.path.dirname(__file__), 'schema.sql'
            )
        
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        with self.get_connection() as conn:
            conn.executescript(schema_sql)
        
        self._initialized = True
        print(f"[DATABASE] Schema initialized from: {schema_path}")
    
    def get_schema_version(self) -> int:
        """Get current schema version from database."""
        try:
            with self.get_connection(readonly=True) as conn:
                cursor = conn.execute(
                    "SELECT MAX(version) FROM schema_version"
                )
                result = cursor.fetchone()
                return result[0] if result and result[0] else 0
        except sqlite3.OperationalError:
            return 0
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        stats = {
            'db_path': self.db_path,
            'exists': self.database_exists(),
            'schema_version': 0,
            'sku_count': 0,
            'location_count': 0,
            'inventory_count': 0
        }
        
        if stats['exists']:
            try:
                stats['schema_version'] = self.get_schema_version()
                with self.get_connection(readonly=True) as conn:
                    for table, key in [('sku_catalog', 'sku_count'),
                                       ('locations', 'location_count'),
                                       ('inventory', 'inventory_count')]:
                        try:
                            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                            stats[key] = cursor.fetchone()[0]
                        except sqlite3.OperationalError:
                            pass
            except Exception as e:
                stats['error'] = str(e)
        
        return stats
    
    def __repr__(self):
        return f"DatabaseManager(db_path='{self.db_path}', exists={self.database_exists()})"


# Convenience functions for quick access
def get_db() -> DatabaseManager:
    """Get the singleton DatabaseManager instance."""
    return DatabaseManager.get_instance()


def get_readonly_connection():
    """Get a read-only connection context manager."""
    return get_db().get_connection(readonly=True)


def get_write_connection():
    """Get a write connection context manager."""
    return get_db().get_connection(readonly=False)
