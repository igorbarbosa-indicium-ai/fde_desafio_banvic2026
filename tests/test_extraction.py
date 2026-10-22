import tempfile
import unittest
import zipfile
from pathlib import Path

from app.extraction import extract_zip


class ExtractZipTests(unittest.TestCase):
    def test_extracts_files_under_destination(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "incoming.zip"
            destination = root / "extracted"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("nested/data.csv", "id,name\n1,Ada\n")

            files = extract_zip(archive_path, destination)

            self.assertEqual([(destination / "nested/data.csv").resolve()], files)
            self.assertEqual("id,name\n1,Ada\n", files[0].read_text())

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "incoming.zip"
            destination = root / "extracted"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside.csv", "unexpected")

            with self.assertRaises(ValueError):
                extract_zip(archive_path, destination)
            self.assertFalse((root / "outside.csv").exists())


if __name__ == "__main__":
    unittest.main()