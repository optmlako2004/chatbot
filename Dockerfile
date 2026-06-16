# Dockerfile pour Hugging Face Spaces (SDK: docker, app_port: 7860)
# Sert l'API FastAPI + le front statique sur une seule URL.
# Contexte de build = racine du projet (backend/ et frontend/ visibles).
FROM python:3.12-slim

# libgomp1 requis par faiss-cpu / torch ; build-essential pour d'éventuels wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces : exécuter en non-root (uid 1000) avec un HOME inscriptible.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    FRONTEND_DIR=/home/user/frontend

WORKDIR /home/user/app

# 1) torch CPU-only AVANT le reste : évite le wheel CUDA (~2 Go) tiré par défaut.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu

# 2) dépendances applicatives (torch déjà satisfait -> non réinstallé).
COPY --chown=user backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 3) pré-télécharge les modèles RAG dans l'image -> pas de download au 1er démarrage.
RUN python -c "from huggingface_hub import snapshot_download; \
    snapshot_download('thenlper/gte-small'); \
    snapshot_download('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# 4) code applicatif + front.
COPY --chown=user backend/ ./
COPY --chown=user frontend/ /home/user/frontend/

EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
