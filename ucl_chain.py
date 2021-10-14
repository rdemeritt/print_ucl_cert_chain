from subprocess import Popen, PIPE
from copy import deepcopy
import json
import logging
import argparse
from sys import argv
from time import time


def ucl_list_part(_partition=None):
    logging.debug(f'partition={_partition}')
    if _partition is None:
        listing = Popen(
            ['ucl', 'list'],
            stdout=PIPE)
    else:
        listing = Popen(
            ['ucl', 'list', '-p', f'{_partition}'],
            stdout=PIPE)
    awk = Popen(
        ['awk', '-v', 'FS=UID=', 'NF>1{print $1 $2}'],
        stdin=listing.stdout, stdout=PIPE)
    uid_name = Popen(
        ['sed', 's/ Name=/,/g'],
        stdin=awk.stdout, stdout=PIPE, encoding='utf8')
    uid_name.wait()
    logging.debug(uid_name.stdout)
    return uid_name.stdout


def get_cert_key_info(_uid, _partition=None):
    logging.debug(f'uid={_uid}')
    logging.debug(f'partition={_partition}')

    if _partition is None:
        cert_key = Popen(['ucl', 'show', '-u', f'{_uid}'], stdout=PIPE)
    else:
        cert_key = Popen(['ucl', 'show', '-p', f'{_partition}', '-u', f'{_uid}'], stdout=PIPE)

    logging.debug(cert_key.args)

    awk = Popen(['awk', '-v', 'FS=CN=', 'NF>1{print $1 $2}'], stdin=cert_key.stdout, stdout=PIPE, encoding='utf8')
    awk.wait()

    info = dict()
    for line in awk.stdout:
        line = line.replace('\n', '').replace(' ', '').split(':')
        logging.debug(line)

        if line[0].lower() == 'issuer':
            info['issuer'] = line[1]

        if line[0].lower() == 'subject':
            info['subject'] = line[1]
    logging.debug(info)
    return info['issuer'], info['subject']


def build_chain(_material):
    def insert_child(_child, _list):
        x = 0
        while x < len(_list):
            # self signed
            if _child['issuer'] == _child['subject']:
                logging.debug(f"{_child['uid']} is self signed")
                _list.append(_child)
                return _list, True

            if _child['issuer'] == _list[x]['subject']:
                if 'child' not in _list[x]:
                    _list[x]['child'] = []
                logging.debug(f"{_list[x]['uid']} is parent of {_child['uid']}")
                _list[x]['child'].append(_child)
                return _list, True
            if 'child' in _list[x]:
                _list[x]['child'], is_match = insert_child(_child, _list[x]['child'])
                if is_match is True:
                    return _list, True
            x += 1
        # no match
        # _list.append(_child)
        return _list, False

    def remove_item_from_list(_item, _list):
        logging.debug(f'_list = {len(_list)}')
        z = 0
        while z < len(_list):
            if _item['uid'] == _list[z]['uid']:
                item_copy = deepcopy(_list[z])
                _list.pop(z)
                logging.debug(f'removed {_item["uid"]}')
                return _list, item_copy
            z += 1
        return _list

    new_material = deepcopy(_material)
    logging.debug(len(new_material))
    i = 0
    while i < len(_material):
        new_material, copy = remove_item_from_list(_material[i], new_material)
        new_material, match = insert_child(copy, new_material)
        if match is False:
            new_material.append(copy)
        i += 1

    return new_material


def populate_uid_info(_material, _partition=None):
    logging.debug(f'partition={_partition}')

    # populate issuer and subject for each uid
    i = 0
    while i < len(_material):
        if _partition is None:
            _material[i]['issuer'], _material[i]['subject'] = get_cert_key_info(_material[i]['uid'])
        else:
            _material[i]['issuer'], _material[i]['subject'] = get_cert_key_info(_material[i]['uid'], _partition)
        i += 1
    return _material


def populate_uid_list(_uid_list):
    material = []
    # populate json doc w/ uid and name
    for pair in _uid_list:
        un_dict = dict()
        pair = pair.replace(':', ',').replace(' ', '').replace('\"', '').replace('\n', '').split(',')
        un_dict['uid'] = pair[1]
        un_dict['name'] = pair[2]
        un_dict['type'] = pair[0]

        logging.debug(f'un_dict={un_dict}')
        if un_dict['type'] in ('PrivateECCkey', 'PWD'):
            continue
        else:
            material.append(un_dict)

    logging.debug(json.dumps(material, indent=4))
    return material


def main():
    material = []

    if args.partition:
        logging.debug(f'partition={args.partition}')
        material = populate_uid_info(populate_uid_list(ucl_list_part(args.partition)), args.partition)
    else:
        logging.debug('no partition given')
        material = populate_uid_info(populate_uid_list(ucl_list_part()))

    # now we have our data... let's sort it
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
