import os
from functools import lru_cache
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    # bge-m3 requiere trust_remote_code
    return SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu", trust_remote_code=True)

def embed_texts(texts: List[str]) -> np.ndarray:
    model = _get_model()
    # Normaliza para usar Distance.COSINE en Qdrant
    return model.encode(texts, batch_size=16, normalize_embeddings=True, convert_to_numpy=True)
