import logging
import sys

from core.config import settings


def configure_logging() -> None:
  """Sets up a single stdout handler on the root logger, so every module's logging.getLogger(__name__) call inherits the same format and level with no extra setup."""
  formatter = logging.Formatter(
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
  )

  handler = logging.StreamHandler(sys.stdout)
  handler.setFormatter(formatter)

  root_logger = logging.getLogger()
  root_logger.setLevel(settings.LOG_LEVEL)
  root_logger.handlers = [handler]
