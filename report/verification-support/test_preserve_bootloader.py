import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "preserve_bootloader.py"
spec = importlib.util.spec_from_file_location("preserve_bootloader", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PreserveBootloaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.image = self.root / "input.img"
        self.boot = self.root / "boot.bin"
        self.output = self.root / "candidate.img"
        self.payload = b"A5E-TEST-BOOTLOADER"
        module.EXPECTED_BOOTLOADER_SIZE = len(self.payload)
        module.EXPECTED_BOOTLOADER_SHA256 = hashlib.sha256(self.payload).hexdigest()
        self._write_mbr(self.image, first_lba=2048)
        with self.image.open("r+b") as f:
            f.seek(1024 * 1024)
            f.write(b"PARTITION-DATA")
        self.boot.write_bytes(self.payload)

    def tearDown(self):
        self.tmp.cleanup()
        module.EXPECTED_BOOTLOADER_SIZE = 896_329
        module.EXPECTED_BOOTLOADER_SHA256 = "2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb"

    @staticmethod
    def _write_mbr(path, first_lba=2048, partition_type=0x83, signature=b"\x55\xaa"):
        data = bytearray(2 * 1024 * 1024)
        data[510:512] = signature
        entry = 446
        data[entry + 4] = partition_type
        data[entry + 8:entry + 12] = first_lba.to_bytes(4, "little")
        data[entry + 12:entry + 16] = (1024).to_bytes(4, "little")
        path.write_bytes(data)

    def test_success_creates_candidate_and_preserves_other_bytes(self):
        before = self.image.read_bytes()
        result = module.assemble(self.image, self.boot, self.output)
        after = self.output.read_bytes()
        self.assertEqual(self.image.read_bytes(), before)
        self.assertEqual(after[:module.BOOTLOADER_OFFSET], before[:module.BOOTLOADER_OFFSET])
        start, end = module.BOOTLOADER_OFFSET, module.BOOTLOADER_OFFSET + len(self.payload)
        self.assertEqual(after[start:end], self.payload)
        self.assertEqual(after[end:], before[end:])
        self.assertTrue(result["outside_region_unchanged"])
        self.assertEqual(result["readback_sha256"], hashlib.sha256(self.payload).hexdigest())

    def test_rejects_bad_hash(self):
        self.boot.write_bytes(b"wrong payload")
        with self.assertRaises(module.ValidationError):
            module.assemble(self.image, self.boot, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_partition_overlap(self):
        self._write_mbr(self.image, first_lba=8)
        with self.assertRaises(module.ValidationError):
            module.assemble(self.image, self.boot, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_invalid_mbr_signature(self):
        self._write_mbr(self.image, signature=b"\x00\x00")
        with self.assertRaises(module.ValidationError):
            module.assemble(self.image, self.boot, self.output)

    def test_rejects_protective_gpt_mbr(self):
        self._write_mbr(self.image, partition_type=0xEE)
        with self.assertRaises(module.ValidationError):
            module.assemble(self.image, self.boot, self.output)

    def test_rejects_partition_past_end_of_image(self):
        self._write_mbr(self.image, first_lba=2048)
        data = bytearray(self.image.read_bytes())
        entry = 446
        data[entry + 12:entry + 16] = (999999).to_bytes(4, "little")
        self.image.write_bytes(data)
        with self.assertRaises(module.ValidationError):
            module.assemble(self.image, self.boot, self.output)

    def test_rejects_overlapping_mbr_partitions(self):
        self._write_mbr(self.image, first_lba=8)
        data = bytearray(self.image.read_bytes())
        second = 446 + 16
        data[second + 4] = 0x83
        data[second + 8:second + 12] = (10).to_bytes(4, "little")
        data[second + 12:second + 16] = (100).to_bytes(4, "little")
        self.image.write_bytes(data)
        with self.assertRaises(module.ValidationError):
            module.assemble(self.image, self.boot, self.output)

    def test_refuses_to_overwrite_output(self):
        self.output.write_bytes(b"do not overwrite")
        with self.assertRaises(module.ValidationError):
            module.assemble(self.image, self.boot, self.output)
        self.assertEqual(self.output.read_bytes(), b"do not overwrite")

    def test_refuses_wrong_size(self):
        module.EXPECTED_BOOTLOADER_SIZE = len(self.payload) + 1
        with self.assertRaises(module.ValidationError):
            module.assemble(self.image, self.boot, self.output)

    def test_rejects_invalid_partition_boot_flag(self):
        data = bytearray(self.image.read_bytes())
        data[446] = 0x01
        self.image.write_bytes(data)
        with self.assertRaises(module.ValidationError):
            module.first_partition_offset(self.image)

    def test_refuses_output_path_equal_to_source_image(self):
        before = self.image.read_bytes()
        with self.assertRaises(module.ValidationError):
            module.assemble(self.image, self.boot, self.image)
        self.assertEqual(self.image.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
