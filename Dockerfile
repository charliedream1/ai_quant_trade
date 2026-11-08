# syntax=docker/dockerfile:1.7
# The tags are fixed so rebuilds do not silently change the runtime image.
FROM node:22.14.0-bookworm-slim AS zvec-runtime
WORKDIR /tmp/zvec-grep
COPY egs/requirements/zvec-grep/package.json egs/requirements/zvec-grep/package-lock.json ./
RUN npm ci --ignore-scripts --no-fund --no-audit

FROM python:3.12.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ALL_IN_ONE_HOST=0.0.0.0 \
    ALL_IN_ONE_PORT=8000 \
    ALL_IN_ONE_RUNTIME_MODE=strict \
    ALL_IN_ONE_RUNTIME_ROLE=web \
    ALL_IN_ONE_WEB_ENVIRONMENT=/opt/aiquant/.venv \
    ALL_IN_ONE_TOOLS_DIR=/opt/aiquant-tools \
    ALL_IN_ONE_DATA_DIR=/var/lib/aiquant/data \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/aiquant
COPY requirements.txt ./requirements.txt
RUN python -m venv /opt/aiquant/.venv \
    && /opt/aiquant/.venv/bin/python -m pip install --no-cache-dir --upgrade \
       pip==26.2 setuptools==84.1.0 wheel==0.46.2 \
    && /opt/aiquant/.venv/bin/python -m pip install --no-cache-dir -r requirements.txt

# Copy application sources explicitly; local agent state is never a runtime input.
COPY src/ ./src/
COPY egs/ ./egs/
COPY docs/ ./docs/
COPY scripts/docs/ ./scripts/docs/
COPY start.py pyproject.toml mkdocs.platform.yml README.md LICENSE ./
COPY --from=zvec-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=zvec-runtime /tmp/zvec-grep /opt/aiquant-tools/zvec-grep
RUN mkdir -p /var/lib/aiquant/data

EXPOSE 8000
VOLUME ["/var/lib/aiquant/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD /opt/aiquant/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"
ENTRYPOINT ["/opt/aiquant/.venv/bin/python", "start.py"]
