"""Independent SOF IPC3 wire checks against this 82FF's decoded NHLT.

This does not assert hardware compatibility; the runtime MMIO/stream census
and acoustic capture are separate required gates.
"""
import hashlib
import importlib.util
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
spec = importlib.util.spec_from_file_location('generator', ROOT / 'tools/generate-dai.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class NHLTWireTests(unittest.TestCase):
    def test_physical_pdm0_two_capsules(self):
        p = generator.generate()
        self.assertEqual(len(p), 216)
        self.assertEqual(struct.unpack_from('<4I', p), (216, 0x80010000, 2, 0))
        self.assertEqual(struct.unpack_from('<7H', p, 124), (0, 1, 1, 0, 0, 0, 0))
        self.assertEqual(struct.unpack_from('<I', p, 84)[0], 1)

    def test_exact_clock_and_stereo_containers(self):
        p = generator.generate()
        self.assertEqual(struct.unpack_from('<3I', p, 60), (2400000, 2400000, 48000))
        bits1, bits2, duty_min, duty_max = struct.unpack_from('<4H', p, 76)
        self.assertEqual((bits1, bits2), (32, 32))
        self.assertEqual((duty_min, duty_max), (50, 50))

    def test_reserved_bytes_zero(self):
        p = generator.generate()
        for first, last in ((20, 52), (88, 120), (138, 216)):
            self.assertFalse(any(p[first:last]))


if __name__ == '__main__':
    unittest.main()
