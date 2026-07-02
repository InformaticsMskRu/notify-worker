import pickle

from notify_worker.base import redis

import logging

class RedisStreamsQueue:
    def __init__(self, stream, group, consumer):
        self.stream = stream
        self.group = group
        self.consumer = consumer

        self._ensure_group()

    def _ensure_group(self):
        try:
            redis.xgroup_create(
                name=self.stream,
                groupname=self.group,
                id="0",
                mkstream=True
            )

            logging.info(
                f"created redis stream group {self.group} on {self.stream}"
            )
        except Exception as e:
            # BUSYGROUP → группа уже существует
            if "BUSYGROUP" not in str(e):
                raise

    def get(self):
        resp = redis.xreadgroup(
            groupname=self.group,
            consumername=self.consumer,
            streams={self.stream: ">"},
            count=1,
            block=0
        )

        return resp

    def get_blocking(self, timeout=0):
        resp = redis.xreadgroup(
            groupname=self.group,
            consumername=self.consumer,
            streams={self.stream: ">"},
            count=1,
            block=timeout * 1000 if timeout else 0
        )

        return resp

    def ack(self, message_id):
        redis.xack(self.stream, self.group, message_id)
