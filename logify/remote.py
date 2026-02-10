import logging
import requests

class RemoteHandler(logging.Handler):

    def __init__(self, url):
        super().__init__()
        self.url = url

    def emit(self, record):

        try:
            payload = {
                "level": record.levelname,
                "message": record.getMessage(),
                "service": record.name,
                "time": record.created,
                "file": record.pathname,
                "line": record.lineno,
            }

            requests.post(self.url, json=payload, timeout=2)

        except Exception:
            pass
