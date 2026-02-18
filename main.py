import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from pydantic import BaseModel, validator, ValidationError

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

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

create_tables()

# =============================
# HELPER FUNCTIONS
# =============================

def error_response(status_code: int, message: str):
    """Create standardized error response"""
    return make_response(jsonify({"error": message}), status_code)

# =============================
# PRODUCTS
# =============================

@app.route('/products', methods=['GET'])
def get_products():
    """Get all products with optional pagination"""
    try:
        try:
            skip = int(request.args.get('skip', 0))
            limit = int(request.args.get('limit', 100))
        except ValueError:
            return error_response(400, 'Invalid pagination parameters')

        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM products ORDER BY date_received DESC LIMIT ? OFFSET ?",
            (limit, skip)
        ).fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        return error_response(500, f"Database error: {str(e)}")


@app.route('/products', methods=['POST'])
def add_product():
    """Add a new product"""
    try:
        payload = request.get_json() or {}
        try:
            product = Product.model_validate(payload)
        except ValidationError as ve:
            return error_response(400, str(ve))

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
        return jsonify({"message": "Product added", "id": product.id})
    except sqlite3.IntegrityError:
        return error_response(400, "Product with this ID already exists")
    except Exception as e:
        return error_response(500, f"Database error: {str(e)}")


@app.route('/products/<product_id>', methods=['PUT'])
def update_product(product_id: str):
    """Update an existing product"""
    try:
        payload = request.get_json() or {}
        try:
            product = Product.model_validate(payload)
        except ValidationError as ve:
            return error_response(400, str(ve))

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
        
        # Check if product exists
        cursor = conn.execute("SELECT id FROM products WHERE id=?", (product_id,))
        if not cursor.fetchone():
            conn.close()
            return error_response(404, "Product not found")
        
        conn.close()
        return jsonify({"message": "Product updated"})
    except Exception as e:
        return error_response(500, f"Database error: {str(e)}")


@app.route('/products/<product_id>', methods=['DELETE'])
def delete_product(product_id: str):
    """Delete a product and all its variants and sales"""
    try:
        conn = get_connection()
        
        # Check if product exists
        cursor = conn.execute("SELECT id FROM products WHERE id=?", (product_id,))
        if not cursor.fetchone():
            conn.close()
            return error_response(404, "Product not found")
        
        # Delete related sales first (due to foreign key)
        conn.execute("DELETE FROM sales WHERE variant_id IN (SELECT id FROM product_variants WHERE product_id=?)", (product_id,))
        # Delete variants
        conn.execute("DELETE FROM product_variants WHERE product_id=?", (product_id,))
        # Delete product
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Product deleted"})
    except Exception as e:
        return error_response(500, f"Database error: {str(e)}")


@app.route('/products/<product_id>/variants', methods=['GET'])
def get_variants(product_id: str):
    """Get all variants for a product"""
    try:
        conn = get_connection()
        
        # Check if product exists
        cursor = conn.execute("SELECT id FROM products WHERE id=?", (product_id,))
        if not cursor.fetchone():
            conn.close()
            return error_response(404, "Product not found")
        
        rows = conn.execute(
            "SELECT * FROM product_variants WHERE product_id=?",
            (product_id,)
        ).fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        return error_response(500, f"Database error: {str(e)}")


# =============================
# VARIANTS (SIZES)
# =============================

@app.route('/variants', methods=['POST'])
def add_variant():
    """Add a new product variant"""
    try:
        payload = request.get_json() or {}
        try:
            variant = ProductVariant.model_validate(payload)
        except ValidationError as ve:
            return error_response(400, str(ve))

        # Validate product exists
        conn = get_connection()
        cursor = conn.execute("SELECT id FROM products WHERE id=?", (variant.productId,))
        if not cursor.fetchone():
            conn.close()
            return error_response(404, "Product not found")
        
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
        return jsonify({"message": "Variant added", "id": variant.id})
    except sqlite3.IntegrityError:
        return error_response(400, "Variant with this ID already exists")
    except Exception as e:
        return error_response(500, f"Database error: {str(e)}")


# =============================
# SALES
# =============================

@app.route('/sales', methods=['GET'])
def get_sales():
    """Get all sales with optional pagination"""
    try:
        try:
            skip = int(request.args.get('skip', 0))
            limit = int(request.args.get('limit', 100))
        except ValueError:
            return error_response(400, 'Invalid pagination parameters')

        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM sales ORDER BY date_sold DESC LIMIT ? OFFSET ?",
            (limit, skip)
        ).fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        return error_response(500, f"Database error: {str(e)}")


@app.route('/sales', methods=['POST'])
def add_sale():
    """Record a new sale and update stock"""
    try:
        payload = request.get_json() or {}
        try:
            sale = Sale.model_validate(payload)
        except ValidationError as ve:
            return error_response(400, str(ve))

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
            return error_response(404, "Variant not found")

        # Calculate available stock
        total_sold = cursor.execute(
            "SELECT COALESCE(SUM(quantity_sold), 0) FROM sales WHERE variant_id=?",
            (sale.variantId,)
        ).fetchone()[0]

        current_stock = variant["stock_received"] - total_sold

        if sale.quantitySold > current_stock:
            conn.close()
            return error_response(400, f"Insufficient stock. Available: {current_stock}")

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
        return jsonify({"message": "Sale recorded", "id": sale.id})
    except Exception as e:
        return error_response(500, f"Database error: {str(e)}")


@app.route('/products/<product_id>/sell', methods=['PUT'])
def sell_product(product_id: str):
    """Alternative endpoint to record a sale by product ID"""
    try:
        payload = request.get_json() or {}
        try:
            sell_request = SellRequest.model_validate(payload)
        except ValidationError as ve:
            return error_response(400, str(ve))

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
            return error_response(404, "No variant found for this product")
        
        variant_id = variant["id"]
        
        # Check stock
        total_sold = cursor.execute(
            "SELECT COALESCE(SUM(quantity_sold), 0) FROM sales WHERE variant_id=?",
            (variant_id,)
        ).fetchone()[0]
        
        current_stock = variant["stock_received"] - total_sold
        
        if sell_request.quantitySold > current_stock:
            conn.close()
            return error_response(400, f"Insufficient stock. Available: {current_stock}")
        
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
        return jsonify({"message": "Sale recorded", "id": sale_id})
    except Exception as e:
        return error_response(500, f"Database error: {str(e)}")


# =============================
# HELPER FUNCTIONS (Additional)
# =============================

def is_number(x):
    """Check if value can be converted to float"""
    try:
        if x is None:
            return False
        float(x)
        return True
    except (ValueError, TypeError):
        return False


# =============================
# EXCEL IMPORT
# =============================

@app.route('/api/import-excel', methods=['POST'])
def import_excel():
    """Import products from Excel file"""
    import pandas as pd
    from io import BytesIO
    
    try:
        if 'file' not in request.files:
            return error_response(400, 'No file provided')
        
        file = request.files['file']
        if file.filename == '':
            return error_response(400, 'No file selected')
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            return error_response(400, 'Invalid file format. Please upload .xlsx or .xls file')
        
        # Read Excel file
        try:
            data = file.read()
            df = pd.read_excel(BytesIO(data))
        except Exception as e:
            return error_response(400, f'Failed to read Excel file: {str(e)}')
        
        # Validate DataFrame
        if df.empty:
            return error_response(400, 'Excel file is empty')
        
        # Check required columns
        required_columns = ['Product', 'Category']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return error_response(400, f'Missing required columns: {", ".join(missing_columns)}')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Extract and clean data
                product_name = str(row.get('Product', '')).strip()
                category = str(row.get('Category', '')).strip()
                size = str(row.get('Size', 'N/A')).strip() if 'Size' in row else 'N/A'
                price = row.get('Price') if 'Price' in row else None
                image = str(row.get('Image', '')).strip() if 'Image' in row else None
                
                # Validate required fields
                if not product_name:
                    errors.append(f"Row {idx + 2}: Product name is required")
                    continue
                
                if not category:
                    errors.append(f"Row {idx + 2}: Category is required")
                    continue
                
                # Validate and convert price
                if price is None or not is_number(price):
                    errors.append(f"Row {idx + 2}: Invalid price '{price}'")
                    continue
                
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    errors.append(f"Row {idx + 2}: Invalid price '{price}'")
                    continue
                
                if price < 0:
                    errors.append(f"Row {idx + 2}: Price cannot be negative")
                    continue
                
                # Create product
                product_id = uuid.uuid4().hex[:8]
                date_received = datetime.now().strftime("%Y-%m-%d")
                expiry_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
                
                cursor.execute("""
                    INSERT INTO products (id, name, category, image, date_received, expiry_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (product_id, product_name, category, image, date_received, expiry_date))
                
                # Create variant with size and price
                variant_id = uuid.uuid4().hex[:8]
                stock_received = 1
                
                cursor.execute("""
                    INSERT INTO product_variants (id, product_id, size, price, stock_received)
                    VALUES (?, ?, ?, ?, ?)
                """, (variant_id, product_id, size, price, stock_received))
                
                imported_count += 1
                
            except sqlite3.IntegrityError as e:
                errors.append(f"Row {idx + 2}: Database integrity error - {str(e)}")
                continue
            except Exception as e:
                errors.append(f"Row {idx + 2}: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "imported": imported_count,
            "total_rows": len(df),
            "errors": errors
        })
    
    except Exception as e:
        return error_response(500, f"Import error: {str(e)}")


if __name__ == '__main__':
    # Ensure tables exist before starting
    create_tables()
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)


