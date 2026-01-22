import sqlite3
import os


# For local development, use current directory
# For production (Render), use persistent disk if available
if os.environ.get('RENDER'):
    # Render environment - try to use persistent disk
    disk_path = os.environ.get('RENDER_DISK_PATH')
    if disk_path:
        DB_DIR = disk_path
    else:
        # Fallback - but this will be ephemeral on Render free tier
        DB_DIR = '/tmp'
        print("WARNING: Using ephemeral storage. Data will be lost on restart!")
else:
    # Local development
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
	name TEXT,
	category TEXT,
	price REAL,
	image TEXT,
	date_received TEXT,
	stock_received INTEGER,
	expiry_date TEXT
	)
	""")

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS sales (
	id TEXT PRIMARY KEY,
	product_id TEXT,
	date_sold TEXT,
	quantity_sold INTEGER,
	price REAL,
	FOREIGN KEY (product_id) REFERENCES products (id)
	)
	""")

	conn.commit()
	conn.close()

