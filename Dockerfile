FROM python:3.13-slim

WORKDIR /app

# minimal deps from requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# project source (data 体积大, 用 .dockerignore 控制需要拷贝什么)
COPY backend ./backend
COPY scripts ./scripts
COPY frontend ./frontend
COPY data ./data

# build DB at image build time (idempotent, 3-5s)
RUN python3 scripts/init_db.py 2>&1 | tail -3

EXPOSE 8765
CMD ["python3", "backend/api/main.py", "--host", "0.0.0.0", "--port", "8765"]
