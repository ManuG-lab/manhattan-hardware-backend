import sqlite3
import os

if os.environ.get('RENDER'):
    disk_path = os.environ.get('RENDER_DISK_PATH')
    if disk_path:
        DB_DIR = disk_path
    else:
        DB_DIR = '/tmp'
        print("WARNING: Using ephemeral storage. Data will be lost on restart!")
else:
    DB_DIR = os.getcwd()

DB_NAME = os.path.join(DB_DIR, "inventory.db")


def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT,
        image TEXT,
        date_received TEXT,
        expiry_date TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_variants (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        size TEXT NOT NULL,
        price REAL NOT NULL,
        stock_received INTEGER DEFAULT 0,
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id TEXT PRIMARY KEY,
        variant_id TEXT NOT NULL,
        date_sold TEXT,
        quantity_sold INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY (variant_id) REFERENCES product_variants (id)
    )
    """)

    conn.commit()
    conn.close()
