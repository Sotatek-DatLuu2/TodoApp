FROM python:3.12

WORKDIR /app


COPY requirements.txt .


RUN uv pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000


CMD ["uvicorn", "main:app", "--port", "8000"]


