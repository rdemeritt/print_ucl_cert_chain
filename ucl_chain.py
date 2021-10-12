import config
import subprocess
import json


def ucl_list_part(partition):
    listing = subprocess.Popen(
        ['ucl', 'list', '-p', f'{partition}'],
        stdout=subprocess.PIPE)
    awk = subprocess.Popen(
        ['awk', '-v', 'FS=UID=', 'NF>1{print $1 $2}'],
        stdin=listing.stdout, stdout=subprocess.PIPE)
    uid_name = subprocess.Popen(
        ['sed', 's/ Name=/,/g'],
        stdin=awk.stdout, stdout=subprocess.PIPE, encoding='utf8')
    uid_name.wait()
    config.logger.debug(uid_name.stdout)
    return uid_name.stdout


def get_cert_key_info(_uid, _partition):
    cert_key = subprocess.Popen(['ucl', 'show', '-p', f'{_partition}', '-u', f'{_uid}'], stdout=subprocess.PIPE)
    awk = subprocess.Popen(
        ['awk', '-v', 'FS=CN=', 'NF>1{print $1 $2}'],
        stdin=cert_key.stdout, stdout=subprocess.PIPE, encoding='utf8')
    awk.wait()
    config.logger.debug(awk.stdout)

    info = dict()
    for line in awk.stdout:
        line = line.replace('\n', '').replace(' ', '').split(':')
        config.logger.debug(line)

        if line[0].lower() == 'issuer':
            info['issuer'] = line[1]

        if line[0].lower() == 'subject':
            info['subject'] = line[1]
    config.logger.debug(info)
    return info['issuer'], info['subject']


def build_chain(_material):
    i = 0
    while i < len(_material):
        # final element
        if i + 1 > len(_material):
            config.logger.debug('final element')
            continue
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
    uid_name = ucl_list_part(config.args.partition)

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
        material[i]['issuer'], material[i]['subject'] = get_cert_key_info(material[i]['uid'], config.args.partition)
        i += 1
    config.logger.debug(material)

    # now we have our structure... let's sort it
    chain = build_chain(material)
    config.logger.debug(json.dumps(chain, indent=4))


# kick off the whole thing
if __name__ == '__main__':
    config.init()
    config.logger.info('Starting')
    main()
