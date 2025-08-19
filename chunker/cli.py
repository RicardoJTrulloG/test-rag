import os, hashlib, uuid, json
from pathlib import Path
from typing import List, Tuple
import typer
import mammoth
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

app = typer.Typer(add_completion=False)

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "reglamentos")
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024  # bge-m3

def load_model():
    return SentenceTransformer(EMBED_MODEL, device="cpu", trust_remote_code=True)

def ensure_collection(client: QdrantClient):
    if not client.collection_exists(COLLECTION):
        client.create_collection(COLLECTION, vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE))

def checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def chunk_html(html: str, max_chars=2500, overlap=300) -> List[Tuple[str, str, str]]:
    """
    Devuelve lista de (section_path, text, section_label)
    Heurística: corta por headings h1/h2/h3 y empaqueta párrafos hasta max_chars.
    """
    soup = BeautifulSoup(html, "html.parser")
    buffers = []
    path = []
    buf = ""
    section = ""

    def flush():
        nonlocal buf, section
        if buf.strip():
            buffers.append((" > ".join(path), buf.strip(), section))
            if overlap and len(buf) > overlap:
                buf = buf[-overlap:]
            else:
                buf = ""
        else:
            buf = ""

    for el in soup.find_all(["h1","h2","h3","p","li","table","pre","code"]):
        if el.name in ("h1","h2","h3"):
            flush()
            level = int(el.name[1])
            # recorta path
            path[:] = path[:level-1]
            section = el.get_text(strip=True)
            path.append(section)
        else:
            txt = el.get_text(separator=" ", strip=True)
            if not txt:
                continue
            if len(buf) + len(txt) + 1 > max_chars:
                flush()
            buf += ("\n" if buf else "") + txt
    flush()
    return buffers

@app.command()
def ingest(doc: str = typer.Option(..., help="Ruta al .docx"),
           regulation: str = typer.Option(...),
           version: str = typer.Option(...),
           title: str = typer.Option(None, help="Título legible (opcional)")):
    p = Path(doc)
    assert p.exists(), f"No existe: {p}"
    raw = p.read_bytes()
    doc_sha = checksum_bytes(raw)
    r = mammoth.convert_to_html(raw)
    html = r.value
    chunks = chunk_html(html)

    model = load_model()
    texts = [c[1] for c in chunks]
    vecs = model.encode(texts, batch_size=16, normalize_embeddings=True, convert_to_numpy=True)

    cli = QdrantClient(url=QDRANT_URL, timeout=60)
    ensure_collection(cli)

    pts = []
    for i, ((path, text, section), vec) in enumerate(zip(chunks, vecs)):
        pid = str(uuid.uuid4())
        payload = {
            "doc_sha": doc_sha,
            "title": title or p.stem,
            "regulation": regulation,
            "version": version,
            "section": section,
            "path": path,
            "page": None,  # docx no tiene páginas; si luego conviertes a PDF, puedes ponerlo aquí
            "text": text,
        }
        pts.append(PointStruct(id=pid, vector=vec.tolist(), payload=payload))

    # upsert en lotes
    B = 128
    for i in range(0, len(pts), B):
        cli.upsert(collection_name=COLLECTION, points=pts[i:i+B])
    print(json.dumps({"ok": True, "points": len(pts), "doc": p.name}))
