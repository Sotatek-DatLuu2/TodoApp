from datetime import timedelta, datetime
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status
import smtplib
from email.mime.text import MIMEText
from uuid import uuid4
import config

# Cấu hình JWT
SECRET_KEY = config.SECRET_KEY
ALGORITHM = 'HS256'

# Cấu hình Email
EMAIL_HOST = config.SMTP_HOST
EMAIL_PORT = config.SMTP_PORT
EMAIL_USERNAME = config.EMAIL_ADDRESS
EMAIL_PASSWORD = config.EMAIL_PASSWORD
EMAIL_FROM = config.EMAIL_ADDRESS

# Cấu hình Bcrypt
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Xác minh mật khẩu thường với mật khẩu đã băm.
    """
    return bcrypt_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Băm mật khẩu.
    """
    return bcrypt_context.hash(password)

def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta) -> str:
    """
    Tạo JWT access token.
    """
    encode = {'sub': username, 'id': user_id, 'role': role}
    expires = datetime.utcnow() + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    """
    Giải mã JWT access token.
    """
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

def send_password_reset_email(email_to: str, user_first_name: str, token: str):
    """
    Gửi email chứa liên kết đặt lại mật khẩu.
    """
    reset_link = f"http://localhost:8000/auth/reset-password-page?token={token}" # Thay đổi domain nếu deploy
    subject = "Password Reset Request"
    body = f"""
    Hello {user_first_name},

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
        msg['To'] = email_to

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
