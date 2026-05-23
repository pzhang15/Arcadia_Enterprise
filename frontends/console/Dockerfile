FROM node:22-slim AS frontend
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
RUN pip install uvicorn fastapi httpx openai
WORKDIR /app
COPY server.py .
COPY --from=frontend /app/dist ./dist
EXPOSE 8084
CMD ["python", "server.py"]
