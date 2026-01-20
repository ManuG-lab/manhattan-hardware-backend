from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from database import create_tables
import uuid
from fastapi.middleware.cors import CORSMiddleware


# =============================
# DATA MODELS
# =============================

class Product(BaseModel):
    id: str | None = None
    name: str
    category: str
    price: float
    image: str
    dateReceived: str | None = None
    stockReceived: int
    expiryDate: str | None = None

class Sale(BaseModel):
    id: str | None = None
    productId: str
    dateSold: str | None = None
    quantitySold: int
    price: float


# =============================
# 5. API ENDPOINTS
# =============================

def get_connection():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    return conn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

create_tables()

@app.get("/products")
def get_products():
    conn = get_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "price": p["price"],
            "image": p["image"],
            "dateReceived": p["date_received"],
            "stockReceived": p["stock_received"],
            "expiryDate": p["expiry_date"]
        }
        for p in products
    ]


@app.get("/sales")
def get_sales():
    conn = get_connection()
    sales = conn.execute("SELECT * FROM sales").fetchall()
    conn.close()
    return [
        {
            "id": s["id"],
            "productId": s["product_id"],
            "dateSold": s["date_sold"],
            "quantitySold": s["quantity_sold"],
            "price": s["price"]
        }
        for s in sales
    ]


@app.post("/sales")
def add_sale(sale: Sale):
    if not sale.id:
        sale.id = uuid.uuid4().hex[:4]
    if not sale.dateSold:
        from datetime import datetime
        sale.dateSold = datetime.now().strftime("%Y-%m-%d")
    
    conn = get_connection()
    cursor = conn.cursor()

    # Get product stock_received
    product = cursor.execute(
        "SELECT stock_received FROM products WHERE id = ?",
        (sale.productId,),
    ).fetchone()

    if not product:
        conn.close()
        return {"error": "Product not found"}

    # Get total quantity sold so far
    total_sold_result = cursor.execute(
        "SELECT SUM(quantity_sold) FROM sales WHERE product_id = ?",
        (sale.productId,),
    ).fetchone()
    total_sold = total_sold_result[0] if total_sold_result and total_sold_result[0] else 0

    current_stock = product[0] - total_sold

    if sale.quantitySold > current_stock:
        conn.close()
        return {"error": "Insufficient stock"}

    # Insert sale
    cursor.execute(
        """
        INSERT INTO sales (id, product_id, date_sold, quantity_sold, price)
        VALUES (?, ?, ?, ?, ?)
        """,
        (sale.id, sale.productId, sale.dateSold, sale.quantitySold, sale.price),
    )

    conn.commit()
    conn.close()
    return {"message": "Sale recorded"}


@app.post("/products")
def add_product(product: Product):
    if not product.id:
        product.id = uuid.uuid4().hex[:4]
    if not product.dateReceived:
        from datetime import datetime
        product.dateReceived = datetime.now().strftime("%Y-%m-%d")
    if not product.expiryDate:
        from datetime import datetime, timedelta
        product.expiryDate = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO products (id, name, category, price, image, date_received, stock_received, expiry_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product.id,
            product.name,
            product.category,
            product.price,
            product.image,
            product.dateReceived,
            product.stockReceived,
            product.expiryDate,
        ),
    )
    conn.commit()
    conn.close()
    return {"message": "Product added"}


@app.put("/products/{product_id}/sell")
def sell_product(product_id: str, sale: Sale):
    if not sale.id:
        sale.id = uuid.uuid4().hex[:4]
    if not sale.dateSold:
        from datetime import datetime
        sale.dateSold = datetime.now().strftime("%Y-%m-%d")
    sale.productId = product_id
    
    conn = get_connection()
    cursor = conn.cursor()

    # Get product stock_received
    product = cursor.execute(
        "SELECT stock_received FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()

    if not product:
        conn.close()
        return {"error": "Product not found"}

    # Get total quantity sold so far
    total_sold_result = cursor.execute(
        "SELECT SUM(quantity_sold) FROM sales WHERE product_id = ?",
        (product_id,),
    ).fetchone()
    total_sold = total_sold_result[0] if total_sold_result and total_sold_result[0] else 0

    current_stock = product[0] - total_sold

    if sale.quantitySold > current_stock:
        conn.close()
        return {"error": "Insufficient stock"}

    # Insert sale
    cursor.execute(
        """
        INSERT INTO sales (id, product_id, date_sold, quantity_sold, price)
        VALUES (?, ?, ?, ?, ?)
        """,
        (sale.id, product_id, sale.dateSold, sale.quantitySold, sale.price),
    )

    conn.commit()
    conn.close()
    return {"message": "Sale recorded"}


