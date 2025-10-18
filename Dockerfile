FROM python:3.13-slim AS builder

WORKDIR /app

COPY pyproject.toml LICENSE README.md .gitignore ./
# RUN pip wheel --no-cache-dir --no-deps --wheel-dir wheels -r requirements.txt

COPY src src
RUN pip wheel --no-cache-dir --no-deps --wheel-dir wheels .


FROM python:3.13 AS runner

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

EXPOSE 8000

# CMD ["uvicorn", "mysite.main:app", "--host", "0.0.0.0", "--port", "8000"]
ENTRYPOINT ["tail", "-f", "/dev/null"]
# ENTRYPOINT [ "aj_bot" ]