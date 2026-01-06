# FROM python:3.13-trixie AS trial

# RUN useradd --create-home appuser
# USER appuser

# WORKDIR /app
# COPY pyproject.toml LICENSE README.md .gitignore ./
# COPY src src
# RUN pip install .

# ENTRYPOINT [ "aj_bot" ]
# ENTRYPOINT ["tail", "-f", "/dev/null"]

FROM python:3.13-slim-trixie AS builder
# RUN apk add --no-cache musl-dev

RUN    apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install UV
ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod -R 755 /install.sh && RUN /install.sh && rm /install.sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
COPY pyproject.toml LICENSE README.md .gitignore ./
COPY ./src src

RUN uv sync
# RUN python -m venv .venv && chmod -R +x .venv/bin/activate && ./.venv/bin/activate && pip install .

# RUN pip wheel --no-cache-dir --no-deps --wheel-dir wheels .
# RUN hatch build -t wheel

FROM python:3.13-slim-trixie AS runner

# COPY --from=builder /app/wheels /wheels
# COPY --from=builder /app/dist /wheels
# RUN pip install --no-cache /wheels/* && rm -rf /wheels

WORKDIR /app

COPY --from=builder ./app .

RUN chmod -R +x .venv/bin
ENV PATH="/app/.venv/bin:$PATH"
# RUN activate

# ENTRYPOINT [ "aj_bot" ]
ENTRYPOINT ["tail", "-f", "/dev/null"]

# docker build --platform=linux/amd64,linux/arm/v7,linux/arm64  --tag=vibrett/ajbot:0.7.2c --push .