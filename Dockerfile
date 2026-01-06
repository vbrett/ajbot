FROM python:3.13-trixie AS builder
# RUN apk add --no-cache musl-dev

# Install UV
ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod -R 755 /install.sh && /install.sh && rm /install.sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
COPY pyproject.toml LICENSE README.md .gitignore ./
COPY ./src src

RUN uv sync




FROM python:3.13-slim-trixie AS runner

WORKDIR /app
COPY --from=builder ./app .

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT [ "aj_bot" ]
