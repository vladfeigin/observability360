import os
import sqlite3
from flask import Flask, request, jsonify
from datetime import datetime
import requests

app = Flask(__name__)
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

@app.route('/orders', methods=['GET'])
def list_my_orders():
    """
    ListMyOrders API.
    Expects a query parameter 'userId'.
    Returns a JSON list of orders. Each order includes:
      - orderId
      - orderDate
      - products: a list of objects with productId, productName, and quantity.
    """
    user_id = request.args.get('userId')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE user_id = ?', (user_id,))
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
    return jsonify(orders), 200

@app.route('/orders', methods=['POST'])
def create_order():
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
    data = request.get_json()
    user_id = data.get('userId')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    # Retrieve the cart items for this user from the Cart Service.
    cart_response = requests.get(f"{CART_SERVICE_URL}/cart", params={"userId": user_id})
    if cart_response.status_code != 200:
        return jsonify({'error': 'Failed to retrieve cart items'}), 500
    cart_items = cart_response.json()
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400

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
        return jsonify({'error': f'Failed to create order: {str(e)}'}), 500
    conn.close()

    # Optionally, you might want to clear the user's cart here.

    return jsonify({
        'orderId': order_id,
        'orderDate': order_date,
        'products': cart_items
    }), 201

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5003)