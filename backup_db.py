import sqlite3
import os
from datetime import datetime
from pathlib import Path


def backup_database():
    """Create a backup of the current database"""
    db_path = "inventory.db"
    if not os.path.exists(db_path):
        print("No database file found to backup")
        return None

    # Create backups directory
    backup_dir = "backups"
    Path(backup_dir).mkdir(parents=True, exist_ok=True)

    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"inventory_backup_{timestamp}.db")

    try:
        # Copy the database file
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())

        # Verify the backup
        if verify_backup(backup_path):
            print(f"Database backed up and verified: {backup_path}")
            return backup_path
        else:
            # Remove invalid backup
            os.remove(backup_path)
            print("Backup verification failed")
            return None
    except Exception as e:
        print(f"Backup error: {e}")
        return None


def verify_backup(backup_path):
    """Verify that a backup file is valid"""
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        expected_tables = ['products', 'product_variants', 'sales']
        table_names = [t[0] for t in tables]
        
        for table in expected_tables:
            if table not in table_names:
                conn.close()
                return False
        
        conn.close()
        return True
    except Exception:
        return False


def list_backups():
    """List all available backups"""
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        return []
    
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.startswith("inventory_backup_") and filename.endswith(".db"):
            filepath = os.path.join(backup_dir, filename)
            # Get file size and modification time
            stat = os.stat(filepath)
            backups.append({
                'filename': filename,
                'path': filepath,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
    
    # Sort by creation time, newest first
    backups.sort(key=lambda x: x['created'], reverse=True)
    return backups


def restore_database(backup_path):
    """Restore database from backup"""
    if not os.path.exists(backup_path):
        print(f"Backup file not found: {backup_path}")
        return False

    # Verify backup before restoring
    if not verify_backup(backup_path):
        print(f"Invalid backup file: {backup_path}")
        return False

    db_path = "inventory.db"
    try:
        with open(backup_path, 'rb') as src, open(db_path, 'wb') as dst:
            dst.write(src.read())

        print(f"Database restored from: {backup_path}")
        return True
    except Exception as e:
        print(f"Restore error: {e}")
        return False


def restore_latest_backup():
    """Restore the most recent backup"""
    backups = list_backups()
    if not backups:
        print("No backups available")
        return False
    
    latest_backup = backups[0]
    return restore_database(latest_backup['path'])


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "backup":
            backup_database()
        elif command == "list":
            backups = list_backups()
            if backups:
                print("Available backups:")
                for b in backups:
                    print(f"  {b['filename']} - {b['created']} - {b['size']} bytes")
            else:
                print("No backups found")
        elif command == "restore" and len(sys.argv) > 2:
            restore_database(sys.argv[2])
        elif command == "restore-latest":
            restore_latest_backup()
        else:
            print("Usage:")
            print("  python backup_db.py backup      - Create a backup")
            print("  python backup_db.py list        - List all backups")
            print("  python backup_db.py restore <file>  - Restore from backup")
            print("  python backup_db.py restore-latest - Restore latest backup")
    else:
        # Default: create a backup
        backup_database()

