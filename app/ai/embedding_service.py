# -*- coding: utf-8 -*-
"""
向量嵌入服务
优先使用本地 ONNX 量化模型（qint8_avx512），加快推理速度并减少内存占用。
加入文本级 MD5 缓存，避免相同文本重复计算。
"""

import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# 量化 ONNX 文件的相对路径（优先顺序）
_ONNX_CANDIDATES = [
    "onnx/model_qint8_avx512.onnx",   # AVX-512 量化，最小最快
    "onnx/model_qint8_avx512_vnni.onnx",
    "onnx/model_quint8_avx2.onnx",
    "onnx/model_O2.onnx",              # 优化但未量化
    "onnx/model.onnx",                 # 原始 ONNX
]


class EmbeddingService:
    """
    向量嵌入服务（懒加载 + MD5缓存）
    加载优先级：ONNX量化版 > sentence-transformers
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = 384
        self._embed_cache: Dict[str, np.ndarray] = {}  # O3-b: 文本向量缓存

    @property
    def model(self):
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self):
        model_dir = Path(__file__).parent.parent.parent / "models" / self.model_name

        # 优先尝试 ONNX 量化版（通过 sentence-transformers 的 ONNX 后端）
        if model_dir.exists():
            for onnx_rel in _ONNX_CANDIDATES:
                onnx_path = model_dir / onnx_rel
                if onnx_path.exists():
                    try:
                        from sentence_transformers import SentenceTransformer
                        self._model = SentenceTransformer(
                            str(model_dir),
                            backend="onnx",
                            model_kwargs={"file_name": onnx_rel},
                        )
                        self._dimension = self._model.get_sentence_embedding_dimension()
                        logger.info("嵌入模型加载成功(ONNX量化): %s → %s, 维度=%d",
                                    self.model_name, onnx_rel, self._dimension)
                        return
                    except Exception as e:
                        logger.debug("ONNX加载失败(%s)，尝试下一个: %s", onnx_rel, e)

        # 降级：sentence-transformers 普通加载
        try:
            from sentence_transformers import SentenceTransformer
            src = str(model_dir) if model_dir.exists() else self.model_name
            self._model = SentenceTransformer(src)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info("嵌入模型加载成功(PyTorch): %s, 维度=%d", src, self._dimension)
        except Exception as e:
            logger.warning("嵌入模型加载失败，将使用 Mock 向量: %s", e)
            self._model = None

    def _cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def embed(self, text: str) -> np.ndarray:
        key = self._cache_key(text)
        if key in self._embed_cache:
            return self._embed_cache[key]

        if self.model is None:
            vec = self._mock_embed(text)
        else:
            try:
                vec = self.model.encode(text, normalize_embeddings=True)
            except Exception as e:
                logger.warning("向量化失败: %s", e)
                vec = self._mock_embed(text)

        self._embed_cache[key] = vec
        return vec

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        keys = [self._cache_key(t) for t in texts]
        miss_idx = [i for i, k in enumerate(keys) if k not in self._embed_cache]

        if miss_idx:
            miss_texts = [texts[i] for i in miss_idx]
            if self.model is None:
                miss_vecs = np.array([self._mock_embed(t) for t in miss_texts])
            else:
                try:
                    miss_vecs = self.model.encode(miss_texts, normalize_embeddings=True)
                except Exception as e:
                    logger.warning("批量向量化失败: %s", e)
                    miss_vecs = np.array([self._mock_embed(t) for t in miss_texts])
            for i, idx in enumerate(miss_idx):
                self._embed_cache[keys[idx]] = miss_vecs[i]

        return np.array([self._embed_cache[k] for k in keys])

    def _mock_embed(self, text: str) -> np.ndarray:
        np.random.seed(hash(text) % (2 ** 32))
        vec = np.random.randn(self._dimension).astype(np.float32)
        return vec / np.linalg.norm(vec)

    def compute_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        n1, n2 = np.linalg.norm(vec1), np.linalg.norm(vec2)
        if n1 == 0 or n2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (n1 * n2))

    def find_similar(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5,
        threshold: float = 0.85,
    ) -> List[Tuple[str, float]]:
        if not candidates:
            return []
        q_vec = self.embed(query)
        c_vecs = self.embed_batch(candidates)
        results = [
            (c, self.compute_similarity(q_vec, c_vecs[i]))
            for i, c in enumerate(candidates)
            if self.compute_similarity(q_vec, c_vecs[i]) >= threshold
        ]
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    @property
    def dimension(self) -> int:
        return self._dimension


embedding_service = EmbeddingService()
