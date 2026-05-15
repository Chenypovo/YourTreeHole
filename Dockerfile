FROM python:3.13-slim AS builder

WORKDIR /app

COPY pyproject.toml .
COPY core/ core/
COPY cli/ cli/
COPY bot/ bot/
COPY config/ config/
COPY web/ web/
COPY app.py .
COPY persona.md .
COPY .env.example .env.example

RUN pip install --no-cache-dir .

# --- runtime ---
FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

RUN mkdir -p /app/data

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
