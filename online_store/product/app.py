import os
import sqlite3
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from online_store.otel.otel import configure_telemetry

SERVICE_VERSION = "1.0.0"

app = FastAPI()
instruments = configure_telemetry(app, "Product Service", SERVICE_VERSION)

# Get instruments
meter = instruments["meter"]
tracer = instruments["tracer"]
logger = instruments["logger"]

# Create metrics instruments
request_counter = meter.create_counter(
    name="product_http_requests_total",
    description="Total number of HTTP requests to the product service",
    unit="1"
)

DATABASE = os.path.join(os.getcwd(), 'online_store/db/online_store.db')
print(f"DB=={DATABASE}")

def init_db():
    """
    Initialize the SQLite database.
    Creates the 'products' table if it doesn't exist.
    """
    logger.info("Initializing Product service database...")
    db_dir = os.path.dirname(DATABASE)
    if not os.path.exists(db_dir):
        logger.error(f"Database directory {db_dir} does not exist. Try running the service from the project root folder.")
        raise Exception(f"Database directory {db_dir} does not exist. Try running the service from the project root folder.")
        
    with tracer.start_as_current_span("init_product_db"):
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    description TEXT,
                    number_items_in_stock INTEGER NOT NULL,
                    price REAL NOT NULL
                )
            ''')
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            conn.close()
            logger.error("Error initializing database: %s", e)

@app.get("/products")
def list_products():
    """
    ListProducts API.
    Returns a list of products in JSON format.
    """
    with tracer.start_as_current_span("list_products"):
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT product_id, name, description, number_items_in_stock, price 
            FROM products
        ''')
        rows = cursor.fetchall()
        conn.close()

        products = []
        for row in rows:
            products.append({
                'productId': row['product_id'],
                'name': row['name'],
                'description': row['description'],
                'numberItemsInStock': row['number_items_in_stock'],
                'price': row['price']
            })
        return JSONResponse(content=products, status_code=200)

@app.post("/products", status_code=201)
async def add_product(request: Request):
    """
    AddProduct API.
    Expects a JSON payload with: productId, name, description (optional), 
    numberItemsInStock, and price.
    """
    with tracer.start_as_current_span("add_product") as span:
        data = await request.json()
        product_id = data.get('productId')
        name = data.get('name')
        description = data.get('description', '')
        number_items_in_stock = data.get('numberItemsInStock')
        price = data.get('price')
        
        span.set_attribute("product.product_id", product_id)
        span.set_attribute("product.name", name)
        span.set_attribute("product.description", description)
        span.set_attribute("product.number_items_in_stock", number_items_in_stock)
        span.set_attribute("product.price", price)
        
        if not all([product_id, name, number_items_in_stock, price]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        logger.info(f"Adding product: {product_id}, {name}, {description}, {number_items_in_stock}, {price}")
        conn = sqlite3.connect(DATABASE)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO products (product_id, name, description, number_items_in_stock, price)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_id, name, description, number_items_in_stock, price))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to add product: {str(e)}")
        finally:
            conn.close()

        return JSONResponse(content={'message': 'Product added successfully'}, status_code=201)

# [CHANGED/MERGED] New endpoint merging add and remove stock functionality
@app.post("/products/update_stock", status_code=200)
async def update_stock(request: Request):
    """
    Update Product Stock API.
    Expects a JSON payload with: productName and qty_change.
    - If qty_change is positive, the stock is increased.
    - If qty_change is negative, the stock is decreased.
    """
    with tracer.start_as_current_span("update_product_stock") as span:
        data = await request.json()
        product_name = data.get('productName')
        qty_change = data.get('qty_change')
        
        if not product_name or qty_change is None:
            raise HTTPException(status_code=400, detail="Missing required fields: productName and qty_change")
        
        try:
            qty_change = int(qty_change)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid qty_change value")
        
        span.set_attribute("product.product_name", product_name)
        span.set_attribute("product.qty_change", qty_change)
        logger.info(f"Updating stock for product {product_name} by {qty_change}")
        
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT number_items_in_stock FROM products WHERE name = ?', (product_name,))
        row = cursor.fetchone()
        if row is None:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Product {product_name} not found")
        
        current_stock = row['number_items_in_stock']
        new_stock = current_stock + qty_change
        
        # If trying to reduce more than available
        if new_stock < 0:
            conn.close()
            raise HTTPException(status_code=400, detail="The required quantity is not in stock")
        
        try:
            cursor.execute('UPDATE products SET number_items_in_stock = ? WHERE name = ?', (new_stock, product_name))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating stock for {product_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")
        finally:
            conn.close()
        
        return JSONResponse(content={'message': f"Stock updated successfully for {product_name}. New stock is {new_stock}."}, status_code=200)

@app.delete("/products/{product_id}")
async def delete_product(product_id: str):
    """
    Delete Product API.
    Deletes the product with the given product_id.
    """
    with tracer.start_as_current_span("delete_product") as span:
        span.set_attribute("product.product_id", product_id)
        logger.info(f"Deleting product: {product_id}")
        conn = sqlite3.connect(DATABASE)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
            if cursor.rowcount == 0:
                conn.close()
                logger.error(f"Product {product_id} not found.")
                raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting product {product_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete product: {str(e)}")
        finally:
            conn.close()
        return JSONResponse(content={"message": f"Product {product_id} deleted successfully"}, status_code=200)
    
@app.put("/products/{product_id}")
async def update_product(request: Request, product_id: str):
    data = await request.json()
    # Here, implement logic to update the product (e.g., update name, description, stock, price)
    # For example, if you're updating just the stock:
    new_stock = data.get("numberItemsInStock")
    if new_stock is None:
        raise HTTPException(status_code=400, detail="Missing required field: numberItemsInStock")
    conn = sqlite3.connect(DATABASE)
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET number_items_in_stock = ? WHERE product_id = ?", (new_stock, product_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")
    finally:
        conn.close()
    return JSONResponse(content={'message': 'Product updated successfully'}, status_code=200)

if __name__ == '__main__':
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)