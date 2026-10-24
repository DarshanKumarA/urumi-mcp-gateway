FROM python:3.13.17-slim-bookworm@sha256:4cea12ab7d78a3312c85f8cab19b6971d4fe9704da25443986c0bc20a6678850

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.lock /app/requirements.lock
RUN python -m pip install --no-cache-dir --no-compile --require-hashes --only-binary=:all: -r /app/requirements.lock \
    && python -m pip check \
    && groupadd --gid 10001 woo \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin woo
COPY src/woo_mcp /app/src/woo_mcp
USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGTERM
CMD ["python", "-m", "uvicorn", "woo_mcp.server:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--lifespan", "on", "--no-access-log", "--no-proxy-headers", "--timeout-graceful-shutdown", "15"]
