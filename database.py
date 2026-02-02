import sqlite3
import os

# Database configuration
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
    """Get a database connection with proper settings"""
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        raise


def check_connection():
    """Check if database connection is healthy"""
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception:
        return False


def create_tables():
    """Create all required tables if they don't exist"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Create products table
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

        # Create product_variants table
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

        # Create sales table
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

        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_variants_product_id 
            ON product_variants(product_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sales_variant_id 
            ON sales(variant_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sales_date_sold 
            ON sales(date_sold)
        """)

        conn.commit()
        print("Database tables created/verified successfully")
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")
        raise
    finally:
        if conn:
            conn.close()

