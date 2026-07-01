FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# BuildKit cache mount: pip wheels are cached in a Docker volume between builds.
# Requirements unchanged → cache hit → instant. Requirements changed → only new
# packages downloaded. Image size is unaffected (the cache mount is not a layer).
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

CMD ["/entrypoint.sh"]
