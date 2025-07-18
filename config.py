import os

# Lấy DATABASE_URL từ biến môi trường, nếu không có thì dùng giá trị mặc định
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:123456@localhost:5432/Todosapp")

# Lấy SECRET_KEY từ biến môi trường, nếu không có thì dùng giá trị mặc định
SECRET_KEY = os.getenv("SECRET_KEY", "e5944be1ea9d658a7dca1a52daa154c3844370a765e824127f34e8bf877a2cdc")

# Cấu hình email (cũng nên lấy từ biến môi trường)
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "luutiendat1811@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "dbodaxtewdwhrlmi")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587)) # Chuyển đổi sang int
