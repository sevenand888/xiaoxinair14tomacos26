#!/usr/bin/env python3
"""Build SimpleHDA and its HAL package locally with Command Line Tools.

Derived from upstream Tools/generate_project.py at 7517b04.
Requires macOS Command Line Tools, Python 3, and a complete AppleHDA bundle.
Validated with Apple clang 16 and Python 3.9.6 using AppleHDA 540.3.
Only compile-command conventions are adapted; upstream source is obtained separately.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shlex
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--payload', required=True, type=Path, help='Complete original AppleHDA.kext, including all Mach-O binaries')
    parser.add_argument('--developer-dir', type=Path, help='CommandLineTools or Xcode Developer directory')
    parser.add_argument('--configuration', choices=['Debug', 'Release'], default='Debug')
    parser.add_argument('--hal-package', action='store_true', help='Also build the matching HAL installer; does not install it')
    parser.add_argument('--hdau-reference', type=Path, help='Optional local original HDAUniversal executable for the historical guard test; never loaded')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('This build must run on macOS; no files were changed.')
    if os.geteuid() == 0:
        parser.error('Build as a regular user, not root.')
    repo = args.repo.resolve()
    payload = args.payload.resolve()
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['SIMPLEHDA_SOURCE'] = str(payload)
    if args.developer_dir:
        env['DEVELOPER_DIR'] = str(args.developer_dir.resolve())
    pin = json.loads((Path(__file__).resolve().parent / 'source-pin.json').read_text())
    actual = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != pin['upstream_commit']:
        parser.error('Unexpected upstream commit')
    patched = (repo / 'Sources/kern_start.cpp').read_text(encoding='utf-8').encode()
    if hashlib.sha256(patched).hexdigest() != pin['patched_kern_start_sha256_lf']:
        parser.error('Apply the supplied preprobe.patch to the pinned source first')
    for name, expected in pin['added_files'].items():
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != expected:
            parser.error('Missing or changed added source: ' + name)
    config = args.configuration
    build = repo / 'Build' / config
    objects = build / 'Objects-CLT'
    objects.mkdir(parents=True, exist_ok=True)
    log_path = build / 'clt-build.log'
    commands = []
    with log_path.open('w') as log:
        def run(command, capture=False):
            command = [str(v) for v in command]
            commands.append(command)
            rendered = shlex.join(command)
            print(rendered, flush=True)
            log.write('$ ' + rendered + '\n')
            log.flush()
            result = subprocess.run(command, cwd=repo, env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            log.write(result.stdout)
            log.flush()
            if result.returncode:
                print(result.stdout[-16000:], file=sys.stderr)
                raise subprocess.CalledProcessError(result.returncode, command)
            if not capture and result.stdout:
                print(result.stdout[-6000:], end='', flush=True)
            return result.stdout.strip()

        run([sys.executable, Path(__file__).resolve().parent / 'prepare-applehda.py', 'verify', '--source', payload])
        required = [payload] + [payload / 'Contents/PlugIns' / (name + '.kext') for name in
                               ['IOHDAFamily', 'AppleHDAController', 'DspFuncLib', 'AppleHDAHardwareConfigDriver']]
        for bundle in required:
            info = plistlib.loads((bundle / 'Contents/Info.plist').read_bytes())
            executable = bundle / 'Contents/MacOS' / info['CFBundleExecutable']
            if not executable.is_file():
                raise SystemExit('Missing payload executable: ' + str(executable))
            if 'x86_64' not in run(['lipo', '-archs', executable], capture=True).split():
                raise SystemExit('Missing x86_64 slice: ' + str(executable))
        # Verify this alternative bundle independently; keep upstream Resources unchanged.
        run(['codesign', '--verify', '--deep', '--strict', payload])
        run([sys.executable, 'Tools/setup.py'])
        run([sys.executable, 'Tools/verify.py', '--source'])
        run([sys.executable, 'Tools/prepare_vendor.py'])
        run([sys.executable, 'Tools/prepare_payload.py'])
        clang = run(['xcrun', '--find', 'clang'], capture=True)
        sdk = run(['xcrun', '--show-sdk-path'], capture=True)
        resource = run([clang, '-print-resource-dir'], capture=True)
        source_info = plistlib.loads((repo / 'Info.plist').read_bytes())
        version = source_info['CFBundleVersion']
        compile_flags = [
            '-target', 'x86_64-apple-macos10.15', '-isysroot', sdk,
            '-mkernel', '-fno-builtin', '-fno-stack-protector',
            '-fno-asynchronous-unwind-tables', '-mno-red-zone',
            '-mno-sse', '-mno-sse2', '-mno-mmx', '-nostdinc',
            '-fvisibility=hidden', '-Wno-deprecated-declarations',
            '-Wno-sign-conversion', '-Wno-shadow', '-g',
            '-ffile-prefix-map=' + str(repo) + '=.',
            '-fdebug-prefix-map=' + str(repo) + '=.',
            '-O0' if config == 'Debug' else '-Os',
            '-DKERNEL=1', '-DKERNEL_PRIVATE=1',
            '-D__ASSERT_MACROS_DEFINE_VERSIONS_WITHOUT_UNDERSCORES=1',
            '-DPRODUCT_NAME=SimpleHDA', '-DMODULE_VERSION=' + version,
            '-DLILU_CUSTOM_KMOD_INIT=1',
            '-I' + str(repo / 'Generated/Headers'),
            '-I' + str(repo / 'Generated/kxld'),
            '-I' + str(repo / 'Sources'),
            '-I' + str(repo / 'Vendor/Lilu/Lilu'),
            '-I' + str(repo / 'Vendor/MacKernelSDK/Headers'),
            '-isystem', str(Path(resource) / 'include'),
        ]
        if config == 'Debug':
            compile_flags.append('-DDEBUG=1')
        # Xcode normally emits this kmod metadata translation unit itself.
        kmod = objects / 'SimpleHDA_info.c'
        kmod.write_text('''#include <mach/mach_types.h>
#include <mach/kmod.h>
extern kern_return_t _start(kmod_info_t *, void *);
extern kern_return_t _stop(kmod_info_t *, void *);
extern kern_return_t SimpleHDA_kern_start(kmod_info_t *, void *);
extern kern_return_t SimpleHDA_kern_stop(kmod_info_t *, void *);
__attribute__((visibility("default")))
KMOD_EXPLICIT_DECL(cn.laobamac.SimpleHDA, "''' + version + '''", _start, _stop)
__private_extern__ kmod_start_func_t *_realmain = SimpleHDA_kern_start;
__private_extern__ kmod_stop_func_t *_antimain = SimpleHDA_kern_stop;
__private_extern__ int _kext_apple_cc = __APPLE_CC__;
''')
        run(['xcrun', 'clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', 'Tools/test_hdau_identity.cpp', '-o', build / 'test-hdau-identity'])
        if args.hdau_reference:
            reference = args.hdau_reference.resolve()
            expected = 'e4d49303de9db4a2022a569da97260b55926c13bdabf38ce8b7083caa925d7ed'
            if hashlib.sha256(reference.read_bytes()).hexdigest() != expected:
                parser.error('HDAUniversal reference differs from the historical test input')
            run([build / 'test-hdau-identity', reference])
        else:
            print('Guard test compiled; runtime test skipped because no optional archived HDAUniversal reference was supplied.')
        sources = sorted((repo / 'Sources').glob('*.cpp'))
        sources += [repo / 'Vendor/Lilu/Lilu/Library/plugin_start.cpp',
                    repo / 'Generated/Payload.cpp', repo / 'Generated/Payload.S']
        sources += sorted(p for p in (repo / 'Generated/kxld').glob('*.c') if not p.name.startswith('WKdm'))
        sources.append(kmod)
        compiled = []
        for number, source in enumerate(sources):
            target = objects / ('%02d_%s.o' % (number, source.stem))
            flags = compile_flags.copy()
            if source.suffix == '.cpp':
                flags += ['-std=c++17', '-fno-exceptions', '-fno-rtti', '-fapple-kext']
            elif source.suffix == '.c':
                flags += ['-std=gnu11']
            run([clang, *flags, '-c', source, '-o', target])
            compiled.append(target)
        bundle = build / 'SimpleHDA.kext'
        binary = bundle / 'Contents/MacOS/SimpleHDA'
        binary.parent.mkdir(parents=True, exist_ok=True)
        run([clang, '-target', 'x86_64-apple-macos10.15', '-isysroot', sdk,
             '-nostdlib', '-Wl,-kext', '-Wl,-no_fixup_chains',
             '-Wl,-undefined,dynamic_lookup', *compiled,
             '-L' + str(repo / 'Vendor/MacKernelSDK/Library/universal'),
             '-lkmod', '-o', binary])
        def expand(value):
            if isinstance(value, str):
                return value.replace('$(EXECUTABLE_NAME)', 'SimpleHDA').replace('$(PRODUCT_BUNDLE_IDENTIFIER)', 'cn.laobamac.SimpleHDA')
            if isinstance(value, dict):
                return {k: expand(v) for k, v in value.items()}
            if isinstance(value, list):
                return [expand(v) for v in value]
            return value
        (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps(expand(source_info)))
        run([sys.executable, 'Tools/verify.py', '--configuration', config])
        run(['otool', '-hV', binary])
        undefined = run(['nm', '-u', binary], capture=True)
        (build / 'undefined-symbols.txt').write_text(undefined + '\n')
        (build / 'clt-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        report = {'experimental': True, 'runtime_verified': False, 'source_payload': str(payload),
                  'payload_manifest': json.loads((repo / 'Generated/PayloadManifest.json').read_text()),
                  'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                  'upstream_commit': run(['git', 'rev-parse', 'HEAD'], capture=True)}
        (build / 'clt-build-manifest.json').write_text(json.dumps(report, indent=2) + '\n')
        if args.hal_package:
            run([sys.executable, 'Tools/prepare_hal.py'])
        print('Built and statically verified: ' + str(bundle))


if __name__ == '__main__':
    main()
