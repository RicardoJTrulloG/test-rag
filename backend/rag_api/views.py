import json
from typing import Iterator
from django.http import JsonResponse, StreamingHttpResponse, HttpRequest, HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .services.rag_provider import stream_answer
from .services.llm import stream_completion

def sse_format(event: str = None, data: dict | str = "") -> str:
    lines = []
    if event:
        lines.append(f"event: {event}")
    if isinstance(data, (dict, list)):
        payload = json.dumps(data, ensure_ascii=False)
    else:
        payload = str(data)
    for line in payload.splitlines() or [""]:
        lines.append(f"data: {line}")
    lines.append("")
    return "\n".join(lines) + "\n"

@api_view(["GET"])
@permission_classes([AllowAny])
def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})

@api_view(["POST"])
@permission_classes([AllowAny])  # cambia a IsAuthenticated cuando conectes JWT en el front
def query(request: HttpRequest) -> HttpResponse:
    body = request.data if hasattr(request, "data") else {}
    q = (body.get("query") or "").strip()
    if not q:
        return JsonResponse({"error": "query is required"}, status=400)
    regulation = body.get("regulation")
    version = body.get("version")
    stream = True if body.get("stream", True) else False

    if not stream:
        # modo no-stream: acumulamos
        chunks = []
        citations = None
        for ev in stream_answer(q, stream_completion, regulation, version):
            if ev["event"] == "delta":
                chunks.append(ev["data"])
            elif ev["event"] == "end":
                citations = ev["data"]["citations"]
        return JsonResponse({"query": q, "answer": "".join(chunks), "citations": citations})

    # SSE
    def gen() -> Iterator[bytes]:
        for ev in stream_answer(q, stream_completion, regulation, version):
            yield sse_format(ev["event"], ev["data"]).encode("utf-8")

    resp = StreamingHttpResponse(gen(), content_type="text/event-stream; charset=utf-8")
    resp["Cache-Control"] = "no-cache"
    return resp

@api_view(["POST"])
@permission_classes([AllowAny])
def obtain_token(request: HttpRequest) -> JsonResponse:
    from django.contrib.auth.models import User
    from rest_framework_simplejwt.tokens import RefreshToken
    username = (request.data.get("username") or "demo").strip()
    password = (request.data.get("password") or "demo").strip()
    user, _ = User.objects.get_or_create(username=username)
    if not user.has_usable_password():
        user.set_password(password)
        user.save()
    refresh = RefreshToken.for_user(user)
    return JsonResponse({"access": str(refresh.access_token), "refresh": str(refresh)})