"""Safely unpack an incoming ZIP archive into the configured data directory."""

import argparse
import stat
import zipfile
from pathlib import Path


def extract_zip(archive_path: Path, destination: Path) -> list[Path]:
	"""Extract regular files while rejecting archive paths outside destination."""
	destination = destination.resolve()
	destination.mkdir(parents=True, exist_ok=True)
	extracted_files = []

	with zipfile.ZipFile(archive_path) as archive:
		for member in archive.infolist():
			member_path = Path(*Path(member.filename.replace("\\", "/")).parts)
			target = (destination / member_path).resolve()
			if not target.is_relative_to(destination):
				raise ValueError(f"Archive member escapes destination: {member.filename}")

			mode = member.external_attr >> 16
			if stat.S_ISLNK(mode):
				raise ValueError(f"Symbolic links are not allowed: {member.filename}")
			if member.is_dir():
				target.mkdir(parents=True, exist_ok=True)
				continue

			target.parent.mkdir(parents=True, exist_ok=True)
			with archive.open(member) as source, target.open("wb") as output:
				while chunk := source.read(1024 * 1024):
					output.write(chunk)
			extracted_files.append(target)

	return extracted_files


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("archive", type=Path)
	parser.add_argument("destination", type=Path)
	args = parser.parse_args()
	files = extract_zip(args.archive, args.destination)
	print(f"Extracted {len(files)} file(s) to {args.destination}")


if __name__ == "__main__":
	main()
