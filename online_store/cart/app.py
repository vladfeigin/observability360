import os
import sqlite3
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
from online_store.otel.otel import configure_telemetry, trace_span

SERVICE_VERSION = "1.0.0"

app = FastAPI()
instruments = configure_telemetry(app, "Cart Service", SERVICE_VERSION)

# Get instruments
meter = instruments["meter"]
tracer = instruments["tracer"]
logger = instruments["logger"]

# Create metrics instruments
request_counter = meter.create_counter(
    name="cart_service_http_requests_total",
    description="Total number of HTTP requests to the cart service",
    unit="1"
)

DATABASE = os.path.join(os.getcwd(), 'online_store/db/online_store.db')
print(f"DB=={DATABASE}")

@trace_span("init_db for Cart Service", tracer)
def init_db():
    """
    Initialize the SQLite database.
    Creates the 'cart_items' table if it doesn't exist.
    The table stores cart items with:
      - id: auto-increment primary key
      - user_id: identifier for the user owning the cart
      - product_id: identifier for the product added to the cart
      - product_name: name of the product
      - quantity: number of units for the product
    """
    db_dir = os.path.dirname(DATABASE)
    if not os.path.exists(db_dir):
        raise Exception(f"Database directory {db_dir} does not exist. Try running the service from the project root folder.")

    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS cart_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL
            )''')
        conn.commit()
    except sqlite3.Error as e:
        conn.close()
        logger.error("Error initializing database: %s", e)
        raise HTTPException(status_code=500, detail="Cart database initialization failed") from e
    finally:
        conn.close()

@trace_span("list_cart_items", tracer)
@app.get("/cart")
def list_cart_items(userId: str = None):
    """
    ListCartItems API.
    Returns a list of cart items in JSON format.
    You can filter items by providing a query parameter 'userId'.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if userId:
        cursor.execute('''
            SELECT id, user_id, product_id, product_name, quantity FROM cart_items WHERE user_id = ?
        ''', (userId,))
    else:
        cursor.execute('''
            SELECT id, user_id, product_id, product_name, quantity FROM cart_items
        ''')
    rows = cursor.fetchall()
    conn.close()

    cart_items = []
    for row in rows:
        cart_items.append({
            'id': row['id'],
            'userId': row['user_id'],
            'productId': row['product_id'],
            'productName': row['product_name'],
            'quantity': row['quantity']
        })
    return JSONResponse(content=cart_items, status_code=200)

@app.post("/cart", status_code=201)
async def add_cart_item(request: Request):
    """
    AddCartItem API.
    Expects a JSON payload with: userId, productId, productName, and quantity.
    This endpoint calls the Product service's RemoveProductFromStock method.
    RemoveProductFromStock will attempt to decrease the product's stock by the required quantity.
    If the product doesn't have the required quantity in stock, it returns an error.
    """
    request_counter.add(1, attributes={"route": "/cart", "method": "POST" })
    
    data = await request.json()
    user_id = data.get('userId')
    product_id = data.get('productId')
    product_name = data.get('productName')
    
    with tracer.start_as_current_span("add_cart_item") as span:
        #add custom attributes to the span
        span.set_attribute("user.id", user_id)
        span.set_attribute("product.id", product_id)
        span.set_attribute("product.name", product_name)    
        logger.info(f"Adding item to cart: {user_id}, {product_id}, {product_name}")
        try:
            quantity = int(data.get('quantity'))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid quantity provided")
    
        if not all([user_id, product_id, quantity]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        conn = sqlite3.connect(DATABASE)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO cart_items (user_id, product_id, product_name, quantity)
                VALUES (?, ?, ?, ?)
            ''', (user_id, product_id, product_name, quantity))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding item to cart: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to add item to cart: {str(e)}")
        finally:
            conn.close()

        return JSONResponse(content={'message': 'Cart item added successfully'}, status_code=201)

@app.put("/cart/{item_id}")
async def update_cart_item(item_id: int, request: Request):
    """
    UpdateCartItem API.
    Expects a JSON payload with the new quantity for the specified cart item.
    """
    data = await request.json()
    quantity = data.get('quantity')
    
    with tracer.start_as_current_span("update_cart_item") as span:
        if quantity is None:
            raise HTTPException(status_code=400, detail="Missing quantity field")
        
        logger.info(f"Updating item in cart: {item_id}, {quantity}")
        conn = sqlite3.connect(DATABASE)
        try:
            cursor = conn.cursor()
            cursor.execute('UPDATE cart_items SET quantity = ? WHERE id = ?', (quantity, item_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating cart item: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to update cart item: {str(e)}")
        finally:
            conn.close()

        return JSONResponse(content={'message': 'Cart item updated successfully'}, status_code=200)

@app.delete("/cart/{item_id}")
def delete_cart_item(item_id: int):
    """
    DeleteCartItem API.
    Deletes a cart item by its ID.
    """
    with tracer.start_as_current_span("delete_cart_item") as span:
        span.set_attribute("item.id", item_id)

        logger.info(f"Deleting item from cart: {item_id}")
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cart_items WHERE id = ?', (item_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting cart item: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete cart item: {str(e)}")
        finally:
            conn.close()
            
        return JSONResponse(content={'message': 'Cart item deleted successfully'}, status_code=200)

if __name__ == '__main__':
    init_db()  # Ensure the database and table are set up before running the service
    uvicorn.run(app, host="0.0.0.0", port=5002)