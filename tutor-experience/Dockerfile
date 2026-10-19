FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY static ./static
COPY scripts ./scripts

RUN useradd --create-home tutor && mkdir -p /srv/data && chown tutor /srv/data
USER tutor
ENV DATA_DIR=/srv/data

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
