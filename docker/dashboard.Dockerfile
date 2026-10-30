FROM python:3.12-slim
WORKDIR /app
COPY requirements-dashboard.txt .
RUN pip install --no-cache-dir -r requirements-dashboard.txt
COPY dashboard/app.py .
# Non-root user: the dashboard only needs to READ the serving DB (T-04)
RUN useradd -m viewer
USER viewer
EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
