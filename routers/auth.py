from datetime import timedelta, datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from starlette import status
from database import SessionLocal
from models import Users, PasswordResetToken
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from fastapi.templating import Jinja2Templates
from uuid import uuid4
import smtplib
from email.mime.text import MIMEText
import config

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)


SECRET_KEY = config.SECRET_KEY
ALGORITHM = 'HS256'

# Cấu hình email server từ config.py
EMAIL_HOST = config.SMTP_HOST
EMAIL_PORT = config.SMTP_PORT
EMAIL_USERNAME = config.EMAIL_ADDRESS
EMAIL_PASSWORD = config.EMAIL_PASSWORD
EMAIL_FROM = config.EMAIL_ADDRESS

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str
    last_name: str
    password: str = Field(..., min_length=8)
    role: str
    phone_number: str


class Token(BaseModel):
    access_token: str
    token_type: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]

templates = Jinja2Templates(directory="templates")


# Pages
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


# Endpoints
def authenticate_user(username: str, password: str, db):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if user and not user.is_active:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency,
                      create_user_request: CreateUserRequest):
    if db.query(Users).filter(Users.email == create_user_request.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Email already exists.')
    if db.query(Users).filter(Users.username == create_user_request.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Username already exists.')

    create_user_model = Users(
        email=create_user_request.email,
        username=create_user_request.username,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        role=create_user_request.role,
        hashed_password=bcrypt_context.hash(create_user_request.password),
        is_active=True,
        phone_number=create_user_request.phone_number
    )
    try:
        db.add(create_user_model)
        db.commit()
        db.refresh(create_user_model)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lưu vào database: {str(e)}"
        )


def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id, 'role': role}
    expires = datetime.utcnow() + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: int = payload.get('id')
        user_role: str = payload.get('role')
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Could not validate user.')
        return {'username': username, 'id': user_id, 'user_role': user_role}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Could not validate user.')


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Could not validate user.')
    token = create_access_token(user.username, user.id, user.role, timedelta(minutes=30))
    return {'access_token': token, 'token_type': 'bearer'}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(request: ForgotPasswordRequest, db: db_dependency):
    user = db.query(Users).filter(Users.email == request.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="If an account with that email exists, a password reset link has been sent.")

    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
    db.commit()

    token = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=1)

    new_token_entry = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    db.add(new_token_entry)
    db.commit()

    reset_link = f"http://localhost:8000/auth/reset-password-page?token={token}"
    subject = "Password Reset Request"
    body = f"""
       Hello {user.first_name},

       You have requested to reset your password.
       Please click on the link below to reset your password:

       {reset_link}

       If the link does not work, you can copy the token below and paste it into the 'Token' field on the reset password page:
       Token: {token}

       This link and token will expire in 1 hour.
       If you did not request a password reset, please ignore this email.

       Thanks,
       Your App Team
       """

    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = user.email

        if EMAIL_PORT == 587:
            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT)

        with server:
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Error sending email: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to send password reset email. Please try again later.")

    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(request: ResetPasswordRequest, db: db_dependency):
    reset_token_entry = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token
    ).first()

    if not reset_token_entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token.")

    if datetime.utcnow() > reset_token_entry.expires_at:
        db.delete(reset_token_entry)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token.")

    user = db.query(Users).filter(Users.id == reset_token_entry.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.hashed_password = bcrypt_context.hash(request.new_password)
    db.add(user)
    db.delete(reset_token_entry)
    db.commit()

    return {"message": "Password has been reset successfully."}


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    request: ChangePasswordRequest,
    db: db_dependency,
    current_user: Annotated[dict, Depends(get_current_user)]
):
    user_id = current_user.get("id")
    user = db.query(Users).filter(Users.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if not bcrypt_context.verify(request.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password.")

    user.hashed_password = bcrypt_context.hash(request.new_password)
    db.add(user)
    db.commit()

    return {"message": "Password has been changed successfully."}
