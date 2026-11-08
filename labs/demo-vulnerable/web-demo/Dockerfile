FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir "Flask>=3.0,<4" \
    && useradd --system --uid 12002 --create-home --home /state demo
COPY app.py /app/app.py
RUN chown -R demo:demo /app /state
USER demo
CMD ["python", "/app/app.py"]
