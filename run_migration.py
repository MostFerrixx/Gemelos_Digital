#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Migration Script
Digital Twin Warehouse Simulator

Run this script to create/reset the SQLite database and import
data from Warehouse_Logic.xlsx.

Usage:
    python run_migration.py
    python run_migration.py --excel path/to/file.xlsx
    python run_migration.py --db path/to/warehouse.db
    python run_migration.py --keep-existing  # Don't clear existing data

Author: Digital Twin Warehouse Team
Version: V1.0
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from src.subsystems.database.database_manager import DatabaseManager
from src.subsystems.database.importer import ExcelImporter, ImportResult


def find_excel_file() -> str:
    """Find the default Warehouse_Logic.xlsx file."""
    # Fuente unica de verdad = RAIZ. El arbol data/ fue una migracion abandonada
    # y su copia divergente esta archivada en _legacy/data/ (ver _legacy/README.md).
    possible_paths = [
        PROJECT_ROOT / "layouts" / "Warehouse_Logic.xlsx",
        PROJECT_ROOT / "Warehouse_Logic.xlsx",
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    
    return str(possible_paths[0])  # Return first as default


def run_migration(excel_path: str, db_path: str, 
                  clear_existing: bool = True) -> bool:
    """
    Run the database migration.
    
    Args:
        excel_path: Path to Excel file
        db_path: Path to SQLite database
        clear_existing: Whether to clear existing data
        
    Returns:
        True if successful, False otherwise
    """
    print("\n" + "=" * 60)
    print("  WAREHOUSE DATABASE MIGRATION")
    print("  Digital Twin Warehouse Simulator")
    print("=" * 60)
    print(f"\n  Excel source: {excel_path}")
    print(f"  Database target: {db_path}")
    print(f"  Clear existing: {clear_existing}")
    print("\n" + "-" * 60 + "\n")
    
    # Validate Excel exists
    if not os.path.exists(excel_path):
        print(f"[ERROR] Excel file not found: {excel_path}")
        print("\nPlease ensure Warehouse_Logic.xlsx exists at:")
        print("  - layouts/Warehouse_Logic.xlsx  (fuente unica de verdad)")
        return False
    
    # Initialize database manager
    DatabaseManager.reset_instance()
    db = DatabaseManager.get_instance(db_path)
    
    # Initialize schema
    print("[MIGRATION] Step 1: Initializing database schema...")
    try:
        db.initialize_schema()
        print("[MIGRATION] Schema initialized successfully.\n")
    except Exception as e:
        print(f"[ERROR] Failed to initialize schema: {e}")
        return False
    
    # Import data
    print("[MIGRATION] Step 2: Importing data from Excel...")
    importer = ExcelImporter(db)
    result = importer.import_from_excel(excel_path, clear_existing)
    
    if not result.success:
        print("\n[ERROR] Migration failed. Errors:")
        for error in result.errors:
            print(f"  - {error}")
        return False
    
    # Verify data
    print("[MIGRATION] Step 3: Verifying imported data...")
    stats = db.get_stats()
    print(f"\n  Database Statistics:")
    print(f"    - Schema version: {stats['schema_version']}")
    print(f"    - SKUs: {stats['sku_count']}")
    print(f"    - Locations: {stats['location_count']}")
    print(f"    - Inventory records: {stats['inventory_count']}")
    
    # Show sample data
    print("\n[MIGRATION] Step 4: Sample data verification...")
    with db.get_connection(readonly=True) as conn:
        # Sample SKUs
        cursor = conn.execute("SELECT sku_code FROM sku_catalog LIMIT 5")
        skus = [row[0] for row in cursor.fetchall()]
        print(f"  Sample SKUs: {skus}")
        
        # Sample locations
        cursor = conn.execute(
            "SELECT location_id, pick_sequence, work_area FROM locations LIMIT 5"
        )
        locations = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
        print(f"  Sample Locations: {locations}")
        
        # Sample inventory
        cursor = conn.execute("""
            SELECT location_id, sku_code, qty_available 
            FROM inventory LIMIT 5
        """)
        inventory = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
        print(f"  Sample Inventory: {inventory}")
    
    print("\n" + "=" * 60)
    print("  MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"\n  Database ready at: {db_path}")
    print(f"  Total records imported: {result.skus_imported + result.locations_imported + result.inventory_imported}")
    if result.warnings:
        print(f"  Warnings: {len(result.warnings)}")
    print()
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate warehouse data from Excel to SQLite"
    )
    parser.add_argument(
        '--excel', '-e',
        default=None,
        help="Path to Warehouse_Logic.xlsx (default: layouts/Warehouse_Logic.xlsx)"
    )
    parser.add_argument(
        '--db', '-d',
        default=None,
        help="Path to SQLite database (default: warehouse.db in project root)"
    )
    parser.add_argument(
        '--keep-existing', '-k',
        action='store_true',
        help="Don't clear existing data before import"
    )
    
    args = parser.parse_args()
    
    # Determine paths
    excel_path = args.excel or find_excel_file()
    db_path = args.db or str(PROJECT_ROOT / "warehouse.db")
    clear_existing = not args.keep_existing
    
    # Run migration
    success = run_migration(excel_path, db_path, clear_existing)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
