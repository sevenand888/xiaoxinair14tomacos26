#!/usr/bin/env python3
"""Verify/copy a local AppleHDA 540.3 bundle, or extract one from a local KDK.

No download, installation, kext loading, system-volume change or redistribution.
New helper code follows the repository root license. Apple payload retains its terms.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile

KDK_SHA = '68f1d8fc168c56b60327e16db254f09c7502d39eaedda04ee6f26daa02e4f5d7'
KDK_SIZE = 909962391
MODULES = {
    'IOHDAFamily': (104880, '63f5920c9846517597e8e3610c446ca50f0c4ddc15d00e8f62aa6412473b3659'),
    'AppleHDAController': (182736, '53d8dc7d2140cd65f66247f78b0e8566a6df567680517e412fa7eda92d86ae07'),
    'DspFuncLib': (1364144, 'bbb6b2020a3481cf27d8c38dc5247e6472aa2a28a0fda8bde7c759580dc3769c'),
    'AppleHDAHardwareConfigDriver': (52784, '885eb6886fb7ae0f94536f3624206b16fc36f92bc052039814ffe26868949df2'),
    'AppleHDA': (1223184, '9c8d8a3220c2ea669782409aedfe951e3462f7b3c29072637181186862dd46bb'),
}
HAL_SHA = 'f0995484b411b6d795c56c91ae3ee5c77c39c23f5096513f9cc99f088c312b45'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def run(*args):
    return subprocess.check_output([str(x) for x in args], text=True).strip()


def verify(source):
    source = Path(source).resolve()
    require(source.is_dir(), 'A complete AppleHDA bundle directory is required')
    run('codesign', '--verify', '--deep', '--strict', '-R', '=anchor apple', source)
    records = []
    with tempfile.TemporaryDirectory(prefix='applehda-verify-') as temporary:
        for name, (size, expected) in MODULES.items():
            bundle = source if name == 'AppleHDA' else source / 'Contents/PlugIns' / (name + '.kext')
            info = plistlib.loads((bundle / 'Contents/Info.plist').read_bytes())
            require(info['CFBundleVersion'] == '540.3', 'Unexpected module version: ' + name)
            executable = bundle / 'Contents/MacOS' / info['CFBundleExecutable']
            require(executable.is_file(), 'Missing Mach-O executable: ' + name)
            architectures = run('lipo', '-archs', executable).split()
            require('x86_64' in architectures, 'Missing x86_64 architecture: ' + name)
            candidate = executable
            if len(architectures) > 1:
                candidate = Path(temporary) / name
                run('lipo', executable, '-thin', 'x86_64', '-output', candidate)
            require(candidate.stat().st_size == size and digest(candidate) == expected,
                    'Module differs from the verified 540.3 input: ' + name)
            records.append({'name': name, 'version': '540.3', 'x86_64_sha256': expected, 'bytes': size})
    require(plistlib.loads((source / 'Contents/Info.plist').read_bytes())['CFBundleIdentifier'] == 'com.apple.driver.AppleHDA', 'Unexpected root bundle ID')
    for relative in ['Contents/Resources/Platforms.xml.zlib', 'Contents/Resources/en.lproj/Localizable.strings', 'Contents/Resources/zh_CN.lproj/Localizable.strings']:
        require((source / relative).is_file(), 'Missing required resource: ' + relative)
    hal = source / 'Contents/PlugIns/AppleHDAHALPlugIn.bundle'
    info = plistlib.loads((hal / 'Contents/Info.plist').read_bytes())
    require(info['CFBundleIdentifier'] == 'com.apple.audio.AppleHDAHALPlugIn' and info['CFBundleVersion'] == '540.3', 'Unexpected HAL identity')
    require(digest(hal / 'Contents/MacOS' / info['CFBundleExecutable']) == HAL_SHA, 'HAL differs from verified 540.3 input')
    run('codesign', '--verify', '--deep', '--strict', '-R', '=anchor apple', hal)
    return {'apple_signature_verified': True, 'version': '540.3', 'modules': records, 'hal_sha256': HAL_SHA}


def copy_verified(source, destination):
    source, destination = Path(source).resolve(), Path(destination).absolute()
    require(not destination.exists() and not destination.is_symlink(), 'Refuse to overwrite the output destination')
    require(source != destination.resolve() and source not in destination.resolve().parents,
            'Output must be outside the original AppleHDA bundle')
    report = verify(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, symlinks=True)
    verify(destination)
    return report


def extract(dmg, destination):
    dmg = Path(dmg).resolve()
    require(dmg.stat().st_size == KDK_SIZE and digest(dmg) == KDK_SHA,
            'Expected original KDK 14.8.9 build 23J631 with the recorded SHA256')
    require(not Path(destination).exists() and not Path(destination).is_symlink(), 'Output already exists')
    with tempfile.TemporaryDirectory(prefix='applehda-kdk-') as temporary:
        root = Path(temporary)
        mount = root / 'mount'
        mount.mkdir()
        attached = False
        try:
            run('hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', mount, dmg)
            attached = True
            packages = list(mount.glob('KernelDebugKit.pkg'))
            require(len(packages) == 1, 'Expected exactly one KernelDebugKit.pkg')
            expanded = root / 'expanded'
            run('pkgutil', '--expand-full', packages[0], expanded)
            candidates = list(expanded.rglob('AppleHDA.kext'))
            valid = []
            for candidate in candidates:
                info_path = candidate / 'Contents/Info.plist'
                if info_path.is_file() and plistlib.loads(info_path.read_bytes()).get('CFBundleVersion') == '540.3':
                    valid.append(candidate)
            require(len(valid) == 1, 'Expected exactly one complete 540.3 bundle candidate')
            return copy_verified(valid[0], destination)
        finally:
            if attached:
                run('hdiutil', 'detach', mount)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ['verify', 'copy']:
        command = sub.add_parser(action)
        command.add_argument('--source', type=Path, required=True)
        if action == 'copy':
            command.add_argument('--destination', type=Path, required=True)
    command = sub.add_parser('extract')
    command.add_argument('--dmg', type=Path, required=True)
    command.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    require(sys.platform == 'darwin', 'Run this helper on macOS')
    require(os.geteuid() != 0, 'Run as a regular user; extraction does not require root')
    if args.action == 'verify':
        report = verify(args.source)
    elif args.action == 'copy':
        report = copy_verified(args.source, args.destination)
    else:
        report = extract(args.dmg, args.destination)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
