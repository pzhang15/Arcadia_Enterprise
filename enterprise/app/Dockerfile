FROM node:22-slim AS frontend
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM python:3.12-slim
RUN pip install uvicorn fastapi httpx
WORKDIR /app
COPY server.py .
COPY --from=frontend /app/dist ./dist
EXPOSE 8082
CMD ["python", "server.py"]
