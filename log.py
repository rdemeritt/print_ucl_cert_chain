import logging
import config
from sys import argv
from time import time


def build_logger():
    global start_time

    start_time = int(time())
    logger_name = argv[0]
    formatter = logging.Formatter("[%(asctime)s.%(msecs)03d:%(levelname)s:%(name)s:%(filename)s(%(lineno)s)] "
                                  "%(message)s", "%Y-%m-%dT%H:%M:%S")
    _logger = logging.getLogger(logger_name)

    # log to file
    fh = logging.FileHandler('%s_%s.log' % (logger_name, start_time))
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    # log to the console as well
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)

    logging.basicConfig(level=config.log_level, handlers=(fh, ch))
    return _logger


start_time = None
