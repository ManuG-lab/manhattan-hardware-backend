from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from database import create_tables, get_connection
import uuid
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta

# =============================
# DATA MODELS
# =============================

class Product(BaseModel):
    id: str | None = None
    name: str
    category: str
    image: str | None = None
    dateReceived: str | None = None
    expiryDate: str | None = None


class ProductVariant(BaseModel):
    id: str | None = None
    productId: str
    size: str
    price: float
    stockReceived: int


class Sale(BaseModel):
    id: str | None = None
    variantId: str
    dateSold: str | None = None
    quantitySold: int
    price: float


# =============================
# APP SETUP
# =============================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

create_tables()

# =============================
# PRODUCTS
# =============================

@app.get("/products")
def get_products():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/products")
def add_product(product: Product):
    product.id = product.id or uuid.uuid4().hex[:6]
    product.dateReceived = product.dateReceived or datetime.now().strftime("%Y-%m-%d")
    product.expiryDate = product.expiryDate or (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")

    conn = get_connection()
    conn.execute("""
        INSERT INTO products (id, name, category, image, date_received, expiry_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        product.id,
        product.name,
        product.category,
        product.image,
        product.dateReceived,
        product.expiryDate
    ))
    conn.commit()
    conn.close()
    return {"message": "Product added", "id": product.id}


@app.put("/products/{product_id}")
def update_product(product_id: str, product: Product):
    conn = get_connection()
    conn.execute("""
        UPDATE products
        SET name=?, category=?, image=?, date_received=?, expiry_date=?
        WHERE id=?
    """, (
        product.name,
        product.category,
        product.image,
        product.dateReceived,
        product.expiryDate,
        product_id
    ))
    conn.commit()
    conn.close()
    return {"message": "Product updated"}


@app.delete("/products/{product_id}")
def delete_product(product_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM sales WHERE variant_id IN (SELECT id FROM product_variants WHERE product_id=?)", (product_id,))
    conn.execute("DELETE FROM product_variants WHERE product_id=?", (product_id,))
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
    return {"message": "Product deleted"}

# =============================
# VARIANTS (SIZES)
# =============================

@app.get("/products/{product_id}/variants")
def get_variants(product_id: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM product_variants WHERE product_id=?",
        (product_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/variants")
def add_variant(variant: ProductVariant):
    variant.id = variant.id or uuid.uuid4().hex[:6]

    conn = get_connection()
    conn.execute("""
        INSERT INTO product_variants (id, product_id, size, price, stock_received)
        VALUES (?, ?, ?, ?, ?)
    """, (
        variant.id,
        variant.productId,
        variant.size,
        variant.price,
        variant.stockReceived
    ))
    conn.commit()
    conn.close()
    return {"message": "Variant added", "id": variant.id}


# =============================
# SALES
# =============================

@app.get("/sales")
def get_sales():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM sales").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/sales")
def add_sale(sale: Sale):
    sale.id = sale.id or uuid.uuid4().hex[:6]
    sale.dateSold = sale.dateSold or datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    cursor = conn.cursor()

    variant = cursor.execute(
        "SELECT stock_received FROM product_variants WHERE id=?",
        (sale.variantId,)
    ).fetchone()

    if not variant:
        return {"error": "Variant not found"}

    total_sold = cursor.execute(
        "SELECT SUM(quantity_sold) FROM sales WHERE variant_id=?",
        (sale.variantId,)
    ).fetchone()[0] or 0

    current_stock = variant["stock_received"] - total_sold

    if sale.quantitySold > current_stock:
        return {"error": "Insufficient stock"}

    cursor.execute("""
        INSERT INTO sales (id, variant_id, date_sold, quantity_sold, price)
        VALUES (?, ?, ?, ?, ?)
    """, (
        sale.id,
        sale.variantId,
        sale.dateSold,
        sale.quantitySold,
        sale.price
    ))

    conn.commit()
    conn.close()
    return {"message": "Sale recorded"}
