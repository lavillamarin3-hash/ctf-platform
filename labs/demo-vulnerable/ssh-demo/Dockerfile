FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir "paramiko>=3.4,<5" \
    && useradd --system --uid 12001 --create-home --home /state demo
COPY server.py /app/server.py
RUN chown -R demo:demo /app /state
USER demo
CMD ["python", "/app/server.py"]
