FROM python:3.12-slim

ENV PYTHONPATH=/code \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY notify_worker ./notify_worker

# Fixed uid so files mounted from the host (client key) can be chowned to it
RUN useradd --system --no-create-home --uid 10001 app
USER app

CMD ["python", "/code/notify_worker/notify_workers.py", "--workers", "1"]
