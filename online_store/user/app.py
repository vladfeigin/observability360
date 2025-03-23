import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from werkzeug.security import generate_password_hash
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
    name="user_srv_http_requests_total",
    description="Total number of HTTP requests to the user service",
    unit="1"
)

DATABASE = os.path.join(os.getcwd(), 'online_store/db/online_store.db')
print(f"DB=={DATABASE}")

def init_db():
    logger.info("Initializing User service database...")
    db_dir = os.path.dirname(DATABASE)
    if not os.path.exists(db_dir):
        raise Exception(f"Database directory {db_dir} does not exist. Try run the service from the project root folder.")
    
    with tracer.start_as_current_span("init_db for User service") as span:
        logger.info("Creating database connection...")
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL UNIQUE,
                    user_alias TEXT NOT NULL,
                    password TEXT NOT NULL
                )
            ''')
            conn.commit()
            
            # Load and execute the SQL script from 'populate_users.sql'
            sql_file_path = os.path.join(os.path.dirname(__file__), 'populate_users.sql')
            if not os.path.exists(sql_file_path):
                logger.error("SQL init users file not found: %s", sql_file_path)
                raise HTTPException(status_code=500, detail="SQL init users file not found")
            with open(sql_file_path, 'r') as file:
                script_content = file.read()
            cursor.executescript(script_content)
            conn.commit()
        except sqlite3.Error as e:
            logger.error("Error initializing database: %s", e)
            raise HTTPException(status_code=500, detail="User database initialization failed") from e
        finally:
            conn.close()
        
        span.add_event("User service database initialized successfully.")
        logger.info("Database initialized successfully.")
        

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
        logger.error("Missing required fields in request body for adding user.")
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
            logger.error(f"Error adding user: {e}")
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
    logger.info("Fetching all users")
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
        logger.error("Missing required fields in request body for removing user.")
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
            logger.error(f"Error removing user: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()

        if changes == 0:
            logger.error(f"No user found with name: {user.firstName} {user.lastName}", exec_info=True) 
            raise HTTPException(status_code=404, detail="No user found with given firstName and lastName")
        else:
            return JSONResponse(content={'message': 'User removed successfully'})

@app.put("/users")
def update_user(user: UpdateUserRequest):
    if not user.id:
        logger.error("Missing user id in request body for updating user.")
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
                logger.error("No user found with id: %s", user.id)
                raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            logger.error(f"Error updating user: {e}")
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
    