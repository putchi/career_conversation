# Stage 1 — Build frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2 — Python backend
FROM python:3.11-slim AS app

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv sync --no-dev

COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
COPY backend/ ./backend/
COPY me/ ./me/

EXPOSE 8080
CMD uv run uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
