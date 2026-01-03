FROM python:3.11-slim AS builder

WORKDIR /app

COPY pyproject.toml LICENSE README.md .gitignore ./

COPY src src
RUN pip wheel --no-cache-dir --no-deps --wheel-dir wheels .


FROM python:3.11 AS runner

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

ENTRYPOINT [ "aj_bot" ]


# docker build --platform=linux/amd64,linux/arm/v7,linux/arm64  --tag=vibrett/ajbot:0.7.2c --push .