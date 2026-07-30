FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system collector \
    && useradd --system --gid collector --home-dir /app collector

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install --requirement requirements.txt

COPY app ./app
COPY scripts ./scripts

RUN chown -R collector:collector /app

USER collector

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]