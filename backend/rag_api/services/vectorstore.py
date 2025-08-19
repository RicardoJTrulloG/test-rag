import os
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, Filter, FieldCondition, MatchValue

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "reglamentos")  # nombre por defecto
EMBED_DIM = 1024  # bge-m3 = 1024

_client: QdrantClient = None

def client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL, timeout=30)
    return _client

def ensure_collection():
    c = client()
    if not c.collection_exists(COLLECTION):
        c.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )

def make_filter(regulation: Optional[str]=None, version: Optional[str]=None) -> Optional[Filter]:
    conditions = []
    if regulation:
        conditions.append(FieldCondition(key="regulation", match=MatchValue(value=regulation)))
    if version:
        conditions.append(FieldCondition(key="version", match=MatchValue(value=version)))
    if not conditions:
        return None
    return Filter(must=conditions)

def search(query_vec, top_k=50, regulation: str=None, version: str=None):
    ensure_collection()
    qf = make_filter(regulation, version)
    return client().search(
        collection_name=COLLECTION,
        query_vector=query_vec,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
        query_filter=qf,
    )