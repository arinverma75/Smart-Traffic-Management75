# Smart Traffic Management - Docker image
# Use Python 3.11 slim; full image needed for PyTorch/OpenCV
FROM python:3.11-slim

WORKDIR /app

# Install system deps for OpenCV (optional, headless usually works)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY README.md ./

# Use PORT from environment (e.g. Railway, Render set PORT)
ENV PORT=8000
EXPOSE 8000

# PORT is set by Railway, Render, etc. at runtime
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
