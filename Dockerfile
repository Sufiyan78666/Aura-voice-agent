FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    ghostscript \
    unpaper \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8765

CMD ["python", "ws_server.py"]
