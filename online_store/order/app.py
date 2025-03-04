import os
import sqlite3
from datetime import datetime
import requests

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

# Database file for orders
DATABASE = os.path.join(os.getcwd(), 'online_store/db/online_store.db')

# Use environment variable to get Cart Service URL.
CART_SERVICE_URL = os.environ.get("CART_SERVICE_URL", "http://127.0.0.1:5002")


def init_db():
    db_dir = os.path.dirname(DATABASE)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Orders table stores basic order info.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            order_date TEXT NOT NULL
        )
    ''')
    # Order_items table stores each product in an order.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    ''')
    conn.commit()
    conn.close()


class OrderRequest(BaseModel):
    userId: str


@app.get("/orders", response_model=list)
def list_my_orders(userId: str = Query(..., description="User ID")):
    """
    ListMyOrders API.
    Expects a query parameter 'userId'.
    Returns a list of orders. Each order includes:
      - orderId
      - orderDate
      - products: a list of objects with productId, productName, and quantity.
    """
    if not userId:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE user_id = ?', (userId,))
    orders_rows = cursor.fetchall()
    orders = []
    for order in orders_rows:
        order_id = order['id']
        cursor.execute('SELECT product_id, product_name, quantity FROM order_items WHERE order_id = ?', (order_id,))
        items_rows = cursor.fetchall()
        items = []
        for item in items_rows:
            items.append({
                'productId': item['product_id'],
                'productName': item['product_name'],
                'quantity': item['quantity']
            })
        orders.append({
            'orderId': order_id,
            'orderDate': order['order_date'],
            'products': items
        })
    conn.close()
    return orders


@app.post("/orders", status_code=201)
def create_order(order_req: OrderRequest):
    """
    CreateOrder API.
    Expects a JSON payload with: userId.
    The service calls the Cart Service to get all items in the user's cart,
    then creates an order with the following fields:
      - orderId (generated)
      - orderDate (current UTC datetime)
      - products list (each including productId, productName, and quantity)
    If the cart is empty, returns an error.
    """
    user_id = order_req.userId
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    # Retrieve the cart items for this user from the Cart Service.
    cart_response = requests.get(f"{CART_SERVICE_URL}/cart", params={"userId": user_id})
    if cart_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to retrieve cart items")
    cart_items = cart_response.json()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    order_date = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO orders (user_id, order_date) VALUES (?, ?)', (user_id, order_date))
        order_id = cursor.lastrowid
        for item in cart_items:
            product_id = item.get('productId')
            product_name = item.get('productName')
            quantity = item.get('quantity')
            cursor.execute('''
                INSERT INTO order_items (order_id, product_id, product_name, quantity)
                VALUES (?, ?, ?, ?)
            ''', (order_id, product_id, product_name, quantity))
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")
    conn.close()

    # Optionally, you might want to clear the user's cart here.
    return JSONResponse(status_code=201, content={
        'orderId': order_id,
        'orderDate': order_date,
        'products': cart_items
    })


if __name__ == '__main__':
    init_db()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5003)