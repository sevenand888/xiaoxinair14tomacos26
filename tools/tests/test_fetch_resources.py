"""Offline safety checks for the resource fetcher; never contact upstream URLs."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / 'fetch-resources.py'
SPEC = importlib.util.spec_from_file_location('resource_fetcher', SCRIPT)
fetcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetcher)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class MemoryResponse(io.BytesIO):
    def geturl(self):
        return 'https://example.invalid/resource'


class ResourceFetcherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='resource-fetch-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'repository'
        self.root.mkdir()
        self.cache = Path(self.temporary.name) / 'cache'
        self.cache.mkdir()
        self.root_patch = mock.patch.object(fetcher, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.network_patch = mock.patch.object(
            fetcher.urllib.request, 'urlopen',
            side_effect=AssertionError('Unexpected network request in offline test'))
        self.network = self.network_patch.start()
        self.addCleanup(self.network_patch.stop)
        self.output_patch = mock.patch('builtins.print')
        self.output_patch.start()
        self.addCleanup(self.output_patch.stop)

    def cached_item(self, data, **fields):
        expected = sha(data)
        (self.cache / expected).write_bytes(data)
        return {
            'id': 'fixture',
            'url': 'https://example.invalid/resource',
            'sha256': expected,
            'destinationBase': 'components',
            **fields,
        }

    def zip_item(self):
        wanted = b'only the requested component'
        unwanted = b'not selected'
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            executable = zipfile.ZipInfo('release/component/tool')
            executable.create_system = 3
            executable.external_attr = 0o100755 << 16
            archive.writestr(executable, wanted)
            archive.writestr('release/other.txt', unwanted)
            archive.writestr('../outside.txt', b'untrusted member name')
        item = self.cached_item(stream.getvalue(), archive_paths=[{
            'source': 'release/component/tool',
            'target': 'tool',
            'sha256': sha(wanted),
        }])
        return item, wanted

    def test_contained_rejects_escape_and_absolute_paths(self):
        cases = ['../outside', 'nested/../../outside', '..\\outside',
                 str(Path(self.temporary.name).resolve() / 'absolute')]
        for relative in cases:
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                fetcher.contained(self.root, relative)
        self.assertEqual(fetcher.contained(self.root, 'nested/file'),
                         self.root / 'nested/file')

    def test_apply_rejects_escaping_destination_base_before_fetch(self):
        item = self.cached_item(b'component', target='file')
        item['destinationBase'] = '../outside'
        with self.assertRaises(ValueError):
            fetcher.apply(item, self.cache)
        self.assertEqual(list(self.root.iterdir()), [])
        self.network.assert_not_called()

    def test_apply_rejects_escaping_file_and_saved_archive_targets(self):
        for field in ['target', 'save_archive_as']:
            with self.subTest(field=field):
                item = self.cached_item(b'component', **{field: '../outside'})
                with self.assertRaises(ValueError):
                    fetcher.apply(item, self.cache)
        self.assertEqual(list(self.root.iterdir()), [])
        self.network.assert_not_called()

    def test_zip_target_cannot_escape_destination(self):
        item, _ = self.zip_item()
        item['archive_paths'][0]['target'] = '../outside'
        with self.assertRaises(ValueError):
            fetcher.apply(item, self.cache)
        self.assertEqual(list(self.root.iterdir()), [])
        self.network.assert_not_called()

    def test_zip_extracts_only_requested_member_from_validated_cache(self):
        item, wanted = self.zip_item()
        fetcher.apply(item, self.cache)
        target = self.root / 'components/tool'
        self.assertEqual(target.read_bytes(), wanted)
        self.assertEqual([p.relative_to(self.root).as_posix()
                          for p in self.root.rglob('*') if p.is_file()],
                         ['components/tool'])
        self.assertFalse((self.root.parent / 'outside.txt').exists())
        self.network.assert_not_called()

    def test_zip_member_hash_failure_does_not_create_target(self):
        item, _ = self.zip_item()
        item['archive_paths'][0]['sha256'] = sha(b'different content')
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            fetcher.apply(item, self.cache)
        self.assertEqual(list(self.root.iterdir()), [])
        self.network.assert_not_called()

    def test_existing_different_file_is_not_overwritten(self):
        item = self.cached_item(b'new component', target='tool')
        target = self.root / 'components/tool'
        target.parent.mkdir()
        target.write_bytes(b'local existing contents')
        with self.assertRaises(ValueError):
            fetcher.apply(item, self.cache)
        self.assertEqual(target.read_bytes(), b'local existing contents')
        self.network.assert_not_called()

    def test_existing_matching_file_is_idempotent(self):
        item = self.cached_item(b'component', target='tool')
        target = self.root / 'components/tool'
        target.parent.mkdir()
        target.write_bytes(b'component')
        before = target.stat().st_mtime_ns
        fetcher.apply(item, self.cache)
        self.assertEqual(target.read_bytes(), b'component')
        self.assertEqual(target.stat().st_mtime_ns, before)
        self.network.assert_not_called()

    def test_download_hash_failure_cleans_temporary_file(self):
        self.network.side_effect = None
        self.network.return_value = MemoryResponse(b'tampered download')
        expected = sha(b'expected resource')
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            fetcher.fetch('https://example.invalid/resource', expected, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])
        self.network.assert_called_once()

    def test_network_failure_cleans_temporary_file_and_preserves_error(self):
        self.network.side_effect = urllib.error.URLError('fixture connection failed')
        with self.assertRaises(urllib.error.URLError):
            fetcher.fetch('https://example.invalid/resource', sha(b'expected'), self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_zip_symlink_member_is_rejected(self):
        stream = io.BytesIO()
        link_data = b'../../outside'
        with zipfile.ZipFile(stream, 'w') as archive:
            link = zipfile.ZipInfo('release/link')
            link.create_system = 3
            link.external_attr = 0o120777 << 16
            archive.writestr(link, link_data)
        item = self.cached_item(stream.getvalue(), archive_paths=[{
            'source': 'release/link', 'target': 'link', 'sha256': sha(link_data),
        }])
        with self.assertRaises(ValueError):
            fetcher.apply(item, self.cache)
        self.assertEqual(list(self.root.iterdir()), [])
        self.network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
