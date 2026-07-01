# 后端 + 检索服务共用同一镜像（依赖相同），compose 中以不同 command 区分。
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production

# faiss-cpu / torch 运行所需的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖以利用层缓存
COPY requirements.txt .
RUN pip install -r requirements.txt

# 再拷贝源码；模型、GraphRAG vendor、原始数据等运行资产由部署环境挂载或下载
COPY . .

EXPOSE 8082
# 默认作为后端启动：先应用迁移，再起服务（检索服务在 compose 中覆盖 command）
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8082"]
