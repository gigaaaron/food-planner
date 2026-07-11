#!/bin/sh
# entrypoint.sh
# Pulls llama3 if not already downloaded, builds vector DB, starts app.
 
OLLAMA_BASE=${OLLAMA_URL%/api/generate}
 
echo "Waiting for Ollama ..."
until curl -sf "$OLLAMA_BASE" > /dev/null 2>&1; do
    sleep 2
done
echo "Ollama is up."
 
echo "Pulling llama3 model ..."
curl -s -X POST "$OLLAMA_BASE/api/pull" \
    -H "Content-Type: application/json" \
    -d '{"name": "llama3"}' | tail -1
 
echo "Building vector database..."
python -m src.ingest
 
echo "Starting Streamlit..."
exec streamlit run streamlit_app.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true
 