"""
启动入口 — 基于AI的大学生职业规划智能体 v3.0
运行方式: python run.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8082,
        reload=False,
        log_level="info",
    )
