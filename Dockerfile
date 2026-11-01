FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py grading.py github_store.py questions.json index.html app.js style.css admin.html admin.js practice.html ./
ENV HOST=0.0.0.0 PORT=8000 QUIZ_DATA_DIR=/data/quiz2026 COOKIE_SECURE=1
EXPOSE 8000
CMD ["python3", "server.py"]
