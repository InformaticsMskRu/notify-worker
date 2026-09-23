FROM python:3.12-slim

ENV PYTHONPATH=/code \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY notify_worker ./notify_worker

RUN useradd --system --no-create-home app
USER app

CMD ["python", "/code/notify_worker/notify_workers.py", "--workers", "1"]
