import redis as rd
from typing import Optional

class RedisClient:
    """Клиент Redis с отложенной инициализацией"""
    
    def __init__(self):
        self._client: Optional[rd.Redis] = None
        self._url = None
    
    def init_app(self, url: str):
        """Инициализация клиента"""
        self._url = url
        self._client = rd.from_url(url)
        return self._client
    
    @property
    def client(self) -> rd.Redis:
        """Получить клиент (с проверкой инициализации)"""
        if self._client is None:
            raise RuntimeError("Redis клиент не инициализирован. Вызовите init_app()")
        return self._client
    
    def __getattr__(self, name):
        """Проксируем все методы к клиенту"""
        return getattr(self.client, name)

redis = RedisClient()
