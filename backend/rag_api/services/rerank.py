# Placeholder para un reranker; por ahora devolvemos en el mismo orden del score.
# Puedes reemplazar por BAAI/bge-reranker-v2-m3 más adelante.
from typing import List, Dict
def rerank(hits: List[Dict], top_n: int = 8) -> List[Dict]:
    return hits[:top_n]
