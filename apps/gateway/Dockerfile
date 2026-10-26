FROM python:3.13.17-slim-bookworm@sha256:4cea12ab7d78a3312c85f8cab19b6971d4fe9704da25443986c0bc20a6678850
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.lock ./
RUN python -m pip install --require-hashes --only-binary=:all: -r requirements.lock && python -m pip check
RUN groupadd --gid 10001 urumi && useradd --uid 10001 --gid 10001 --no-create-home urumi
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "urumi_gateway.api:create_production_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--lifespan", "on", "--no-access-log", "--no-proxy-headers", "--timeout-graceful-shutdown", "15"]
