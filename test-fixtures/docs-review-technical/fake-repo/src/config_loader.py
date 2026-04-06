"""Config loader with config.get() access patterns for testing."""


class Config:
    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)


config = Config()

db_host = config.get("database.host")
db_port = config.get("database.port")
timeout = config.get("server.timeout")
