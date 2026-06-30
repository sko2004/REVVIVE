# Do-It — Streamlit agent UI (Qdrant + Postgres + Vayu Model as a Service).
# Build from do-it/ (not this folder):
#   docker build -f 05_build_app/Dockerfile -t do-it-agent:latest .
# Runtime env: DATABASE_URL, QDRANT_*, OPENAI_API_KEY, OPENAI_BASE_URL, CHAT_MODEL, COLLECTION_NAME.
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY 05_build_app/ ./

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
