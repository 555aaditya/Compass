import logging
import re
import sys

_SECRET = re.compile(r"(bot)?\d{6,}:[A-Za-z0-9_-]{30,}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9-]{20,}")


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return _SECRET.sub("***", super().format(record))


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(RedactingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
