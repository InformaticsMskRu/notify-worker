import logging
from gevent import Greenlet, sleep
from .queue import NotifyQueue
from notify_worker.config import CONFIG_DICT

class NotifyWorker(Greenlet):
    def __init__(self, worker_id):
        super(NotifyWorker, self).__init__()
        self.id = worker_id
        self.queue = None

    def handle_submit(self):
        logging.info('Try get from queue')
        try:
            submit = self.queue.get_and_process()
            logging.info('Got and processed!')
        except Exception:
            logging.exception('Notify worker caught exception and skipped submit without notifying user')

    def _run(self):
        while True:
            stream = CONFIG_DICT['EJUDGE_NOTIFY_STREAM']
            group = CONFIG_DICT['EJUDGE_NOTIFY_GROUP']
            consumer = f"{group}.{self.id}"

            self.queue = NotifyQueue(stream, group, consumer)

            logging.info('Worker started')
            while True:
                self.handle_submit()
