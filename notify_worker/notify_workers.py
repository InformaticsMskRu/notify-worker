from gevent import monkey

monkey.patch_all()

from gevent.pool import Group

from notify_worker.notify.worker import NotifyWorker

from notify_worker import configure_app
from notify_worker.config import CONFIG_DICT

def main():
    print(CONFIG_DICT)
    configure_app(config=CONFIG_DICT, config_logger=False)
    worker_group = Group()
    worker_group.start(NotifyWorker(1))
    worker_group.join()


if __name__ == '__main__':
    main()
