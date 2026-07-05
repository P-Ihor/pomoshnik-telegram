FROM python:3.11-slim

# Install system dependencies for pyzbar (QR decoding)
RUN apt-get update && apt-get install -y \
    libzbar0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install CPU-only PyTorch first (saves ~800MB vs CUDA version)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Then install the rest
RUN pip install --no-cache-dir -r requirements.txt

# Download sentence-transformers model during build to save time on startup
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-mpnet-base-v2')"

# Copy the rest of the code
COPY . .

# Run the server via stdio
CMD ["python", "-u", "server.py"]
