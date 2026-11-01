"""Exercise identity insertion using synthetic identities and temporary files."""
import copy
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'tools' / 'personalize-config.py'
TEMPLATE = ROOT / 'tahoe26' / 'configs' / 'config-install.plist'


class PersonalizeConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.config = self.work / 'config.plist'
        self.original_bytes = TEMPLATE.read_bytes()
        self.config.write_bytes(self.original_bytes)
        self.identity_path = self.work / 'identity.json'
        self.identity = {
            'MLB': 'TEST0000000000001',
            'SystemSerialNumber': 'TEST00000001',
            'SystemUUID': '01234567-89ab-4cde-8fab-0123456789ab',
            'ROM': '0200000000ab',
        }
        self.output = self.work / 'nested' / 'config.private.plist'

    def run_tool(self, identity=None, output=None):
        self.identity_path.write_text(
            json.dumps(self.identity if identity is None else identity),
            encoding='utf-8-sig',
        )
        return subprocess.run(
            [sys.executable, str(SCRIPT), '--identity', str(self.identity_path),
             '--config', str(self.config), '--output', str(output or self.output)],
            capture_output=True,
        )

    def test_writes_only_four_identity_fields_and_preserves_template(self):
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = plistlib.loads(self.original_bytes)
        expected['PlatformInfo']['Generic'].update(
            MLB=self.identity['MLB'],
            SystemSerialNumber=self.identity['SystemSerialNumber'],
            SystemUUID=self.identity['SystemUUID'].upper(),
            ROM=bytes.fromhex(self.identity['ROM']),
        )
        self.assertEqual(plistlib.loads(self.output.read_bytes()), expected)
        self.assertEqual(self.config.read_bytes(), self.original_bytes)

    def test_refuses_overwriting_template_or_existing_output(self):
        result = self.run_tool(output=self.config)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_bytes(), self.original_bytes)
        self.output.parent.mkdir()
        self.output.write_bytes(b'keep existing output')
        result = self.run_tool()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_bytes(), b'keep existing output')

    def test_invalid_identity_is_rejected_before_creating_output(self):
        cases = [
            ('MLB', ''), ('MLB', 'invalid value'),
            ('SystemSerialNumber', None), ('SystemSerialNumber', 'test-123'),
            ('SystemUUID', 'invalid'),
            ('SystemUUID', '00000000-0000-0000-0000-000000000000'),
            ('ROM', '000000000000'), ('ROM', '0200000000'),
            ('ROM', '0200000000zz'),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                identity = dict(self.identity, **{field: value})
                result = self.run_tool(identity=identity)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())
                self.assertEqual(self.config.read_bytes(), self.original_bytes)

    def test_rejects_other_system_product(self):
        other = copy.deepcopy(plistlib.loads(self.original_bytes))
        other['PlatformInfo']['Generic']['SystemProductName'] = 'MacBookPro16,1'
        self.config.write_bytes(plistlib.dumps(other, sort_keys=False))
        result = self.run_tool()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
