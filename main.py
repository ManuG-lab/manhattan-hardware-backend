import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, validator
from fastapi.middleware.cors import CORSMiddleware

from database import create_tables, get_connection

# =============================
# DATA MODELS
# =============================

class Product(BaseModel):
    id: Optional[str] = None
    name: str
    category: str
    image: Optional[str] = None
    dateReceived: Optional[str] = None
    expiryDate: Optional[str] = None

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Product name cannot be empty')
        return v.strip()

    @validator('category')
    def validate_category(cls, v):
        if not v or not v.strip():
            raise ValueError('Category cannot be empty')
        return v.strip()


class ProductVariant(BaseModel):
    id: Optional[str] = None
    productId: str
    size: str
    price: float
    stockReceived: int

    @validator('price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('Price cannot be negative')
        return v

    @validator('stockReceived')
    def validate_stock(cls, v):
        if v < 0:
            raise ValueError('Stock cannot be negative')
        return v


class Sale(BaseModel):
    id: Optional[str] = None
    variantId: str
    dateSold: Optional[str] = None
    quantitySold: int
    price: float

    @validator('price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('Price cannot be negative')
        return v

    @validator('quantitySold')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity sold must be positive')
        return v


class SellRequest(BaseModel):
    variantId: str
    quantitySold: int


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
# HELPER FUNCTIONS
# =============================

def error_response(status_code: int, message: str):
    """Create standardized error response"""
    return {"error": message}

# =============================
# PRODUCTS
# =============================

@app.get("/products")
def get_products(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return")
):
    """Get all products with optional pagination"""
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM products ORDER BY date_received DESC LIMIT ? OFFSET ?",
            (limit, skip)
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/products")
def add_product(product: Product):
    """Add a new product"""
    try:
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
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product with this ID already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.put("/products/{product_id}")
def update_product(product_id: str, product: Product):
    """Update an existing product"""
    try:
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
        
        # Check if product was actually updated
        cursor = conn.execute("SELECT id FROM products WHERE id=?", (product_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Product not found")
        
        conn.close()
        return {"message": "Product updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.delete("/products/{product_id}")
def delete_product(product_id: str):
    """Delete a product and all its variants and sales"""
    try:
        conn = get_connection()
        
        # Check if product exists
        cursor = conn.execute("SELECT id FROM products WHERE id=?", (product_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Delete related sales first (due to foreign key)
        conn.execute("DELETE FROM sales WHERE variant_id IN (SELECT id FROM product_variants WHERE product_id=?)", (product_id,))
        # Delete variants
        conn.execute("DELETE FROM product_variants WHERE product_id=?", (product_id,))
        # Delete product
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        conn.close()
        return {"message": "Product deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/products/{product_id}/variants")
def get_variants(product_id: str):
    """Get all variants for a product"""
    try:
        conn = get_connection()
        
        # Check if product exists
        cursor = conn.execute("SELECT id FROM products WHERE id=?", (product_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Product not found")
        
        rows = conn.execute(
            "SELECT * FROM product_variants WHERE product_id=?",
            (product_id,)
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# =============================
# VARIANTS (SIZES)
# =============================

@app.post("/variants")
def add_variant(variant: ProductVariant):
    """Add a new product variant"""
    try:
        # Validate product exists
        conn = get_connection()
        cursor = conn.execute("SELECT id FROM products WHERE id=?", (variant.productId,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Product not found")
        
        variant.id = variant.id or uuid.uuid4().hex[:6]

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
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Variant with this ID already exists")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# =============================
# SALES
# =============================

@app.get("/sales")
def get_sales(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return")
):
    """Get all sales with optional pagination"""
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM sales ORDER BY date_sold DESC LIMIT ? OFFSET ?",
            (limit, skip)
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/sales")
def add_sale(sale: Sale):
    """Record a new sale and update stock"""
    try:
        sale.id = sale.id or uuid.uuid4().hex[:6]
        sale.dateSold = sale.dateSold or datetime.now().strftime("%Y-%m-%d")

        conn = get_connection()
        cursor = conn.cursor()

        # Check if variant exists and get current stock
        cursor.execute(
            "SELECT stock_received FROM product_variants WHERE id=?",
            (sale.variantId,)
        )
        variant = cursor.fetchone()

        if not variant:
            conn.close()
            raise HTTPException(status_code=404, detail="Variant not found")

        # Calculate available stock
        total_sold = cursor.execute(
            "SELECT COALESCE(SUM(quantity_sold), 0) FROM sales WHERE variant_id=?",
            (sale.variantId,)
        ).fetchone()[0]

        current_stock = variant["stock_received"] - total_sold

        if sale.quantitySold > current_stock:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Insufficient stock. Available: {current_stock}")

        # Record the sale
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
        return {"message": "Sale recorded", "id": sale.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.put("/products/{product_id}/sell")
def sell_product(product_id: str, sell_request: SellRequest):
    """Alternative endpoint to record a sale by product ID"""
    try:
        # Find the variant for this product
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, stock_received FROM product_variants WHERE product_id=? LIMIT 1",
            (product_id,)
        )
        variant = cursor.fetchone()
        
        if not variant:
            conn.close()
            raise HTTPException(status_code=404, detail="No variant found for this product")
        
        variant_id = variant["id"]
        
        # Check stock
        total_sold = cursor.execute(
            "SELECT COALESCE(SUM(quantity_sold), 0) FROM sales WHERE variant_id=?",
            (variant_id,)
        ).fetchone()[0]
        
        current_stock = variant["stock_received"] - total_sold
        
        if sell_request.quantitySold > current_stock:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Insufficient stock. Available: {current_stock}")
        
        # Create sale
        sale_id = uuid.uuid4().hex[:6]
        date_sold = datetime.now().strftime("%Y-%m-%d")
        price = cursor.execute(
            "SELECT price FROM product_variants WHERE id=?",
            (variant_id,)
        ).fetchone()["price"]
        
        cursor.execute("""
            INSERT INTO sales (id, variant_id, date_sold, quantity_sold, price)
            VALUES (?, ?, ?, ?, ?)
        """, (sale_id, variant_id, date_sold, sell_request.quantitySold, price))
        
        conn.commit()
        conn.close()
        return {"message": "Sale recorded", "id": sale_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

