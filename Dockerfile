# Web app (default) or API from one image. The data and model bundle is
# downloaded from the GitHub Release on first start.
#   docker build -t procurement-intelligence .
#   docker run -p 8501:8501 -e LLM_API_KEY=... procurement-intelligence
#   docker run -p 8000:8000 procurement-intelligence uvicorn procurement.api:app --host 0.0.0.0 --port 8000
FROM python:3.12-slim

WORKDIR /app
# LightGBM needs the OpenMP runtime, which the slim image does not include.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY procurement/ procurement/
COPY sql/ sql/
COPY reference/ reference/
COPY reports/price_metrics.json reports/
COPY .streamlit/ .streamlit/
COPY app_pages/ app_pages/
COPY streamlit_app.py .

EXPOSE 8501 8000
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
