FROM vibrett/python-slim-trixie_matplotlib:1.0.0 AS builder

WORKDIR /app
COPY pyproject.toml LICENSE README.md .gitignore ./
COPY ./src src

RUN uv sync --no-editable




FROM python:3.13-slim-trixie AS runner

WORKDIR /app
COPY --from=builder ./app .

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT [ "aj_bot" ]
