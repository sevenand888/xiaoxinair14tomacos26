#!/usr/bin/env python3
"""按资源清单从上游获取组件，核对 SHA256 后放到对应目录。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def contained(base, relative):
    if Path(relative).is_absolute() or '\\' in relative:
        raise ValueError('目标应为相对目录，使用 / 分隔：' + relative)
    result = (base / relative).resolve()
    result.relative_to(base.resolve())
    return result


def checked_hash(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value.lower()):
        raise ValueError('资源清单缺少完整 SHA256')
    return value.lower()


def fetch(url, expected, cache):
    expected = checked_hash(expected)
    if urllib.parse.urlparse(url).scheme != 'https':
        raise ValueError('资源地址应使用 HTTPS')
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / expected
    if destination.is_file() and digest(destination) == expected:
        return destination
    request = urllib.request.Request(url, headers={'User-Agent': 'Lenovo82FF-resource-fetcher/1.0'})
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=cache, prefix='download-', delete=False) as stream:
            temporary = Path(stream.name)
            with urllib.request.urlopen(request, timeout=90) as response:
                if urllib.parse.urlparse(response.geturl()).scheme != 'https':
                    raise ValueError('下载重定向未使用 HTTPS')
                shutil.copyfileobj(response, stream)
            stream.flush()
            os.fsync(stream.fileno())
        if digest(temporary) != expected:
            raise ValueError('下载文件 SHA256 与清单不一致：' + url)
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def install_bytes(data, destination, expected, mode=0o644):
    expected = checked_hash(expected)
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('目标内容 SHA256 与清单不一致：' + str(destination))
    if destination.exists():
        if destination.is_file() and digest(destination) == expected:
            return
        raise ValueError('目标已有不同内容，请先保存现有文件：' + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(data)
    destination.chmod(mode)


def apply(item, cache):
    if item.get('kind') == 'disabled-reference':
        print('跳过关闭条目：', item['id'])
        return
    if item.get('kind') in ('local-build', 'manual') or not item.get('url'):
        print('按文档准备：', item['id'], item.get('note', ''))
        return
    base = contained(ROOT, item['destinationBase'])
    downloaded = fetch(item['url'], item['sha256'], cache)
    if item.get('target'):
        install_bytes(downloaded.read_bytes(), contained(base, item['target']), item['sha256'])
    if item.get('archive_paths'):
        with zipfile.ZipFile(downloaded) as archive:
            for entry in item['archive_paths']:
                info = archive.getinfo(entry['source'])
                filetype = (info.external_attr >> 16) & 0o170000
                if info.is_dir() or filetype == 0o120000:
                    raise ValueError('清单提取项应为普通文件：' + entry['source'])
                mode = 0o755 if (info.external_attr >> 16) & 0o111 else 0o644
                install_bytes(archive.read(info), contained(base, entry['target']), entry['sha256'], mode)
    if item.get('save_archive_as'):
        install_bytes(downloaded.read_bytes(), contained(base, item['save_archive_as']), item['sha256'])
    print('已核验：', item['id'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--list', action='store_true', help='列出条目，不下载')
    parser.add_argument('--id', action='append', dest='ids', help='只处理指定条目，可重复')
    parser.add_argument('--cache-dir', type=Path, default=ROOT / '.cache' / 'downloads')
    args = parser.parse_args()
    items = json.loads(args.manifest.read_text(encoding='utf-8-sig'))['items']
    if args.ids:
        missing = set(args.ids) - {item['id'] for item in items}
        if missing:
            parser.error('未找到条目：' + ', '.join(sorted(missing)))
        items = [item for item in items if item['id'] in args.ids]
    for item in items:
        if args.list:
            print(item['id'], item.get('kind', 'download'), item.get('note', ''))
        else:
            apply(item, args.cache_dir.resolve())


if __name__ == '__main__':
    main()
