from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os

app = FastAPI()

def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        database=os.getenv("DB_NAME", "tasksdb"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres123")
    )

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            done BOOLEAN DEFAULT FALSE
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.on_event("startup")
def startup():
    init_db()

class Task(BaseModel):
    title: str
    done: bool = False

@app.get("/tasks")
def get_tasks():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, title, done FROM tasks ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "title": r[1], "done": r[2]} for r in rows]

@app.post("/tasks")
def create_task(task: Task):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id",
                (task.title, task.done))
    task_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {"id": task_id, "title": task.title, "done": task.done}

@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: Task):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET title=%s, done=%s WHERE id=%s",
                (task.title, task.done, task_id))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    conn.commit()
    cur.close()
    conn.close()
    return {"id": task_id, "title": task.title, "done": task.done}

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    conn.commit()
    cur.close()
    conn.close()
    return {"message": "Task deleted"}