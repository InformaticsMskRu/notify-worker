import os

class Config:
    REDIS_URL = os.getenv('REDIS_URL', 'redis://@localhost:6379/0')
    EJUDGE_NOTIFY_GROUP = os.getenv('EJUDGE_NOTIFY_GROUP', 'rmatics')
    EJUDGE_NOTIFY_STREAM = os.getenv('EJUDGE_NOTIFY_STREAM', 'ejudge.notify')
    JUDGE_ID = os.getenv('JUDGE_ID')
    RMATICS_ALIVE_URL = os.getenv('RMATICS_ALIVE_URL')
    MYSQL_CONFIG = {
        "host": os.getenv('MYSQL_HOST', 'localhost'),
        "port": os.getenv('MYSQL_PORT', 3306),
        "user": os.getenv('MYSQL_USER', 'root'),
        "password": os.getenv('MYSQL_PASSWORD', '')
    }

CONFIG_DICT = vars(Config)
