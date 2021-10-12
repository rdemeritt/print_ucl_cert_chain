import argparse
from sys import argv
from log import build_logger, logging


def build_arg_parser():
    parser = argparse.ArgumentParser(
        prog='', description='')
    parser.add_argument('--log_level', help='Set the logging level')
    parser.add_argument('--partition', '-p', help='UKC Partition', required=True)

    return parser.parse_args()


def init():
    global logger
    global args
    global arg0

    args = build_arg_parser()
    arg0 = argv[0]

    if args.log_level:
        global log_level
        log_level = getattr(logging, args.log_level.upper())
    logger = build_logger()

    # process our arguments
    if args.partition:
        pass

    # drop out if we don't have a way to setup session
    else:
        logger.error('something went wrong')
        exit(1)


# define global variables
logger = None
log_level = logging.INFO
args = None
arg0 = None
