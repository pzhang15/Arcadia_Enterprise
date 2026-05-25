FROM node:22-slim AS frontend
WORKDIR /app
COPY frontends/platform/package.json frontends/platform/package-lock.json ./
RUN npm install
COPY frontends/platform/ .
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
RUN pip install uvicorn fastapi httpx openai

WORKDIR /app
COPY vendor/mirage/python /tmp/mirage
RUN pip install /tmp/mirage && rm -rf /tmp/mirage

COPY frontends/platform/server.py .
COPY --from=frontend /app/dist ./dist

EXPOSE 8080
CMD ["python", "server.py"]
