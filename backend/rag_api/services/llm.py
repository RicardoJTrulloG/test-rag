import os, json, requests
from typing import Iterator, Dict

PROVIDER = os.getenv("LLM_PROVIDER", "OLLAMA").upper()
LOCAL_LLM = os.getenv("LOCAL_LLM", "llama3.1:8b-instruct-q4_K_M")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SYS_PROMPT = (
    "Eres un asistente experto en reglamentos técnicos colombianos (RETIE, RETSIT, RETILAB, RETIQ). "
    "Responde en español formal, y CITA SIEMPRE con formato [n] incluyendo título/versión/sección/página. "
    "Si no hay evidencia suficiente en los fragmentos, dilo explícitamente."
)

def _format_messages(prompt: str, context: str):
    user = (
        "Pregunta:\n"
        f"{prompt}\n\n"
        "Contexto (fragmentos relevantes, cítalos):\n"
        f"{context}\n\n"
        "Instrucciones: Sé preciso, enumera referencias [1], [2], ... con sección/página."
    )
    return [{"role":"system","content":SYS_PROMPT},{"role":"user","content":user}]

def stream_ollama(prompt: str, context: str) -> Iterator[str]:
    url = "http://ollama:11434/api/chat"
    payload = {
        "model": LOCAL_LLM,
        "stream": True,
        "messages": _format_messages(prompt, context),
        "options": {"temperature": 0.2}
    }
    with requests.post(url, json=payload, stream=True, timeout=600) as r:
        r.raise_for_status()
        for ln in r.iter_lines():
            if not ln: 
                continue
            obj = json.loads(ln.decode("utf-8"))
            # formato de ollama streaming: { "message": {"role":"assistant","content":"..."}, "done": false }
            if "message" in obj and "content" in obj["message"]:
                yield obj["message"]["content"]
            if obj.get("done"):
                break

def stream_openai(prompt: str, context: str) -> Iterator[str]:
    import httpx
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    body = {
        "model": "gpt-4o-mini",
        "messages": _format_messages(prompt, context),
        "stream": True,
        "temperature": 0.2,
    }
    with httpx.stream("POST", "https://api.openai.com/v1/chat/completions", headers=headers, json=body, timeout=600.0) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line or not line.startswith("data: "): 
                continue
            chunk = line[6:]
            if chunk == "[DONE]":
                break
            data = json.loads(chunk)
            for c in data.get("choices", []):
                delta = c.get("delta", {}).get("content")
                if delta:
                    yield delta

def stream_gemini(prompt: str, context: str) -> Iterator[str]:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    sm = model.generate_content(_format_messages(prompt, context), stream=True)
    for ch in sm:
        if ch.text:
            yield ch.text

def stream_completion(prompt: str, context: str) -> Iterator[str]:
    p = PROVIDER
    if p == "OPENAI" and OPENAI_API_KEY:
        yield from stream_openai(prompt, context)
    elif p == "GEMINI" and GEMINI_API_KEY:
        yield from stream_gemini(prompt, context)
    else:
        yield from stream_ollama(prompt, context)