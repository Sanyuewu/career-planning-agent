# AI 职业规划智能体 - 后端
FROM python:3.12-slim

WORKDIR /app

# 设置内存优化环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖（精简版）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 分批安装 Python 依赖，减少内存峰值
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --timeout 300

# 复制代码
COPY app/ ./app/
COPY data/ ./data/
COPY scripts/ ./scripts/

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
