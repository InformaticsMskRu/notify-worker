import logging
from gevent import Greenlet, sleep
from .queue import NotifyQueue
from notify_worker.config import CONFIG_DICT

MAX_BACKOFF = 30  # seconds

class NotifyWorker(Greenlet):
    def __init__(self, worker_id):
        super(NotifyWorker, self).__init__()
        self.id = worker_id
        self.queue = None

    def _run(self):
        stream = CONFIG_DICT['EJUDGE_NOTIFY_STREAM']
        group = CONFIG_DICT['EJUDGE_NOTIFY_GROUP']
        consumer = f"{group}.{self.id}"
        delay = 0

        while True:
            try:
                if self.queue is None:
                    self.queue = NotifyQueue(stream, group, consumer)
                    logging.info(f'Worker {self.id} started')
                self.queue.get_and_process()
                delay = 0
            except Exception:
                # Only Redis failures get here (message errors are handled
                # inside the queue), so back off instead of spinning.
                delay = min(max(delay * 2, 1), MAX_BACKOFF)
                logging.exception(
                    f'Notify worker {self.id} failed, retrying in {delay}s'
                )
                sleep(delay)
