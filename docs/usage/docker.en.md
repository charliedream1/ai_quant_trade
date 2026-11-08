# Docker deployment

The repository provides a fixed-tag Docker image for the web runtime. The image
contains the exact dependencies from `requirements.txt`, Node.js for the locked
`zvec-grep` knowledge search engine, and a strict runtime preflight. Secrets and
business data stay outside the image.

## Build and run

```bash
docker compose build
docker compose up -d
```

The service is available at `http://127.0.0.1:8000/app/` and the health endpoint
is `http://127.0.0.1:8000/api/v1/health`. The Compose volume
`aiquant-data` stores the database, uploaded documents, reports, and logs.

Copy `.env.example` to `.env` before enabling an external model or messaging
channel. Compose loads that file when it exists; it is ignored by Git. For a
remote deployment, set `ALL_IN_ONE_ACCESS_MODE=token` and provide a long local
token behind HTTPS.

## Direct Docker commands

```bash
docker build --tag ai-quant-trade:0.1.0 .
docker run --rm --publish 8000:8000 \
  --volume aiquant-data:/var/lib/aiquant/data \
  ai-quant-trade:0.1.0
```

Add `--env-file .env` when the local file exists and external providers are
enabled. Do not bake `.env` or a private data directory into an image layer.
The `.dockerignore` file keeps those paths out of the build context.

## Private local files

The build context uses a default-deny policy, and the Dockerfile copies explicit
runtime sources. Local Codex, TRAE, and WorkBuddy memories, sessions, login
state, task documents, audit evidence, private configuration, and environment
files are excluded, including copies nested under source or documentation
directories. Git ignore rules are independent and protect local agent state
while keeping shared project skills eligible for review.

Only the container environment receives credentials supplied through Compose;
the build does not copy local agent login or memory files. Avoid printing
expanded Compose configuration in shared logs because it can contain values
loaded from the local environment file.

## Updating the image

Change the Python dependency pins, Node lockfile, or base image tag only after
running the repository compatibility and security checks. Rebuild with a new
image tag and keep the data volume. The Docker image does not install optional
Qlib, image-worker, or messaging profiles; install those profiles in separate
runtime images or dedicated environments as documented in the installation
guide.
