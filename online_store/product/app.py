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

@app.route('/products/remove_stock', methods=['POST'])
def remove_product_from_stock():
    """
    RemoveProductFromStock API.
    Expects a JSON payload with: productName and required_qty.
    Decreases the number_items_in_stock for the given product by required_qty.
    If the product is not found or does not have enough stock, returns an error.
    """
    data = request.get_json()
    product_name = data.get('productName')
    required_qty = data.get('required_qty')

    if not product_name or required_qty is None:
        return jsonify({'error': 'Missing required fields: productName and required_qty'}), 400

    try:
        required_qty = int(required_qty)
        if required_qty <= 0:
            raise ValueError()
    except ValueError:
        return jsonify({'error': 'Invalid required_qty value'}), 400

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT number_items_in_stock FROM products WHERE name = ?', (product_name,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return jsonify({'error': 'Product not found'}), 404

    current_stock = row['number_items_in_stock']
    if current_stock < required_qty:
        conn.close()
        return jsonify({'error': 'The required quantity is not in stock'}), 400

    new_stock = current_stock - required_qty
    cursor.execute('UPDATE products SET number_items_in_stock = ? WHERE name = ?', (new_stock, product_name))
    conn.commit()
    conn.close()

    return jsonify({'message': f'Successfully removed {required_qty} items from {product_name}. New stock is {new_stock}.'}), 200

if __name__ == '__main__':
    init_db()  # Create the products table (and seed data if needed)
    app.run(debug=True, port=5001)