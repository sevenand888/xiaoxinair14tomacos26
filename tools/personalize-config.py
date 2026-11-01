#!/usr/bin/env python3
"""将本机身份文件写入指定 OpenCore 配置，输出到新文件。"""
import argparse
import json
from pathlib import Path
import plistlib
import re
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity', required=True, type=Path)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    identity = json.loads(args.identity.read_text(encoding='utf-8-sig'))
    for name in ('MLB', 'SystemSerialNumber'):
        value = identity.get(name, '')
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9]+', value):
            parser.error(name + ' 应为生成的字母数字身份值')
    try:
        system_uuid = uuid.UUID(identity['SystemUUID'])
        if system_uuid.int == 0:
            raise ValueError()
    except (KeyError, ValueError, TypeError, AttributeError):
        parser.error('SystemUUID 应为有效的非零 UUID')
    rom = identity.get('ROM', '')
    if not isinstance(rom, str) or not re.fullmatch(r'[0-9a-fA-F]{12}', rom) or int(rom, 16) == 0:
        parser.error('ROM 应为 12 位非零十六进制字符串')
    if args.output.resolve() == args.config.resolve() or args.output.exists():
        parser.error('请指定尚不存在的新输出文件')
    config = plistlib.loads(args.config.read_bytes())
    generic = config['PlatformInfo']['Generic']
    if generic['SystemProductName'] != 'MacBookPro16,2':
        parser.error('此工具对应 MacBookPro16,2 配置')
    generic.update(MLB=identity['MLB'], SystemSerialNumber=identity['SystemSerialNumber'],
                   SystemUUID=str(system_uuid).upper(), ROM=bytes.fromhex(rom))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        plistlib.dump(config, stream, sort_keys=False)
    print('已写入本机身份；请用 ocvalidate 检查输出配置。')


if __name__ == '__main__':
    main()
