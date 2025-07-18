from sqlalchemy.orm import Session
from models import Users, PasswordResetToken
from modules.auth_modules.auth_schemas import CreateUserRequest
from modules.auth_modules.auth_utils import get_password_hash
from datetime import datetime, timedelta
from uuid import uuid4

def get_user_by_username(db: Session, username: str):
    return db.query(Users).filter(Users.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(Users).filter(Users.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(Users).filter(Users.id == user_id).first()

def create_user(db: Session, user_data: CreateUserRequest):
    hashed_password = get_password_hash(user_data.password)
    db_user = Users(
        email=user_data.email,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        hashed_password=hashed_password,
        is_active=True,
        phone_number=user_data.phone_number
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def save_password_reset_token(db: Session, user_id: int) -> str:
    # Xóa các token cũ của người dùng này
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()
    db.commit()

    token = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=1) # Token hết hạn sau 1 giờ

    new_token_entry = PasswordResetToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(new_token_entry)
    db.commit()
    return token

def get_password_reset_token_entry(db: Session, token: str):
    return db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()

def delete_password_reset_token_entry(db: Session, token_entry: PasswordResetToken):
    db.delete(token_entry)
    db.commit()

def update_user_password(db: Session, user: Users, new_password: str):
    user.hashed_password = get_password_hash(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
