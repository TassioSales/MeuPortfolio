# app/database.py
import sqlite3
import random
import threading

# Thread-local storage for database connections
thread_local = threading.local()

def get_db():
    if not hasattr(thread_local, "db"):
        thread_local.db = sqlite3.connect('tasks.db')
        thread_local.cursor = thread_local.db.cursor()
    return thread_local.db, thread_local.cursor

def generate_random_id():
    return random.randint(10000000, 99999999)

def create_table():
    db, cursor = get_db()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL
        )
    ''')
    db.commit()

def insert_task(title, description, status):
    db, cursor = get_db()
    # Gerar ID aleatório único
    while True:
        task_id = generate_random_id()
        cursor.execute('SELECT id FROM tasks WHERE id = ?', (task_id,))
        if not cursor.fetchone():
            break
    
    cursor.execute('''
        INSERT INTO tasks (id, title, description, status)
        VALUES (?, ?, ?, ?)
    ''', (task_id, title, description, status))
    
    db.commit()
    task = get_task(task_id)
    return task

def get_tasks():
    db, cursor = get_db()
    cursor.execute('SELECT * FROM tasks')
    tasks = []
    for row in cursor.fetchall():
        tasks.append({
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'status': row[3]
        })
    return tasks

def get_task(task_id):
    db, cursor = get_db()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    
    if row:
        return {
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'status': row[3]
        }
    return None

def update_task(task_id, title, description, status):
    db, cursor = get_db()
    cursor.execute('''
        UPDATE tasks
        SET title = ?, description = ?, status = ?
        WHERE id = ?
    ''', (title, description, status, task_id))
    db.commit()
    task = get_task(task_id)
    return task

def delete_task(task_id):
    db, cursor = get_db()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db.commit()

# Criar a tabela ao importar o módulo
create_table()
