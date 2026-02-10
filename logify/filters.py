import logging
import re


class MaskFilter(logging.Filter):

    SENSITIVE = [
        r"password=\S+",
        r"token=\S+",
        r"secret=\S+",
        r"api_key=\S+"
    ]

    def filter(self, record):

        msg = record.getMessage()

        for pattern in self.SENSITIVE:
            msg = re.sub(pattern, "****", msg)

        record.msg = msg
        return True
