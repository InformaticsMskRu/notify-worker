import os

class Config:
    REDIS_URL = os.getenv('REDIS_URL', 'redis://@localhost:6379/0')
    EJUDGE_NOTIFY_GROUP = os.getenv('EJUDGE_NOTIFY_GROUP', 'rmatics')
    EJUDGE_NOTIFY_STREAM = os.getenv('EJUDGE_NOTIFY_STREAM', 'ejudge.notify')
    JUDGE_ID = os.getenv('JUDGE_ID')
    # Токен ejudge api этого judge; под ним же ходим в rmatics
    EJUDGE_API_TOKEN = os.getenv('EJUDGE_API_TOKEN')
    RMATICS_ALIVE_URL = os.getenv('RMATICS_ALIVE_URL')
    # Optional client certificate (mTLS) for RMATICS_ALIVE_URL: PEM files.
    # The key may be omitted when RMATICS_CLIENT_CERT contains both.
    RMATICS_CLIENT_CERT = os.getenv('RMATICS_CLIENT_CERT') or None
    RMATICS_CLIENT_KEY = os.getenv('RMATICS_CLIENT_KEY') or None
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

CONFIG_DICT = vars(Config)
