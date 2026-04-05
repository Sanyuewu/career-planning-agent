#!/usr/bin/env python3
"""下载项目所需的预训练模型"""
import os
import sys
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS = [
    {
        "name": "all-MiniLM-L6-v2",
        "source": "sentence-transformers/all-MiniLM-L6-v2",
        "description": "用于文本嵌入的语义相似度模型"
    }
]


def download_model(model_info: dict) -> bool:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("错误: 请先安装 sentence-transformers: pip install sentence-transformers")
        return False

    model_name = model_info["name"]
    model_source = model_info["source"]
    save_path = MODELS_DIR / model_name

    if save_path.exists():
        print(f"模型 {model_name} 已存在，跳过下载")
        return True

    print(f"正在下载模型: {model_name}")
    print(f"来源: {model_source}")
    print(f"目标路径: {save_path}")

    try:
        model = SentenceTransformer(model_source)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(str(save_path))
        print(f"✓ 模型 {model_name} 下载完成")
        return True
    except Exception as e:
        print(f"✗ 下载失败: {e}")
        return False


def main():
    print("=" * 50)
    print("预训练模型下载工具")
    print("=" * 50)
    print()

    success_count = 0
    for model_info in MODELS:
        print(f"\n[{model_info['description']}]")
        if download_model(model_info):
            success_count += 1
        print()

    print("=" * 50)
    print(f"下载完成: {success_count}/{len(MODELS)} 个模型成功")
    print("=" * 50)

    if success_count < len(MODELS):
        sys.exit(1)


if __name__ == "__main__":
    main()
