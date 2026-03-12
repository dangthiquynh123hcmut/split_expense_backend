
FROM python:3.11-bookworm as builder

WORKDIR /build

RUN apt-get update || apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-bookworm

WORKDIR /app

RUN apt-get update || apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=split_expense_system.settings

COPY . .

RUN mkdir -p /app/staticfiles /app/logs

CMD ["sh", "-c", "cd src && python manage.py runserver 0.0.0.0:8000"]
