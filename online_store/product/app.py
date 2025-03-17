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
    db_dir = os.path.dirname(DATABASE)
    if not os.path.exists(db_dir):
        raise Exception(f"Database directory {db_dir} does not exist. Try run the service from the project root folder.")
        
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            number_items_in_stock INTEGER NOT NULL,
            price REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

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
    with tracer.start_as_current_span("add_product"):
        data = await request.json()
        product_id = data.get('productId')
        name = data.get('name')
        description = data.get('description', '')
        number_items_in_stock = data.get('numberItemsInStock')
        price = data.get('price')

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

@app.post("/products/remove_stock")
async def remove_product_from_stock(request: Request):
    """
    RemoveProductFromStock API.
    Expects a JSON payload with: productName and required_qty.
    Decreases the number_items_in_stock for the given product by required_qty.
    If the product is not found or does not have enough stock, returns an error.
    """
    with tracer.start_as_current_span("remove_product_from_stock"):
        data = await request.json()
        product_name = data.get('productName')
        required_qty = data.get('required_qty')

        if not product_name or required_qty is None:
            raise HTTPException(status_code=400, detail="Missing required fields: productName and required_qty")
        
        logger.info(f"Removing {required_qty} items from {product_name}")

        try:
            required_qty = int(required_qty)
            if required_qty <= 0:
                raise ValueError()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid required_qty value")

        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT number_items_in_stock FROM products WHERE name = ?', (product_name,))
        row = cursor.fetchone()

        if row is None:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Product: {product_name} not found")

        current_stock = row['number_items_in_stock']
        if current_stock < required_qty:
            conn.close()
            raise HTTPException(status_code=400, detail="The required quantity is not in stock")

        new_stock = current_stock - required_qty
        # TODO -wrap this in a transaction in try/except block
        cursor.execute('UPDATE products SET number_items_in_stock = ? WHERE name = ?', (new_stock, product_name))
        conn.commit()
        conn.close()

        return JSONResponse(content={'message': f"Successfully removed {required_qty} items from {product_name}. New stock is {new_stock}."}, status_code=200)

@app.post("/products/add_stock")
async def add_product_to_stock(request: Request):
    """
    AddProductToStock API.
    Expects a JSON payload with: productName and added_qty.
    Increases the number_items_in_stock for the given product by added_qty.
    """
    with tracer.start_as_current_span("add_product_to_stock"):
        data = await request.json()
        product_name = data.get('productName')
        added_qty = data.get('added_qty')

        if not product_name or added_qty is None:
            raise HTTPException(status_code=400, detail="Missing required fields: productName and added_qty")

        logger.info(f"Adding {added_qty} items to {product_name}")
        try:
            added_qty = int(added_qty)
            if added_qty <= 0:
                raise ValueError()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid added_qty value")

        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT number_items_in_stock FROM products WHERE name = ?', (product_name,))
        row = cursor.fetchone()

        if row is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Product not found")

        current_stock = row['number_items_in_stock']
        new_stock = current_stock + added_qty
        cursor.execute('UPDATE products SET number_items_in_stock = ? WHERE name = ?', (new_stock, product_name))
        conn.commit()
        conn.close()

        return JSONResponse(content={'message': f"Successfully added {added_qty} items to {product_name}. New stock is {new_stock}."}, status_code=200)

if __name__ == '__main__':
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)