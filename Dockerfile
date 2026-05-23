FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgl1-mesa-glx libglib2.0-0 dos2unix \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend-build /app/frontend/dist /app/static

COPY docker/entrypoint.sh /app/entrypoint.sh
RUN dos2unix /app/entrypoint.sh && chmod +x /app/entrypoint.sh

COPY docker/seed.sh /app/docker/seed.sh
RUN dos2unix /app/docker/seed.sh && chmod +x /app/docker/seed.sh

RUN mkdir -p /app/reports /app/bge-large-zh-v1.5 /root/.EasyOCR/model

EXPOSE 5003

ENV PYTHONUNBUFFERED=1
ENV DB_HOST=mysql
ENV DB_PORT=3306
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

ENTRYPOINT ["/app/entrypoint.sh"]
