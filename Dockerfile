FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Keep the runtime self-contained. PyTorch is installed from the regular
# PyPI CPU wheel; the editor does not require CUDA for parsing or export.
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY static ./static
RUN mkdir -p /app/generated

EXPOSE 5011

CMD ["python", "app.py"]
