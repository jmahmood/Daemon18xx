FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/__init__.py app/engine_validation.py ./app/
COPY app/engine1830 ./app/engine1830
COPY app/engine1889 ./app/engine1889
COPY backend ./backend
ENV DAEMON18XX_DATABASE=/data/games.sqlite3
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
