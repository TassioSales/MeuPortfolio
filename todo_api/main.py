from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import time
from app.database import insert_task, get_tasks, get_task, update_task, delete_task, create_table

app = FastAPI()

# Criar a tabela ao iniciar a aplicação
create_table()

class Task(BaseModel):
    id: Optional[int] = None
    title: str
    description: str
    status: str

@app.post("/tasks/", response_model=Task)
async def create_task(task: Task):
    # Simular um pequeno atraso para testar o indicador de carregamento
    time.sleep(1)
    
    result = insert_task(task.title, task.description, task.status)
    if result:
        return result
    raise HTTPException(status_code=500, detail="Error creating task")

@app.get("/tasks/", response_model=List[Task])
async def get_all_tasks():
    # Simular um pequeno atraso para testar o indicador de carregamento
    time.sleep(1)
    return get_tasks()

@app.get("/tasks/{task_id}", response_model=Task)
async def get_single_task(task_id: int):
    # Simular um pequeno atraso para testar o indicador de carregamento
    time.sleep(1)
    
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.put("/tasks/{task_id}", response_model=Task)
async def update_single_task(task_id: int, task: Task):
    # Simular um pequeno atraso para testar o indicador de carregamento
    time.sleep(1)
    
    result = update_task(task_id, task.title, task.description, task.status)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return result

@app.delete("/tasks/{task_id}")
async def delete_single_task(task_id: int):
    # Simular um pequeno atraso para testar o indicador de carregamento
    time.sleep(1)
    
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    delete_task(task_id)
    return {"message": "Task deleted successfully"} 