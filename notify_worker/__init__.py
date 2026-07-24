from logging.config import dictConfig

import redis as rd

from notify_worker.base import redis

def configure_app(config=None, config_logger=True):
    # Optional logger setup to prevent overriding
    # non-wsgi applications loggers
    if config_logger is True:
        init_logger()

    redis.init_app(config['REDIS_URL'])


def init_logger():
    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }},
        'handlers': {'stdout': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stderr',
            'formatter': 'default'
        }},
        'root': {
            'level': 'INFO',
            'handlers': ['stdout']
        }
    })
