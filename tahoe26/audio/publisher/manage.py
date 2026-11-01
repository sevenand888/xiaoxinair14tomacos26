#!/usr/bin/env python3
"""Receipt-based installation/removal of the one-shot publication service.
Fresh install refuses every existing target. Removal compares all installed
hashes before bootout, then moves owned files to a protected rollback backup.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import sys
import time

LABEL = 'local.codex.Lenovo82FFSSTPublish'
HELPERS = Path('/Library/PrivilegedHelperTools')
DEST = HELPERS / LABEL
DAEMONS = Path('/Library/LaunchDaemons')
PLIST = DAEMONS / (LABEL + '.plist')
BACKUPS = Path('/Library/Application Support/Lenovo82FFSSTPublish/Backups')
LOG = Path('/private/var/log/lenovo82ff-sst-publish.log')
PACKAGE = Path(__file__).resolve().parent
PUBLISHER_SHA = '55e2936f6fe9caf300711d687ec1d2c39e80e2f734b1c29d6611be690c03d4bd'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protected(path, directory=False):
    st = path.lstat()
    require(not stat.S_ISLNK(st.st_mode) and st.st_uid == 0 and not st.st_mode & 0o022,
            'Unprotected/symlink path: ' + str(path))
    require(stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode), 'Wrong file type: ' + str(path))


def mkdir_protected(path, mode=0o755):
    require(path.is_absolute(), 'Absolute protected path required')
    if path.exists() or path.is_symlink():
        protected(path, True)
        return
    mkdir_protected(path.parent)
    path.mkdir(mode=mode)
    os.chown(path, 0, 0)
    protected(path, True)


def copy_new(source, destination, mode):
    require(not destination.exists() and not destination.is_symlink(), 'Refuse to overwrite: ' + str(destination))
    data = Path(source).read_bytes()
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
        os.fchown(stream.fileno(), 0, 0)
        os.fchmod(stream.fileno(), mode)
    require(sha(destination) == hashlib.sha256(data).hexdigest(), 'Copy verification failed')


def launchctl(*arguments, allow_failure=False):
    result = subprocess.run(['/bin/launchctl', *map(str,arguments)], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    if not allow_failure:
        require(result.returncode == 0, 'launchctl failed: ' + result.stdout)
    return result


def new_backup(kind):
    mkdir_protected(BACKUPS, 0o700)
    path = BACKUPS / (time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid()) + '-' + kind)
    path.mkdir(mode=0o700)
    os.chown(path, 0, 0)
    return path


def installed_receipt():
    protected(DEST, True)
    receipt_path = DEST / 'receipt.json'
    protected(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    require(receipt.get('label') == LABEL and receipt.get('version') == 1, 'Unknown installation receipt')
    require(set(p.name for p in DEST.iterdir()) == {'publish','publish-once.sh','receipt.json'}, 'Unknown files in helper directory')
    expected = {str(DEST/'publish'),str(DEST/'publish-once.sh'),str(PLIST)}
    require(set(receipt['installedHashes']) == expected, 'Receipt target set differs')
    for name,digest in receipt['installedHashes'].items():
        path = Path(name)
        protected(path)
        require(sha(path) == digest, 'Installed file changed; refusing overwrite/removal: ' + name)
    return receipt


def install(activate):
    manifest = json.loads((PACKAGE/'package-manifest.json').read_text())
    require(manifest['publisherSHA256'] == PUBLISHER_SHA, 'Unexpected publisher manifest')
    for name,digest in manifest['files'].items():
        require(name in {'publish','publish-once.sh',LABEL+'.plist','manage.py'}, 'Unknown package path')
        require(sha(PACKAGE/name) == digest, 'Reviewed package hash differs: ' + name)
    require(set(manifest['files']) == {'publish','publish-once.sh',LABEL+'.plist','manage.py'}, 'Incomplete package')
    require(sha(PACKAGE/'publish') == PUBLISHER_SHA, 'Publisher differs from reviewed binary')
    require(not DEST.exists() and not DEST.is_symlink() and not PLIST.exists() and not PLIST.is_symlink(),
            'Installation target already exists; no upgrade/overwrite is implicit')
    require(launchctl('print','system/'+LABEL,allow_failure=True).returncode != 0, 'Launch job already registered')
    for parent in [HELPERS,DAEMONS,LOG.parent]:
        mkdir_protected(parent)
    require(not LOG.exists() and not LOG.is_symlink(), 'Fresh install refuses an existing log path; preserve/review it first')
    backup = new_backup('install')
    for name in manifest['files']:
        copy_new(PACKAGE/name,backup/name,0o600)
    copy_new(PACKAGE/'package-manifest.json',backup/'package-manifest.json',0o600)
    receipt = {'version':1,'label':LABEL,'backup':str(backup),'originalTargets':'absent','logPath':str(LOG),
               'installedHashes':{str(DEST/'publish'):manifest['files']['publish'],
                                  str(DEST/'publish-once.sh'):manifest['files']['publish-once.sh'],
                                  str(PLIST):manifest['files'][LABEL+'.plist']}}
    created = []
    try:
        DEST.mkdir(mode=0o755);os.chown(DEST,0,0)
        for name in ['publish','publish-once.sh']:
            copy_new(PACKAGE/name,DEST/name,0o755);created.append(DEST/name)
        receipt_path = DEST/'receipt.json'
        receipt_path.write_text(json.dumps(receipt,indent=2)+'\n');os.chown(receipt_path,0,0);receipt_path.chmod(0o644)
        created.append(receipt_path)
        copy_new(PACKAGE/(LABEL+'.plist'),PLIST,0o644);created.append(PLIST)
        if not LOG.exists():
            fd=os.open(LOG,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o640)
            os.fchown(fd,0,0);os.close(fd)
            created.append(LOG)
        installed_receipt()
        if activate:
            launchctl('bootstrap','system',PLIST)
        print(json.dumps({'status':'installed','activated':activate,'backup':str(backup),'log':str(LOG)},indent=2))
    except BaseException:
        # Stop only our registered label, then preserve created content, never delete arbitrary files.
        launchctl('bootout','system/'+LABEL,allow_failure=True)
        for path in created:
            if path.exists():
                expected = receipt['installedHashes'].get(str(path))
                require(not expected or sha(path)==expected, 'Rollback stopped: installed target changed')
                os.rename(path,backup/('failed-'+path.name))
        if DEST.exists() and not list(DEST.iterdir()):
            DEST.rmdir()
        raise


def uninstall():
    receipt = installed_receipt()  # All comparisons precede bootout or filesystem mutation.
    require(receipt.get('logPath') == str(LOG), 'Receipt log path differs')
    protected(LOG)
    backup = new_backup('uninstall')
    present = launchctl('print','system/'+LABEL,allow_failure=True).returncode == 0
    if present:
        launchctl('bootout','system/'+LABEL)
    require(launchctl('print','system/'+LABEL,allow_failure=True).returncode != 0,'Job still registered')
    installed_receipt()  # Compare again immediately before moving only our known targets.
    os.rename(PLIST,backup/PLIST.name)
    os.rename(DEST,backup/'helpers')
    os.rename(LOG,backup/LOG.name)
    (backup/'uninstall-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':'uninstalled','backup':str(backup),
                      'note':'Current published device and default input untouched; next boot has no publisher job.'},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['install','uninstall','verify'])
    parser.add_argument('--activate',action='store_true',help='Bootstrap only after installation; otherwise takes effect next boot')
    args=parser.parse_args()
    require(sys.platform=='darwin' and os.geteuid()==0,'Run manually as root on macOS')
    if args.action=='install':install(args.activate)
    elif args.action=='uninstall':uninstall()
    else:print(json.dumps(installed_receipt(),indent=2))


if __name__=='__main__':
    main()
