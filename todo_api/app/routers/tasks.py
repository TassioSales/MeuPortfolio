# app/routers/tasks.py
from fastapi import APIRouter, HTTPException
from ..schemas import Task, TaskCreate, TaskUpdate
from ..crud import TaskRepository

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=Task)
def create_new_task(task: TaskCreate):
    return TaskRepository.create_task(task)

@router.get("/", response_model=list[Task])
def list_tasks():
    return TaskRepository.get_tasks()

@router.get("/{task_id}", response_model=Task)
def get_task(task_id: int):
    task = TaskRepository.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.put("/{task_id}", response_model=Task)
def update_task(task_id: int, task: TaskUpdate):
    updated_task = TaskRepository.update_task(task_id, task)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated_task

@router.delete("/{task_id}")
def delete_task(task_id: int):
    if not TaskRepository.get_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    TaskRepository.delete_task(task_id)
    return {"message": "Task deleted successfully"}