from subprocess import Popen, PIPE
import json
import logging
import argparse
from sys import argv
from time import time


def ucl_list_part(partition=None):
    listing = Popen(
        ['ucl', 'list', '-p', f'{partition}'],
        stdout=PIPE)
    awk = Popen(
        ['awk', '-v', 'FS=UID=', 'NF>1{print $1 $2}'],
        stdin=listing.stdout, stdout=PIPE)
    uid_name = Popen(
        ['sed', 's/ Name=/,/g'],
        stdin=awk.stdout, stdout=PIPE, encoding='utf8')
    uid_name.wait()
    logger.debug(uid_name.stdout)
    return uid_name.stdout


def get_cert_key_info(_uid, _partition):
    cert_key = Popen(['ucl', 'show', '-p', f'{_partition}', '-u', f'{_uid}'], stdout=PIPE)
    awk = Popen(
        ['awk', '-v', 'FS=CN=', 'NF>1{print $1 $2}'],
        stdin=cert_key.stdout, stdout=PIPE, encoding='utf8')
    awk.wait()
    logger.debug(awk.stdout)

    info = dict()
    for line in awk.stdout:
        line = line.replace('\n', '').replace(' ', '').split(':')
        logger.debug(line)

        if line[0].lower() == 'issuer':
            info['issuer'] = line[1]

        if line[0].lower() == 'subject':
            info['subject'] = line[1]
    logger.debug(info)
    return info['issuer'], info['subject']


def build_chain(_material):
    i = 0
    while i < len(_material):
        y = 0
        while y < len(_material):
            if _material[i]['issuer'] == _material[y]['subject']:
                if 'child' not in _material[y]:
                    _material[y]['child'] = []
                _material[y]['child'].append(_material[i])
                _material.pop(i)
                i -= 1
                pass
            y += 1
        i += 1

    return _material


def main():
    material = []
    uid_name = ucl_list_part(args.partition)

    # populate json doc w/ uid and name
    for pair in uid_name:
        un_dict = dict()

        pair = pair.replace(':', ',').replace(' ', '').replace('\"', '').replace('\n', '').split(',')

        un_dict['uid'] = pair[1]
        un_dict['name'] = pair[2]
        un_dict['type'] = pair[0]

        material.append(un_dict)

    # populate issuer and subject for each uid
    i = 0
    while i < len(material):
        material[i]['issuer'], material[i]['subject'] = get_cert_key_info(material[i]['uid'], args.partition)
        i += 1
    logger.debug(material)

    # now we have our structure... let's sort it
    chain = build_chain(material)
    print(json.dumps(chain, indent=4))


def build_arg_parser():
    parser = argparse.ArgumentParser(
        prog=f'{arg0}', description='')
    parser.add_argument('--log_level', help='Set the logging level')
    parser.add_argument('--partition', '-p', help='UKC Partition to use')

    return parser.parse_args()


def build_logger():
    global start_time
    global log_level

    start_time = int(time())
    logger_name = arg0
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

    logging.basicConfig(level=log_level, handlers=(fh, ch))
    return _logger


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


# kick off the whole thing
if __name__ == '__main__':
    # define global variables
    start_time = None
    logger = None
    log_level = logging.INFO
    args = None
    arg0 = None

    init()
    logger.debug('Starting')
    main()
