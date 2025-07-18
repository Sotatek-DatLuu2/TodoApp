from sqlalchemy.orm import Session
from models import Todos
from modules.todos_modules.todo_schemas import TodoRequest

def get_all_todos_for_user(db: Session, owner_id: int):
    return db.query(Todos).filter(Todos.owner_id == owner_id).all()

def get_todo_by_id_for_user(db: Session, todo_id: int, owner_id: int):
    return db.query(Todos).filter(Todos.id == todo_id).filter(Todos.owner_id == owner_id).first()

def create_new_todo(db: Session, todo_request: TodoRequest, owner_id: int):
    todo_model = Todos(**todo_request.dict(), owner_id=owner_id)
    db.add(todo_model)
    db.commit()
    db.refresh(todo_model)
    return todo_model

def update_existing_todo(db: Session, todo_model: Todos, todo_request: TodoRequest):
    todo_model.title = todo_request.title
    todo_model.description = todo_request.description
    todo_model.priority = todo_request.priority
    todo_model.complete = todo_request.complete
    db.add(todo_model)
    db.commit()
    db.refresh(todo_model)
    return todo_model

def delete_existing_todo(db: Session, todo_model: Todos):
    db.delete(todo_model)
    db.commit()
