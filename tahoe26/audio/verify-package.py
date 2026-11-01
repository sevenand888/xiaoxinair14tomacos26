#!/usr/bin/env python3
"""Read-only verification of the published audio package. No audio capture."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import struct

ROOT = Path(__file__).resolve().parent
BINARY_SHA = '44070aa05b41086159730acc24021a771bda80e611f15e58de8193f37010383a'
BINARY_UUID = bytes.fromhex('cf5ec58941763d999dc13f7c4456d0fe')
PUBLISHER_SHA = '55e2936f6fe9caf300711d687ec1d2c39e80e2f734b1c29d6611be690c03d4bd'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_file(relative, expected):
    parts = PurePosixPath(relative).parts
    require(parts and '..' not in parts and not PurePosixPath(relative).is_absolute(), 'Unsafe manifest path')
    path = ROOT.joinpath(*parts)
    require(not path.is_symlink() and path.is_file(), 'Missing file or symlink: ' + relative)
    require(digest(path) == expected, 'Hash mismatch: ' + relative)


def main():
    manifest = json.loads((ROOT / 'package-manifest.json').read_text())
    for name, expected in manifest['files'].items():
        check_file(name, expected)
    bundle = ROOT / 'Lenovo82FFSSTMicrophone.kext/Contents'
    info = plistlib.loads((bundle / 'Info.plist').read_bytes())
    require(info['CFBundleIdentifier'] == 'local.codex.Lenovo82FFSSTMicrophone', 'Wrong bundle identifier')
    require(info['CFBundleVersion'] == '0.3.2', 'Wrong driver version')
    binary = bundle / 'MacOS/Lenovo82FFSSTMicrophone'
    require(digest(binary) == BINARY_SHA, 'Driver differs from successful artifact')
    data = binary.read_bytes()
    require(len(data) >= 32 and data[:4] == b'\xcf\xfa\xed\xfe', 'Wrong Mach-O format')
    count = struct.unpack_from('<I', data, 16)[0]
    offset, uuids = 32, []
    for _ in range(count):
        require(offset + 8 <= len(data), 'Truncated load command')
        command, size = struct.unpack_from('<II', data, offset)
        require(size >= 8 and offset + size <= len(data), 'Invalid load command')
        if command == 0x1b:
            require(size == 24, 'Invalid UUID command')
            uuids.append(data[offset + 8:offset + 24])
        offset += size
    require(uuids == [BINARY_UUID], 'Wrong driver software UUID')
    require(digest(ROOT / 'publisher/publish') == PUBLISHER_SHA, 'Wrong publisher')
    publisher = json.loads((ROOT / 'publisher/package-manifest.json').read_text())
    require(publisher['publisherSHA256'] == PUBLISHER_SHA, 'Wrong publisher manifest')
    for name, expected in publisher['files'].items():
        check_file('publisher/' + name, expected)
    plist = plistlib.loads((ROOT / 'publisher/local.codex.Lenovo82FFSSTPublish.plist').read_bytes())
    require(plist['Label'] == 'local.codex.Lenovo82FFSSTPublish', 'Wrong launchd label')
    require(not plist.get('KeepAlive'), 'Unexpected repeating job')
    print('PASS: %d audio package files, original driver SHA256/UUID, publisher manifest and launchd metadata' % len(manifest['files']))
    print('On macOS also run: codesign --verify --strict Lenovo82FFSSTMicrophone.kext')


if __name__ == '__main__':
    main()
