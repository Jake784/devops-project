from fastapi import FastAPI, HTTPException, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import os
import hashlib
import secrets

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = {}

def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        database=os.getenv("DB_NAME", "tasksdb"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres123")
    )

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Tabla de usuarios
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabla de tareas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            done BOOLEAN DEFAULT FALSE
        )
    """)

    # Insertar usuario admin por defecto si no existe
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            ("admin", hash_password("admin123"))
        )

    conn.commit()
    cur.close()
    conn.close()

@app.on_event("startup")
def startup():
    init_db()

# ── Models ──────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class Task(BaseModel):
    title: str
    done: bool = False

# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post("/login")
def login(data: LoginRequest, response: Response):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username FROM users WHERE username=%s AND password=%s",
        (data.username, hash_password(data.password))
    )
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    # Close session if already exists
    token = secrets.token_hex(32)
    sessions[token] = {"id": user[0], "username": user[1]}

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        max_age=3600
    )
    return {"message": "Login exitoso", "username": user[1]}

@app.post("/logout")
def logout(response: Response, session: str = Cookie(default=None)):
    if session and session in sessions:
        del sessions[session]
    response.delete_cookie("session")
    return {"message": "Logout exitoso"}

@app.get("/me")
def me(session: str = Cookie(default=None)):
    if not session or session not in sessions:
        raise HTTPException(status_code=401, detail="No autenticado")
    return sessions[session]

# ── Tasks endpoints ───────────────────────────────────────────────────────────

def require_auth(session: str = None):
    if not session or session not in sessions:
        raise HTTPException(status_code=401, detail="No autenticado")
    return sessions[session]

@app.get("/tasks")
def get_tasks(session: str = Cookie(default=None)):
    require_auth(session)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, title, done FROM tasks ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "title": r[1], "done": r[2]} for r in rows]

@app.post("/tasks")
def create_task(task: Task, session: str = Cookie(default=None)):
    require_auth(session)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id",
        (task.title, task.done)
    )
    task_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {"id": task_id, "title": task.title, "done": task.done}

@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: Task, session: str = Cookie(default=None)):
    require_auth(session)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tasks SET title=%s, done=%s WHERE id=%s",
        (task.title, task.done, task_id)
    )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    conn.commit()
    cur.close()
    conn.close()
    return {"id": task_id, "title": task.title, "done": task.done}

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, session: str = Cookie(default=None)):
    require_auth(session)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    conn.commit()
    cur.close()
    conn.close()
    return {"message": "Tarea eliminada"}