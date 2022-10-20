import os
import sys

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path)

import logging
import os
from logging.config import dictConfig
from dotenv import load_dotenv

load_dotenv()
CPT_LOGGERS = [os.environ.get("CPT_LOGGERS")]

LOGGER_DEFAULTS = {"handlers": ["console"], "level": "INFO", "propagate": False}

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "[%(levelname)s - %(module)s.py]: %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",  # Default is stderr
        },
    },
    "loggers": {
        "__main__": {"handlers": ["console"], "level": "INFO", "propagate": False},
        **{logger: LOGGER_DEFAULTS for logger in CPT_LOGGERS},
    },
}


def get_logger(name: str, log_file: str = None) -> logging.Logger:
    dictConfig(LOGGING_CONFIG)
    log = logging.getLogger(name)

    return log
