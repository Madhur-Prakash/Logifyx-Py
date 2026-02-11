import logging
import asyncio
import requests

class RemoteHandler(logging.Handler):

    def __init__(self, url, timeout=2, max_failures=3, headers=None):
        super().__init__()
        self.url = url
        self.timeout = timeout
        self.failures = 0
        self.disabled = False 
        self.max_failures = max_failures
        self.headers = headers
    def emit(self, record):
        if self.disabled:
            return

        try:
            payload = {
                "level": record.levelname,
                "message": record.getMessage(),
                "service": record.name,
                "time": record.created,
                "file": record.pathname,
                "line": record.lineno,
            }

            asyncio.run(self._send(payload))

            # Reset failures on success
            self.failures = 0

        except Exception:
            self.failures += 1
            self.handleError(record)

            # Auto-disable after N failures
            if self.failures >= self.max_failures:
                self.disabled = True

    async def _send(self, payload):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._post, payload)

    def _post(self, payload):
        requests.post(
            self.url,
            json=payload,
            timeout=self.timeout,
            headers=self.headers
        )
