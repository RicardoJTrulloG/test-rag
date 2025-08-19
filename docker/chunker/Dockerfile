FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr poppler-utils libmagic1 curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY docker/chunker/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY chunker/ /app/
ENTRYPOINT ["/bin/sh","-c"]
CMD ["tail -f /dev/null"]
