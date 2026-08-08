from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import ExifTags, Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ingest_photography as ingest  # noqa: E402


class PhotographyIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="photography-ingest-test-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def image(
        self,
        name: str = "master.jpg",
        size: tuple[int, int] = (2400, 1600),
        with_gps: bool = False,
    ) -> Path:
        path = self.root / name
        value = Image.new("RGB", size, (72, 91, 104))
        exif = Image.Exif()
        exif[271] = "Test Camera Co"
        exif[272] = "Test Camera"
        if with_gps:
            gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
            gps[1] = "N"
            gps[2] = (1.0, 2.0, 3.0)
        value.save(path, quality=94, exif=exif)
        return path

    def test_source_unchanged_and_four_safe_variants(self) -> None:
        source = self.image(with_gps=True)
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        inspection = ingest.inspect_source(source, "P015")
        self.assertTrue(inspection.exif["gpsPresentInMaster"])
        destination = ingest.write_ingest(inspection, self.root / "output", 1)
        self.assertEqual(before, hashlib.sha256(source.read_bytes()).hexdigest())
        for variant, settings in ingest.VARIANTS.items():
            path = destination / "derivatives" / variant / f"P015-v1-{variant}.jpg"
            self.assertTrue(path.is_file())
            with Image.open(path) as image:
                self.assertEqual(max(image.size), settings["long_edge"])
                self.assertNotIn(34853, image.getexif())
                self.assertEqual(image.getexif().get(315), "Kexing Yan")
        download = destination / "derivatives" / "download" / "P015-v1-download.jpg"
        self.assertNotEqual(download.read_bytes(), source.read_bytes())
        self.assertTrue((destination / "draft.private.json").is_file())

    def test_corrupt_jpeg_is_rejected(self) -> None:
        path = self.root / "corrupt.jpg"
        path.write_bytes(b"\xff\xd8\xffnot-an-image")
        with self.assertRaisesRegex(ValueError, "decode failed"):
            ingest.inspect_source(path, "P015")

    def test_unsupported_mime_is_rejected(self) -> None:
        path = self.root / "payload.gif"
        path.write_bytes(b"GIF89a" + b"0" * 20)
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            ingest.inspect_source(path, "P015")

    def test_oversized_encoded_file_is_rejected(self) -> None:
        path = self.root / "large.jpg"
        with path.open("wb") as handle:
            handle.write(b"\xff\xd8\xff")
            handle.seek(ingest.MAX_BYTES)
            handle.write(b"x")
        with self.assertRaisesRegex(ValueError, "exceeds 50 MiB"):
            ingest.inspect_source(path, "P015")

    def test_oversized_dimension_is_rejected(self) -> None:
        path = self.image("wide.png", (ingest.MAX_DIMENSION + 1, 1))
        with self.assertRaisesRegex(ValueError, "12,000px"):
            ingest.inspect_source(path, "P015")

    def test_duplicate_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            ingest.allocate_ids(1, {"P001", "P015"}, "P015")

    def test_dry_run_writes_nothing(self) -> None:
        source = self.image()
        output = self.root / "dry-output"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "ingest_photography.py"),
                str(source),
                "--output", str(output),
                "--dry-run",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("no files or directories written", result.stdout)
        self.assertFalse(output.exists())

    def test_batch_dry_run_allocates_distinct_stable_ids(self) -> None:
        batch = self.root / "batch"
        batch.mkdir()
        self.image("batch/first.jpg", (800, 600))
        self.image("batch/second.png", (600, 800))
        output = self.root / "batch-output"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "ingest_photography.py"),
                str(batch),
                "--output", str(output),
                "--dry-run",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("P015:", result.stdout)
        self.assertIn("P016:", result.stdout)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
