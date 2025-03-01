import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from werkzeug.security import generate_password_hash

app = FastAPI()
DATABASE = os.path.join(os.getcwd(), 'online_store/db/online_store.db')
print(f"DB=={DATABASE}")

def init_db():
    db_dir = os.path.dirname(DATABASE)
    if not os.path.exists(db_dir):
        raise Exception(f"Database directory {db_dir} does not exist. Try run the service from the project root folder.")
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

# Pydantic models for request bodies
class AddUserRequest(BaseModel):
    firstName: str
    lastName: str
    userAlias: str
    password: str

class RemoveUserRequest(BaseModel):
    firstName: str
    lastName: str

class UpdateUserRequest(BaseModel):
    id: int
    firstName: str
    lastName: str
    userAlias: str
    password: str = None

@app.post("/users", status_code=201)
def add_user(user: AddUserRequest):
    if not all([user.firstName, user.lastName, user.userAlias, user.password]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    hashed_password = generate_password_hash(user.password)
    
    conn = sqlite3.connect(DATABASE)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (first_name, last_name, user_alias, password)
            VALUES (?, ?, ?, ?)
        ''', (user.firstName, user.lastName, user.userAlias, hashed_password))
        conn.commit()
        user_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:    
        conn.close()

    return JSONResponse(status_code=201, content={
        'id': user_id,
        'firstName': user.firstName,
        'lastName': user.lastName,
        'userAlias': user.userAlias
    })

@app.get("/users")
def get_users():
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

    return JSONResponse(content=users)

@app.delete("/users")
def remove_user(user: RemoveUserRequest):
    if not all([user.firstName, user.lastName]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    conn = sqlite3.connect(DATABASE)
    changes = 0
    try:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM users 
            WHERE first_name = ? AND last_name = ?
        ''', (user.firstName, user.lastName))
        conn.commit()
        changes = conn.total_changes
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    if changes == 0:
        raise HTTPException(status_code=404, detail="No user found with given firstName and lastName")
    else:
        return JSONResponse(content={'message': 'User removed successfully'})

@app.put("/users")
def update_user(user: UpdateUserRequest):
    if not user.id:
        raise HTTPException(status_code=400, detail="Missing user id")
    if not all([user.firstName, user.lastName, user.userAlias]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    conn = sqlite3.connect(DATABASE)
    try:    
        cursor = conn.cursor()
        if user.password:
            hashed_password = generate_password_hash(user.password)
            cursor.execute('''
                UPDATE users 
                SET first_name = ?, last_name = ?, user_alias = ?, password = ?
                WHERE id = ?
            ''', (user.firstName, user.lastName, user.userAlias, hashed_password, user.id))
        else:
            cursor.execute('''
                UPDATE users 
                SET first_name = ?, last_name = ?, user_alias = ?
                WHERE id = ?
            ''', (user.firstName, user.lastName, user.userAlias, user.id))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
         
    return JSONResponse(content={'message': 'User updated successfully'})

if __name__ == '__main__':
    init_db()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)