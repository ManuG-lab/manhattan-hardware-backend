import sqlite3
import os
from datetime import datetime

def backup_database():
    """Create a backup of the current database"""
    db_path = "inventory.db"
    if not os.path.exists(db_path):
        print("No database file found to backup")
        return

    # Create backups directory
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)

    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"inventory_backup_{timestamp}.db")

    # Copy the database file
    with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
        dst.write(src.read())

    print(f"Database backed up to: {backup_path}")
    return backup_path

def restore_database(backup_path):
    """Restore database from backup"""
    if not os.path.exists(backup_path):
        print(f"Backup file not found: {backup_path}")
        return False

    db_path = "inventory.db"
    with open(backup_path, 'rb') as src, open(db_path, 'wb') as dst:
        dst.write(src.read())

    print(f"Database restored from: {backup_path}")
    return True

if __name__ == "__main__":
    backup_database()