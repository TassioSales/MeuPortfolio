# app/crud.py
from .database import insert_task, get_tasks, get_task, update_task, delete_task
from .schemas import TaskCreate, TaskUpdate

class TaskRepository:
    @staticmethod
    def create_task(task: TaskCreate):
        return insert_task(task.title, task.description, task.status)

    @staticmethod
    def get_tasks():
        return get_tasks()

    @staticmethod
    def get_task(task_id: int):
        return get_task(task_id)

    @staticmethod
    def update_task(task_id: int, task: TaskUpdate):
        existing_task = TaskRepository.get_task(task_id)
        if not existing_task:
            return None
        updated_data = {**existing_task, **task.model_dump(exclude_unset=True)}
        return update_task(task_id, updated_data["title"], updated_data["description"], updated_data["status"])

    @staticmethod
    def delete_task(task_id: int):
        delete_task(task_id)
        return True