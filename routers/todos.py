from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from database import SessionLocal
from models import Todos
# Import từ các module mới tạo
from modules.todos_modules.todo_schemas import TodoRequest
from modules.todos_modules.todo_crud import (
    get_all_todos_for_user, get_todo_by_id_for_user,
    create_new_todo, update_existing_todo, delete_existing_todo
)
from routers.auth import get_current_user

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/todos",
    tags=["todos"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def redirect_to_login():
    """
    Hàm tiện ích để chuyển hướng người dùng đến trang đăng nhập và xóa cookie.
    """
    redirect_response = RedirectResponse(url="/auth/login-page", status_code=status.HTTP_302_FOUND)
    redirect_response.delete_cookie(key='access_token')
    return redirect_response


### Pages ###

@router.get("/todo-page")
async def render_todo_page(request: Request, db: db_dependency):
    """
    Render trang hiển thị danh sách Todos của người dùng.
    """
    try:
        user = await get_current_user(request.cookies.get('access_token'))
        if user is None:
            return redirect_to_login()

        todos = get_all_todos_for_user(db, user.get('id'))
        return templates.TemplateResponse("todo.html", {"request": request, "todos": todos, "user": user})
    except HTTPException as e: # Bắt HTTPException từ get_current_user
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            return redirect_to_login()
        raise # Re-raise other HTTPExceptions
    except Exception: # Bắt các lỗi khác
        return redirect_to_login()


@router.get("/add-todo-page")
async def render_add_todo_page(request: Request, db: db_dependency):
    """
    Render trang thêm Todo mới.
    """
    try:
        user = await get_current_user(request.cookies.get('access_token'))
        if user is None:
            return redirect_to_login()

        return templates.TemplateResponse("add-todo.html", {"request": request, "user": user})
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            return redirect_to_login()
        raise
    except Exception:
        return redirect_to_login()


@router.get("/edit-todo-page/{todo_id}")
async def render_edit_todo_page(request: Request, db: db_dependency, todo_id: int):
    """
    Render trang chỉnh sửa Todo.
    """
    try:
        user = await get_current_user(request.cookies.get('access_token'))
        if user is None:
            return redirect_to_login()

        todo = get_todo_by_id_for_user(db, todo_id, user.get('id'))
        if todo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or not owned by user.")

        return templates.TemplateResponse("edit-todo.html",
                                          {"request": request, "todo": todo, "user": user}
                                          )
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            return redirect_to_login()
        raise
    except Exception:
        return redirect_to_login()


### API Endpoints ###
@router.get("/", status_code=status.HTTP_200_OK)
async def read_all_todos(user: user_dependency, db: db_dependency):
    """
    Lấy tất cả Todos của người dùng hiện tại.
    """
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication Failed')
    return get_all_todos_for_user(db, user.get('id'))


@router.get("/todo/{todo_id}", status_code=status.HTTP_200_OK)
async def read_single_todo(user: user_dependency,
                           db: db_dependency,
                           todo_id: int = Path(gt=0)):
    """
    Lấy một Todo cụ thể của người dùng hiện tại.
    """
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication Failed')

    todo_model = get_todo_by_id_for_user(db, todo_id, user.get('id'))
    if todo_model is not None:
        return todo_model
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found.")


@router.post("/todo", status_code=status.HTTP_201_CREATED)
async def create_todo_item(user: user_dependency,
                           db: db_dependency,
                           todo_request: TodoRequest):
    """
    Tạo một Todo mới cho người dùng hiện tại.
    """
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication Failed')
    create_new_todo(db, todo_request, user.get('id'))
    return {"message": "Todo created successfully."} # Thêm phản hồi thành công


@router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo_item(user: user_dependency,
                           db: db_dependency,
                           todo_id: int,
                           todo_request: TodoRequest):
    """
    Cập nhật một Todo hiện có của người dùng hiện tại.
    """
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication Failed')

    todo_model = get_todo_by_id_for_user(db, todo_id, user.get('id'))
    if todo_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found.")

    update_existing_todo(db, todo_model, todo_request)


@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo_item(user: user_dependency,
                           db: db_dependency, todo_id: int = Path(gt=0)):
    """
    Xóa một Todo của người dùng hiện tại.
    """
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication Failed')

    todo_model = get_todo_by_id_for_user(db, todo_id, user.get('id'))
    if todo_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found.")

    delete_existing_todo(db, todo_model)
