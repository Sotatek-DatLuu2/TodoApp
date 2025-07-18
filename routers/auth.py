from datetime import datetime, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette import status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
from database import SessionLocal
from modules.auth_modules.auth_schemas import (
    CreateUserRequest, Token, ForgotPasswordRequest,
    ResetPasswordRequest, ChangePasswordRequest
)
from modules.auth_modules.auth_utils import (
    verify_password, create_access_token, decode_access_token,
    send_password_reset_email
)
from modules.auth_modules.auth_crud import (
    get_user_by_username, get_user_by_email, create_user,
    save_password_reset_token, get_password_reset_token_entry,
    delete_password_reset_token_entry, update_user_password,
    get_user_by_id
)

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

templates = Jinja2Templates(directory="templates")


# --- Page Routes ---
@router.get("/login-page")
async def render_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register-page")
async def render_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.get("/forgot-password-page")
async def render_forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@router.get("/reset-password-page")
async def render_reset_password_page(request: Request):
    return templates.TemplateResponse("reset_password.html", {"request": request})

@router.get("/change-password-page")
async def render_change_password_page(request: Request):
    return templates.TemplateResponse("change_password.html", {"request": request})


# --- API Endpoints ---

def authenticate_user(username: str, password: str, db: Session):
    """
    Xác thực người dùng bằng tên đăng nhập và mật khẩu.
    """
    user = get_user_by_username(db, username)
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    """
    Lấy thông tin người dùng hiện tại từ token JWT.
    """
    return decode_access_token(token)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def register_user(db: db_dependency, create_user_request: CreateUserRequest):
    """
    Endpoint đăng ký người dùng mới.
    """
    if get_user_by_email(db, create_user_request.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Email already exists.')
    if get_user_by_username(db, create_user_request.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Username already exists.')

    try:
        create_user(db, create_user_request)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi đăng ký người dùng: {str(e)}"
        )
    return {"message": "User registered successfully."}


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: db_dependency):
    """
    Endpoint để lấy JWT access token.
    """
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Could not validate user.')
    token = create_access_token(user.username, user.id, user.role, timedelta(minutes=30))
    return {'access_token': token, 'token_type': 'bearer'}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password_endpoint(request: ForgotPasswordRequest, db: db_dependency):
    """
    Endpoint để yêu cầu đặt lại mật khẩu.
    """
    user = get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="If an account with that email exists, a password reset link has been sent.")

    token = save_password_reset_token(db, user.id)
    send_password_reset_email(user.email, user.first_name, token)

    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password_endpoint(request: ResetPasswordRequest, db: db_dependency):
    """
    Endpoint để đặt lại mật khẩu bằng token.
    """
    reset_token_entry = get_password_reset_token_entry(db, request.token)

    if not reset_token_entry or datetime.utcnow() > reset_token_entry.expires_at:
        if reset_token_entry: # Nếu token hết hạn, xóa nó đi
            delete_password_reset_token_entry(db, reset_token_entry)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token.")

    user = get_user_by_id(db, reset_token_entry.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    update_user_password(db, user, request.new_password)
    delete_password_reset_token_entry(db, reset_token_entry) # Xóa token sau khi sử dụng

    return {"message": "Password has been reset successfully."}


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password_endpoint(
    request: ChangePasswordRequest,
    db: db_dependency,
    current_user: Annotated[dict, Depends(get_current_user)]
):
    """
    Endpoint để thay đổi mật khẩu cho người dùng đã đăng nhập.
    """
    user_id = current_user.get("id")
    user = get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if not verify_password(request.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password.")

    update_user_password(db, user, request.new_password)

    return {"message": "Password has been changed successfully."}
