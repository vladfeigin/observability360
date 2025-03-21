# db_initializer.py
import sqlite3
import os

def initialize_db(db_path: str, sql_file_path: str):
    """
    Initializes the SQLite database by running the SQL script.
    """
    # Check if the database file already exists (if needed)
    if not os.path.exists(db_path):
        print(f"Creating new database at {db_path}.")
    else:
        print(f"Database {db_path} already exists. Running initialization script might update it.")

    # Open connection and execute SQL script
    with sqlite3.connect(db_path) as conn:
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_script = file.read()
        conn.executescript(sql_script)
    print("Database initialization completed.")