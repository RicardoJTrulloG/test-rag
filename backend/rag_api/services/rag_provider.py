from typing import Iterator, Dict, List
from .embeddings import embed_texts
from .vectorstore import search
from .rerank import rerank

def _build_context(snippets: List[Dict]) -> str:
    lines = []
    for i, sn in enumerate(snippets, 1):
        p = sn.get("payload", {})
        title = p.get("title") or p.get("regulation") or "Fuente"
        version = p.get("version", "")
        section = p.get("section", "")
        page = p.get("page", "")
        text = p.get("text", "")
        head = f"[{i}] {title} {version} — {section} p.{page}".strip()
        lines.append(head + "\n" + text)
    return "\n\n".join(lines)

def retrieve(query: str, top_k=50, regulation=None, version=None) -> List[Dict]:
    qvec = embed_texts([query])[0]
    hits = search(qvec, top_k=top_k, regulation=regulation, version=version)
    # normalizamos a dicts sencillos
    items = []
    for h in hits:
        items.append({
            "id": h.id,
            "score": h.score,
            "payload": h.payload or {},
        })
    return items

def stream_answer(query: str, provider_stream, regulation=None, version=None) -> Iterator[Dict]:
    # 1) retrieve
    hits = retrieve(query, top_k=50, regulation=regulation, version=version)
    # 2) rerank -> top 8
    top = rerank(hits, top_n=8)
    # 3) contexto
    context = _build_context(top)
    # 4) stream modelo
    yield {"event":"begin", "data":{"query": query, "n_citations": len(top)}}
    buff = ""
    for tok in provider_stream(query, context):
        buff += tok
        yield {"event":"delta", "data": tok}
    # 5) fin con citas
    citations = []
    for i, sn in enumerate(top, 1):
        p = sn["payload"]
        citations.append({
            "n": i,
            "title": p.get("title"),
            "regulation": p.get("regulation"),
            "version": p.get("version"),
            "section": p.get("section"),
            "page": p.get("page"),
            "score": sn["score"],
            "chunk_id": sn["id"],
        })
    yield {"event":"end", "data":{"citations": citations}}