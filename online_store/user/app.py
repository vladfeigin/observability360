
#start the service from the project root folder
#python ./online_store/user/app.py
import os
import sqlite3
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash

app = Flask(__name__)
DATABASE = os.path.join(os.getcwd(), 'online_store/db/online_store.db')
print(f"DB=={DATABASE}")

def init_db():
    
    db_dir = os.path.dirname(DATABASE)
    if not os.path.exists(db_dir):
        raise Exception(f"Database directory {db_dir} does not exist. Try run the service from the project root folder.")
        
    """Initialize the SQLite database and create the users table if it doesn't exist."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            user_alias TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/users', methods=['POST'])
def add_user():
    """
    AddUser API.
    Expects a JSON payload with: firstName, lastName, userAlias, password.
    Returns the created user's details (excluding the password).
    """
    data = request.get_json()
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    user_alias = data.get('userAlias')
    password = data.get('password')
    
    if not all([first_name, last_name, user_alias, password]):
        return jsonify({'error': 'Missing required fields'}), 400

    hashed_password = generate_password_hash(password)
    
    conn = sqlite3.connect(DATABASE)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (first_name, last_name, user_alias, password)
            VALUES (?, ?, ?, ?)
        ''', (first_name, last_name, user_alias, hashed_password))
        conn.commit()
        user_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:    
        conn.close()

    return jsonify({
        'id': user_id,
        'firstName': first_name,
        'lastName': last_name,
        'userAlias': user_alias
    }), 201

@app.route('/users', methods=['GET'])
def get_users():
    """
    GetUsers API.
    Returns a list of all users.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT id, first_name, last_name, user_alias FROM users')
    rows = cursor.fetchall()
    conn.close()

    users = []
    for row in rows:
        users.append({
            'id': row['id'],
            'firstName': row['first_name'],
            'lastName': row['last_name'],
            'userAlias': row['user_alias']
        })

    return jsonify(users), 200

@app.route('/users', methods=['DELETE'])
def remove_user():
    """
    RemoveUser API.
    Expects a JSON payload with: firstName, lastName.
    Deletes user(s) matching the given names.
    """
    data = request.get_json()
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    
    if not all([first_name, last_name]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    
    conn = sqlite3.connect(DATABASE)
    changes = 0
    try:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM users 
            WHERE first_name = ? AND last_name = ?
        ''', (first_name, last_name))
        conn.commit()
        changes = conn.total_changes
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

    if changes == 0:
        return jsonify({'error': 'No user found with given firstName and lastName'}), 404
    else:
        return jsonify({'message': 'User removed successfully'}), 200

@app.route('/users', methods=['PUT'])
def update_user():
    """
    UpdateUser API.
    Expects a JSON payload with: id, firstName, lastName, userAlias, and optional password.
    Updates the user's details.
    """
    data = request.get_json()
    user_id = data.get('id')
    if not user_id:
        return jsonify({'error': 'Missing user id'}), 400

    first_name = data.get('firstName')
    last_name = data.get('lastName')
    user_alias = data.get('userAlias')
    password = data.get('password')
    
    if not all([first_name, last_name, user_alias]):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = sqlite3.connect(DATABASE)
    try:    
        cursor = conn.cursor()
        if password:
            hashed_password = generate_password_hash(password)
            cursor.execute('''
                UPDATE users 
                SET first_name = ?, last_name = ?, user_alias = ?, password = ?
                WHERE id = ?
            ''', (first_name, last_name, user_alias, hashed_password, user_id))
        else:
            cursor.execute('''
                UPDATE users 
                SET first_name = ?, last_name = ?, user_alias = ?
                WHERE id = ?
            ''', (first_name, last_name, user_alias, user_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
         if cursor.rowcount == 0:
            return jsonify({'error': 'User not found'}), 404
         conn.close()
         
    return jsonify({'message': 'User updated successfully'}), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)