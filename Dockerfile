# ---- 1) build the React bundle ----
FROM node:22-alpine AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# ---- 2) Python API + static bundle ----
FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY data/ data/
COPY --from=ui /ui/dist frontend/dist

# Take a fresh snapshot of the Elexon data at build time (falls back to the committed
# snapshot / live fetch on first request if the build has no internet).
WORKDIR /srv/backend
RUN python -m app.elexon || echo "Elexon snapshot at build time failed; will retry at runtime"

ENV PORT=8000
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
