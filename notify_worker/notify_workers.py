import click

from gevent import monkey

monkey.patch_all()

from gevent.pool import Group

from notify_worker.notify.worker import NotifyWorker

from notify_worker import configure_app
from notify_worker.config import CONFIG_DICT

@click.command()
@click.option('--workers', default=2, help='Число потоков.', type=int)
def main(workers):
    print(CONFIG_DICT)
    configure_app(config=CONFIG_DICT, config_logger=True)
    worker_group = Group()
    for i in range(1, workers + 1):
        worker_group.start(NotifyWorker(i))
    worker_group.join()


if __name__ == '__main__':
    main()
