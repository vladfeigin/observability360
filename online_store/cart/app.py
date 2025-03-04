import os
import sqlite3
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Define the path to the cart service database
DATABASE = os.path.join(os.getcwd(), 'online_store/db/online_store.db')
print(f"DB=={DATABASE}")

def init_db():
    """
    Initialize the SQLite database.
    Creates the 'cart_items' table if it doesn't exist.
    The table stores cart items with:
      - id: auto-increment primary key
      - user_id: identifier for the user owning the cart
      - product_id: identifier for the product added to the cart
      - quantity: number of units for the product
    """
    db_dir = os.path.dirname(DATABASE)
    if not os.path.exists(db_dir):
        raise Exception(f"Database directory {db_dir} does not exist. Try running the service from the project root folder.")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/cart', methods=['GET'])
def list_cart_items():
    """
    ListCartItems API.
    Returns a list of cart items in JSON format.
    You can filter items by providing a query parameter 'userId'.
    """
    user_id = request.args.get('userId')
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if user_id:
        cursor.execute('''
            SELECT id, user_id, product_id, product_name, quantity FROM cart_items WHERE user_id = ?
        ''', (user_id,))
    else:
        cursor.execute('''
            SELECT id, user_id, product_id, product_name ,quantity FROM cart_items
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
    return jsonify(cart_items), 200

@app.route('/cart', methods=['POST'])
def add_cart_item():
    """
    AddCartItem API.
    Expects a JSON payload with: userId, productId, and quantity.
    This endpoint calls the Product service's RemoveProductFromStock method.
    RemoveProductFromStock will attempt to decrease the product's stock by the required quantity.
    If the product doesn't have the required quantity in stock, it returns an error.
    """
    data = request.get_json()
    user_id = data.get('userId')
    product_id = data.get('productId')
    product_name = data.get('productName')
    try:
        quantity = int(data.get('quantity'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid quantity provided'}), 400

    if not all([user_id, product_id, quantity]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Add the item to the cart after successful stock update by Product service
    conn = sqlite3.connect(DATABASE)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO cart_items (user_id, product_id, product_name ,quantity)
            VALUES (?, ?, ?, ?)
        ''', (user_id, product_id, product_name ,quantity))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Failed to add item to cart: {str(e)}'}), 500     
    finally:
        conn.close()

    return jsonify({'message': 'Cart item added successfully'}), 201

@app.route('/cart/<int:item_id>', methods=['PUT'])
def update_cart_item(item_id):
    """
    UpdateCartItem API.
    Expects a JSON payload with the new quantity for the specified cart item.
    """
    data = request.get_json()
    quantity = data.get('quantity')
    if quantity is None:
        return jsonify({'error': 'Missing quantity field'}), 400

    conn = sqlite3.connect(DATABASE)
    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE cart_items SET quantity = ? WHERE id = ?', (quantity, item_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Failed to update cart item: {str(e)}'}), 500
    finally:
        conn.close()

    return jsonify({'message': 'Cart item updated successfully'}), 200

@app.route('/cart/<int:item_id>', methods=['DELETE'])
def delete_cart_item(item_id):
    """
    DeleteCartItem API.
    Deletes a cart item by its ID.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cart_items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Cart item deleted successfully'}), 200

if __name__ == '__main__':
    init_db()  # Ensure the database and table are set up before running the service
    app.run(debug=True, port=5002)
    