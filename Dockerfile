# ============================================================
# Stage 1: 构建前端
# ============================================================
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ============================================================
# Stage 2: 后端 + 静态文件
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（MySQL 客户端库 + 中文字体 for PDF）
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 后端代码
COPY backend/ .

# 前端构建产物（main.py 期望 FRONTEND_DIR = ../frontend/dist 相对于 main.py）
COPY --from=frontend-builder /frontend/dist /frontend/dist

# 启动脚本
COPY backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
