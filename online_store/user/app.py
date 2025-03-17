import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from werkzeug.security import generate_password_hash
import logging
from online_store.otel.otel import configure_telemetry

SERVICE_VERSION = "1.0.0"

app = FastAPI()
instruments = configure_telemetry(app, "User Service", SERVICE_VERSION)

# Get instruments
meter = instruments["meter"]
tracer = instruments["tracer"]
logger = instruments["logger"]

# Create metrics instruments
request_counter = meter.create_counter(
    name="http_requests_total",
    description="Total number of HTTP requests to the user service",
    unit="1"
)

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
    
    request_counter.add(1, attributes={"route": "/users", "method": "POST" })
    hashed_password = generate_password_hash(user.password)
    
    with tracer.start_as_current_span("add_user") as span:
        span.set_attribute("user.first_name", user.firstName)
        span.set_attribute("user.last_name", user.lastName)
        span.set_attribute("user.user_alias", user.userAlias)
        
        logger.info(f"Adding user: {user.firstName} {user.lastName} with alias {user.userAlias}")
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
    request_counter.add(1, attributes={"route": "/users", "method": "GET"})
    with tracer.start_as_current_span("get_users") as span:
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
    request_counter.add(1, attributes={"route": "/users", "method": "DELETE"})
    
    with tracer.start_as_current_span("remove_user") as span:
        span.set_attribute("user.first_name", user.firstName)
        span.set_attribute("user.last_name", user.lastName)
        logger.info(f"Removing user: {user.firstName} {user.lastName}")
        
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

    request_counter.add(1, attributes={"route": "/users", "method": "PUT"}) 
    with tracer.start_as_current_span("update_user") as span:
        span.set_attribute("user.id", user.id)
        span.set_attribute("user.first_name", user.firstName)
        span.set_attribute("user.last_name", user.lastName)
        span.set_attribute("user.user_alias", user.userAlias)
        
        logger.info(f"Updating user: {user.id} {user.firstName} {user.lastName} with alias {user.userAlias}")
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
#start the service run from the project root folder: python -m online_store.user.app
if __name__ == '__main__':
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)