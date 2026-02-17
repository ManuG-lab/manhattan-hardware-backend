from datetime import datetime, timedelta
import uuid

from database import get_connection


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Insert a sample product if none exist
    if not cur.execute("SELECT 1 FROM products LIMIT 1").fetchone():
        pid = uuid.uuid4().hex[:6]
        date_received = datetime.now().strftime("%Y-%m-%d")
        expiry_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        cur.execute(
            "INSERT INTO products (id, name, category, image, date_received, expiry_date) VALUES (?, ?, ?, ?, ?, ?)",
            (pid, 'Sample Product', 'General', None, date_received, expiry_date)
        )

        # Add a variant for the product
        vid = uuid.uuid4().hex[:6]
        cur.execute(
            "INSERT INTO product_variants (id, product_id, size, price, stock_received) VALUES (?, ?, ?, ?, ?)",
            (vid, pid, 'M', 9.99, 100)
        )

        # Add a sample sale
        sid = uuid.uuid4().hex[:6]
        cur.execute(
            "INSERT INTO sales (id, variant_id, date_sold, quantity_sold, price) VALUES (?, ?, ?, ?, ?)",
            (sid, vid, date_received, 2, 9.99)
        )

        conn.commit()
        print('Inserted sample product/variant/sale')
    else:
        print('Products already exist; skipping initialization')

    conn.close()


if __name__ == '__main__':
    init_db()
