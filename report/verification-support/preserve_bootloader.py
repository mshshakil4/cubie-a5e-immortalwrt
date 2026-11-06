#!/usr/bin/env python3
"""Create a separate disk-image candidate with a verified A5E bootloader.

This tool never modifies the input image. It requires an MBR-partitioned image,
checks the approved bootloader digest and size, checks the first partition
boundary, writes only the bootloader region at 0x2000, and verifies read-back
and all bytes outside that region before publishing the candidate.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile

BOOTLOADER_OFFSET = 0x2000
EXPECTED_BOOTLOADER_SIZE = 896_329
EXPECTED_BOOTLOADER_SHA256 = "2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb"
SECTOR_SIZE = 512
MBR_PARTITION_TABLE_OFFSET = 446
MBR_PARTITION_ENTRY_SIZE = 16
MBR_PARTITION_COUNT = 4
MBR_SIGNATURE = b"\x55\xaa"


class ValidationError(Exception):
    """Raised when the input cannot be safely assembled."""


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def first_partition_offset(image: Path) -> int:
    """Return earliest non-empty MBR partition start; reject protective GPT MBRs."""
    with image.open("rb") as stream:
        mbr = stream.read(SECTOR_SIZE)
    if len(mbr) != SECTOR_SIZE:
        raise ValidationError("Image is smaller than one MBR sector")
    if mbr[510:512] != MBR_SIGNATURE:
        raise ValidationError("Invalid MBR signature (expected 0x55AA)")
    image_size = image.stat().st_size
    partitions = []
    for index in range(MBR_PARTITION_COUNT):
        pos = MBR_PARTITION_TABLE_OFFSET + index * MBR_PARTITION_ENTRY_SIZE
        entry = mbr[pos:pos + MBR_PARTITION_ENTRY_SIZE]
        boot_flag = entry[0]
        partition_type = entry[4]
        start_lba = int.from_bytes(entry[8:12], "little")
        sectors = int.from_bytes(entry[12:16], "little")
        if partition_type == 0 and start_lba == 0 and sectors == 0:
            continue
        if partition_type == 0xEE:
            raise ValidationError("Protective MBR/GPT image is not supported")
        if partition_type in (0x05, 0x0F, 0x85):
            raise ValidationError("Extended MBR partitions are not supported")
        if boot_flag not in (0x00, 0x80) or partition_type == 0 or start_lba == 0 or sectors == 0:
            raise ValidationError(f"Malformed MBR partition entry {index + 1}")
        start = start_lba * SECTOR_SIZE
        end = (start_lba + sectors) * SECTOR_SIZE
        if end > image_size:
            raise ValidationError(f"MBR partition entry {index + 1} extends beyond image size")
        partitions.append((start, end, index + 1))
    if not partitions:
        raise ValidationError("No non-empty MBR partitions found")
    partitions.sort()
    for previous, current in zip(partitions, partitions[1:]):
        if current[0] < previous[1]:
            raise ValidationError(f"MBR partition entries {previous[2]} and {current[2]} overlap")
    return partitions[0][0]


def _hash_region(stream, length: int, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    remaining = length
    while remaining:
        chunk = stream.read(min(chunk_size, remaining))
        if not chunk:
            raise ValidationError("Unexpected end of image while hashing region")
        digest.update(chunk)
        remaining -= len(chunk)
    return digest.hexdigest()


def _compare_outside_region(source: Path, candidate: Path, start: int, end: int) -> None:
    """Require byte-for-byte equality before start and after end."""
    with source.open("rb") as original, candidate.open("rb") as output:
        original.seek(0)
        output.seek(0)
        remaining = start
        while remaining:
            size = min(1024 * 1024, remaining)
            if original.read(size) != output.read(size):
                raise ValidationError("Candidate differs from source before bootloader region")
            remaining -= size
        original.seek(end)
        output.seek(end)
        while True:
            a, b = original.read(1024 * 1024), output.read(1024 * 1024)
            if a != b:
                raise ValidationError("Candidate differs from source after bootloader region")
            if not a:
                break


def assemble(source_image: Path, bootloader: Path, output_image: Path) -> dict[str, object]:
    source_image = source_image.resolve(strict=True)
    bootloader = bootloader.resolve(strict=True)
    output_image = output_image.absolute()
    if not source_image.is_file() or not bootloader.is_file():
        raise ValidationError("Source image and bootloader must both be regular files")
    if output_image.exists():
        raise ValidationError(f"Refusing to overwrite existing output: {output_image}")
    if output_image.resolve(strict=False) in (source_image, bootloader):
        raise ValidationError("Output path must differ from source image and bootloader")

    bootloader_size = bootloader.stat().st_size
    if bootloader_size != EXPECTED_BOOTLOADER_SIZE:
        raise ValidationError(f"Bootloader size mismatch: got {bootloader_size}, expected {EXPECTED_BOOTLOADER_SIZE}")
    bootloader_hash = sha256_file(bootloader)
    if bootloader_hash != EXPECTED_BOOTLOADER_SHA256:
        raise ValidationError(f"Bootloader SHA-256 mismatch: got {bootloader_hash}, expected {EXPECTED_BOOTLOADER_SHA256}")

    image_size = source_image.stat().st_size
    partition_offset = first_partition_offset(source_image)
    end_offset = BOOTLOADER_OFFSET + bootloader_size
    if BOOTLOADER_OFFSET < SECTOR_SIZE:
        raise ValidationError("Configured bootloader offset overlaps the MBR sector")
    if end_offset > partition_offset:
        raise ValidationError(f"Bootloader ends at {end_offset}, beyond first partition at {partition_offset}")
    if end_offset > image_size:
        raise ValidationError("Bootloader region extends beyond end of source image")

    output_image.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{output_image.name}.", suffix=".tmp", dir=output_image.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        shutil.copyfile(source_image, temp_path)
        with temp_path.open("r+b") as output, bootloader.open("rb") as payload:
            output.seek(BOOTLOADER_OFFSET)
            shutil.copyfileobj(payload, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        with temp_path.open("rb") as candidate:
            candidate.seek(BOOTLOADER_OFFSET)
            readback_hash = _hash_region(candidate, bootloader_size)
        if readback_hash != EXPECTED_BOOTLOADER_SHA256:
            raise ValidationError("Bootloader read-back SHA-256 verification failed")
        if temp_path.stat().st_size != image_size:
            raise ValidationError("Candidate image size changed during assembly")
        _compare_outside_region(source_image, temp_path, BOOTLOADER_OFFSET, end_offset)
        try:
            os.link(temp_path, output_image)
        except FileExistsError:
            raise ValidationError(f"Refusing to overwrite existing output: {output_image}")
        return {
            "status": "UNTESTED — DO NOT FLASH",
            "source_image": str(source_image),
            "candidate_image": str(output_image),
            "image_size": image_size,
            "bootloader_offset": BOOTLOADER_OFFSET,
            "bootloader_size": bootloader_size,
            "bootloader_sha256": bootloader_hash,
            "first_partition_offset": partition_offset,
            "bootloader_end_offset": end_offset,
            "readback_sha256": readback_hash,
            "outside_region_unchanged": True,
        }
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path, help="Normal build image (never modified)")
    parser.add_argument("--bootloader", required=True, type=Path, help="Verified integrated U-Boot/SPL binary")
    parser.add_argument("--output", required=True, type=Path, help="New candidate image path; must not exist")
    args = parser.parse_args(argv)
    try:
        result = assemble(args.image, args.bootloader, args.output)
    except (OSError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
