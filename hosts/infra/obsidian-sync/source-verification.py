#!/usr/bin/env python3
"""Bind a split photo tar to an independently hashed, stable source inventory."""

import argparse
import bisect
import datetime
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile


INVENTORY = "SOURCE-FILES.jsonl"
RECEIPT = "SOURCE-VERIFIED.json"
FORMAT = "dothomelab-source-sha256-v1"
BLOCK = 1024 * 1024


class InvalidBackup(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidBackup(message)


def digest(stream):
    result = hashlib.sha256()
    while data := stream.read(BLOCK):
        result.update(data)
    return result.hexdigest()


def file_digest(path):
    with open(path, "rb") as stream:
        return digest(stream)


def signature(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns]


def roots_for(dataset):
    require(dataset in ("photos", "immich"), "Unsupported source dataset")
    return ["."] if dataset == "photos" else ["upload", "library"]


def scan(source, dataset):
    """Do not silently omit symlinks, special files, or nested filesystems."""
    entries = {}
    device = source.stat().st_dev

    def visit(path, relative):
        info = path.lstat()
        require(info.st_dev == device, "Source crosses a filesystem boundary")
        require(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode),
                "Source contains a symlink or unsupported special file")
        entries[relative] = {"path": relative,
                             "type": "directory" if path.is_dir() else "file",
                             "stat": signature(info)}
        if stat.S_ISDIR(info.st_mode):
            for child in sorted(path.iterdir()):
                name = child.name if relative == "." else relative + "/" + child.name
                visit(child, name)

    for root in roots_for(dataset):
        require((source / root).is_dir(), "A required source directory is absent")
        visit(source / root, root)
    return entries


def atomic_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write("\n")
    os.replace(temporary, path)


def inventory(source, dataset, destination):
    require(not destination.exists(), "Source inventory already exists")
    before = scan(source, dataset)
    records = []
    total = 0
    for name, entry in sorted(before.items()):
        record = dict(entry)
        if entry["type"] == "file":
            fd = os.open(source / name, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as stream:
                require(signature(os.fstat(stream.fileno())) == entry["stat"],
                        "Source changed before hashing")
                record["sha256"] = digest(stream)
                require(signature(os.fstat(stream.fileno())) == entry["stat"],
                        "Source changed during hashing")
            record["size"] = entry["stat"][3]
            total += record["size"]
        records.append(record)
    require(scan(source, dataset) == before, "Source changed during inventory")
    temporary = destination.with_name(destination.name + ".tmp")
    with open(temporary, "w", encoding="utf-8") as stream:
        stream.write(json.dumps({"format": FORMAT, "dataset": dataset}) + "\n")
        for record in records:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    os.replace(temporary, destination)
    print(json.dumps({"source_files": sum(r["type"] == "file" for r in records),
                      "source_bytes": total, "result": "source hashed"}), flush=True)


def canonical(name):
    if name.startswith("./"):
        name = name[2:]
    name = name.rstrip("/")
    if name in ("", "."):
        return "."
    require(not name.startswith("/") and
            all(p not in ("", ".", "..") for p in name.split("/")),
            "Unsafe archive or inventory path")
    return str(PurePosixPath(name))


def load_inventory(path, dataset):
    require(path.is_file() and not path.is_symlink(), "Missing safe source inventory")
    with open(path, encoding="utf-8") as stream:
        require(json.loads(next(stream)) == {"format": FORMAT, "dataset": dataset},
                "Wrong source inventory format or dataset")
        entries = {}
        for line in stream:
            entry = json.loads(line)
            name = entry["path"]
            require(canonical(name) == name and name not in entries,
                    "Duplicate or unsafe inventory path")
            require(entry["type"] in ("file", "directory") and
                    len(entry["stat"]) == 6, "Invalid inventory metadata")
            if entry["type"] == "file":
                require(type(entry["size"]) is int and entry["size"] >= 0 and
                        re.fullmatch("[0-9a-f]{64}", entry["sha256"]),
                        "Invalid inventory file digest or size")
            entries[name] = entry
    require(all(root in entries and entries[root]["type"] == "directory"
                for root in roots_for(dataset)), "Missing inventory roots")
    return entries


def check_source(source, dataset, entries):
    expected = {name: {k: entry[k] for k in ("path", "type", "stat")}
                for name, entry in entries.items()}
    require(scan(source, dataset) == expected,
            "Source changed between hashing and archive verification; retry staging")


def parts_for(generation):
    checksums = generation / "SHA256SUMS"
    require(checksums.is_file() and not checksums.is_symlink(), "Missing safe part checksums")
    names = []
    for index, line in enumerate(checksums.read_text().splitlines()):
        match = re.fullmatch(r"[0-9a-f]{64}  (archive\.tar\.part-[0-9]{5})", line)
        require(match and match[1] == f"archive.tar.part-{index:05d}",
                "Archive parts must be unique, contiguous and ordered from zero")
        names.append(match[1])
    require(names and names == sorted(p.name for p in generation.glob("archive.tar.part-*")),
            "Missing or unexpected archive parts")
    paths = [generation / name for name in names]
    require(all(p.is_file() and not p.is_symlink() and p.stat().st_size > 0 for p in paths),
            "Unsafe or empty archive part")
    return paths


class Parts(io.RawIOBase):
    """Seekable virtual tar; no joined archive or extracted copy is written."""

    def __init__(self, paths):
        self.files = []
        self.edges = [0]
        self.position = 0
        try:
            for path in paths:
                self.files.append(open(path, "rb"))
                self.edges.append(self.edges[-1] + path.stat().st_size)
        except BaseException:
            self.close()
            raise

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        position = offset + (self.position if whence == 1 else self.edges[-1] if whence == 2 else 0)
        require(0 <= position <= self.edges[-1], "Archive seek exceeds available parts")
        self.position = position
        return position

    def read(self, size=-1):
        require(size >= 0, "Unbounded archive read refused")
        result = []
        while size and self.position < self.edges[-1]:
            index = bisect.bisect_right(self.edges, self.position) - 1
            stream = self.files[index]
            stream.seek(self.position - self.edges[index])
            data = stream.read(min(size, self.edges[index + 1] - self.position))
            require(data, "Unexpected end of archive part")
            result.append(data)
            self.position += len(data)
            size -= len(data)
        return b"".join(result)

    def close(self):
        for stream in self.files:
            stream.close()
        super().close()


def receipt_fields(generation, dataset, entries):
    return {"format": FORMAT, "dataset": dataset,
            "inventory_sha256": file_digest(generation / INVENTORY),
            "parts_manifest_sha256": file_digest(generation / "SHA256SUMS"),
            "files": sum(e["type"] == "file" for e in entries.values()),
            "bytes": sum(e.get("size", 0) for e in entries.values())}


def verify(generation, dataset, source=None):
    entries = load_inventory(generation / INVENTORY, dataset)
    paths = parts_for(generation)
    initial_binding = receipt_fields(generation, dataset, entries)
    before = [signature(p.stat()) for p in paths]
    seen = set()
    verified = {}
    with Parts(paths) as stream:
        with tarfile.open(fileobj=stream, mode="r:") as archive:
            for member in archive:
                name = canonical(member.name)
                require(name not in seen, "Repeated archive path")
                require(name in entries, "Archive contains an unexpected path")
                seen.add(name)
                expected = entries[name]
                if member.isdir():
                    require(expected["type"] == "directory", "Archive entry type mismatch")
                else:
                    require(expected["type"] == "file", "Archive entry type mismatch")
                    if member.isreg():
                        require(member.size == expected["size"], "Archive file size mismatch")
                        with archive.extractfile(member) as payload:
                            actual = digest(payload)
                    elif member.islnk():
                        target = canonical(member.linkname)
                        require(target in verified, "Unsafe or unresolved archive hardlink")
                        actual, size = verified[target]
                        require(size == expected["size"], "Archive hardlink size mismatch")
                    else:
                        raise InvalidBackup("Archive contains a symlink or special file")
                    require(actual == expected["sha256"], "Archive file SHA-256 mismatch")
                    verified[name] = (actual, expected["size"])
            # tarfile stops at the first end marker. Reject hidden concatenated
            # archives, nonzero trailing data, or missing POSIX end blocks.
            end = archive.offset
        require(stream.edges[-1] % 512 == 0 and stream.edges[-1] - end >= 1024,
                "Truncated archive end markers")
        stream.seek(end)
        while tail := stream.read(BLOCK):
            require(not any(tail), "Unexpected content after archive end")
    require(seen == set(entries), "Archive is missing source paths")
    require([signature(p.stat()) for p in paths] == before,
            "Archive parts changed during content verification")
    if source is not None:
        check_source(source, dataset, entries)
    receipt = receipt_fields(generation, dataset, entries)
    require(receipt == initial_binding, "Inventory or part checksum manifest changed during verification")
    receipt["verified_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    atomic_json(generation / RECEIPT, receipt)
    print(json.dumps({"result": "every source file matches archive", **receipt}), flush=True)


def check(generation, dataset):
    entries = load_inventory(generation / INVENTORY, dataset)
    parts_for(generation)
    path = generation / RECEIPT
    require(path.is_file() and not path.is_symlink(), "Missing source verification receipt")
    receipt = json.loads(path.read_text())
    require(all(receipt.get(k) == v for k, v in receipt_fields(generation, dataset, entries).items()),
            "Source verification receipt no longer matches inventory and archive checksums")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "verify", "check"))
    parser.add_argument("--dataset", choices=("photos", "immich"), required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--generation", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "inventory":
            require(args.source is not None, "Inventory requires a source")
            inventory(args.source, args.dataset, args.generation / INVENTORY)
        elif args.command == "verify":
            verify(args.generation, args.dataset, args.source)
        else:
            check(args.generation, args.dataset)
    except (InvalidBackup, OSError, ValueError, KeyError, StopIteration, tarfile.TarError) as exc:
        print(f"Source verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
