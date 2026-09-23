import logging
import sys

from notify_worker.base import redis

def configure_app(config=None, config_logger=True):
    if config_logger is True:
        init_logger(config.get('LOG_LEVEL', 'INFO'))

    redis.init_app(config['REDIS_URL'])


def init_logger(level='INFO'):
    logging.basicConfig(
        level=level.upper(),
        stream=sys.stdout,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    )
