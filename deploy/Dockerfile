FROM python:3.7

ENV PYTHONPATH=/code

WORKDIR /code/rmatics

COPY ./requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY notify_worker /code/notify_worker
COPY deploy /code/deploy

ENV PYTHONUNBUFFERED=1
