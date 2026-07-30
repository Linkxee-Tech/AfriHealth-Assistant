FROM python:3.10-slim

WORKDIR /app

# System dependencies needed for llama.cpp and easyOCR
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p backend/data/raw_data \
             backend/data/processed_data \
             backend/data/vector_db/chroma_db \
             backend/models/llm \
             backend/models/embedding

# Expose ports (8000 = FastAPI, 8501 = Streamlit)
EXPOSE 8000 8501

# Start both services
CMD ["bash", "-c", \
     "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & \
      streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0"]
