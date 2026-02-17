import sqlite3
import os

# Database configuration
# Priority for DB location:
# 1. Explicit DB_PATH environment variable (absolute path or directory)
# 2. If running on Render, use RENDER_DISK_PATH
# 3. Fallback to a persistent directory under the user's home: ~/.bussines_data
DB_PATH = os.environ.get('DB_PATH')
if DB_PATH:
    # If a directory was provided, place the DB file inside it
    if os.path.isdir(DB_PATH):
        DB_DIR = DB_PATH
        DB_NAME = os.path.join(DB_DIR, "inventory.db")
    else:
        # if a file path was provided, use it directly
        DB_NAME = DB_PATH
        DB_DIR = os.path.dirname(DB_NAME) or os.getcwd()
elif os.environ.get('RENDER'):
    disk_path = os.environ.get('RENDER_DISK_PATH')
    if disk_path:
        DB_DIR = disk_path
    else:
        DB_DIR = '/tmp'
        print("WARNING: Using ephemeral storage. Data will be lost on restart!")
    DB_NAME = os.path.join(DB_DIR, "inventory.db")
else:
    home_dir = os.path.expanduser('~')
    DB_DIR = os.path.join(home_dir, '.bussines_data')
    os.makedirs(DB_DIR, exist_ok=True)
    DB_NAME = os.path.join(DB_DIR, 'inventory.db')


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
        # If an old 'sales' table exists using `product_id`, migrate it to `variant_id`.
        cursor.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='sales'""")
        if cursor.fetchone():
            # inspect columns
            cols = [r[1] for r in cursor.execute("PRAGMA table_info(sales)")]
            if 'variant_id' not in cols and 'product_id' in cols:
                # migrate old sales -> create new table and copy rows mapping product_id -> a variant id when possible
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sales_new (
                        id TEXT PRIMARY KEY,
                        variant_id TEXT,
                        date_sold TEXT,
                        quantity_sold INTEGER NOT NULL,
                        price REAL NOT NULL,
                        FOREIGN KEY (variant_id) REFERENCES product_variants (id)
                    )
                """)

                for row in cursor.execute("SELECT id, product_id, date_sold, quantity_sold, price FROM sales"):
                    sale_id, prod_id, date_sold, qty, price = row
                    # try to find any variant for this product
                    cur_variant = cursor.execute("SELECT id FROM product_variants WHERE product_id=? LIMIT 1", (prod_id,)).fetchone()
                    variant_id = cur_variant[0] if cur_variant else None
                    cursor.execute(
                        "INSERT OR REPLACE INTO sales_new (id, variant_id, date_sold, quantity_sold, price) VALUES (?, ?, ?, ?, ?)",
                        (sale_id, variant_id, date_sold, qty, price)
                    )

                # drop old table and rename new
                cursor.execute("DROP TABLE sales")
                cursor.execute("ALTER TABLE sales_new RENAME TO sales")
        else:
            # create fresh sales table
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
        # Create indexes for better performance. Only create variant index if column exists.
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_variants_product_id 
            ON product_variants(product_id)
        """)
        # check sales columns before creating index
        sales_cols = [r[1] for r in cursor.execute("PRAGMA table_info(sales)")]
        if 'variant_id' in sales_cols:
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

