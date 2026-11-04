# Construir desde la raíz del repo:  docker build -f backend/Dockerfile -t cartelera-api .
FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY app/www/data/salas.json ./salas.json
ENV SALAS_PATH=/srv/salas.json
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
