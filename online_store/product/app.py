import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DATABASE = os.path.join(os.getcwd(), 'online_store/db/online_store.db')
print(f"DB=={DATABASE}")

def init_db():
    """
    Initialize the SQLite database.
    Creates the 'products' table if it doesn't exist.
    """
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

@app.route('/products', methods=['GET'])
def list_products():
    """
    ListProducts API.
    Returns a list of products in JSON format.
    """
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
    return jsonify(products), 200

@app.route('/products', methods=['POST'])
def add_product():
    """
    AddProduct API.
    Expects a JSON payload with: productId, name, description (optional), 
    numberItemsInStock, and price.
    """
    data = request.get_json()
    product_id = data.get('productId')
    name = data.get('name')
    description = data.get('description', '')
    number_items_in_stock = data.get('numberItemsInStock')
    price = data.get('price')

    if not all([product_id, name, number_items_in_stock, price]):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO products (product_id, name, description, number_items_in_stock, price)
        VALUES (?, ?, ?, ?, ?)
    ''', (product_id, name, description, number_items_in_stock, price))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Product added successfully'}), 201

if __name__ == '__main__':
    init_db()  # Create the products table (and seed data if needed)
    app.run(debug=True, port=5001)