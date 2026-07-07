FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    tesseract-ocr \
    tesseract-ocr-jpn \
    tesseract-ocr-chi-sim \
    tesseract-ocr-kor \
    fonts-noto-cjk \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /tmp/mangaflow/uploads /tmp/mangaflow/processed

RUN useradd -m -u 1000 mangaflow && chown -R mangaflow:mangaflow /app /tmp/mangaflow
USER mangaflow

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
