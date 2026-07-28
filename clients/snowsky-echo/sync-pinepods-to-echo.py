#!/usr/bin/env python3
"""Compile PinePods downloads into a safe, delta-synced ECHO podcast tree."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import uuid
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_SOURCE = Path("/Volumes/Media/podcasts/pinepods")
DEFAULT_DESTINATION = PurePosixPath("Podcasts/PinePods")
MANIFEST_NAME = ".pinepods-echo.json"
AUDIO_EXTENSIONS = {
    ".aac",
    ".flac",
    ".m4a",
    ".mp3",
    ".mp4",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
}
EPISODE_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<title>.+)_2_(?P<id>\d+)$"
)
FAT_FORBIDDEN = re.compile(r'[\x00-\x1f<>:"/\\|?*]')
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


@dataclass(frozen=True)
class Episode:
    source: Path
    source_relative: str
    source_size: int
    source_mtime_ns: int
    podcast: str
    title: str
    published: str
    episode_id: str
    output_relative: str
    audio_codec: str | None
    estimated_output_size: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compile downloaded PinePods episodes from the read-only Media "
            "share into a tagged, audio-only MP3 tree on a mounted ECHO card."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"PinePods download root (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--device",
        type=Path,
        required=True,
        help="mounted ECHO card root, for example /Volumes/ECHO",
    )
    parser.add_argument(
        "--destination",
        default=str(DEFAULT_DESTINATION),
        help=f"device-relative managed podcast tree (default: {DEFAULT_DESTINATION})",
    )
    parser.add_argument(
        "--min-free-percent",
        type=float,
        default=10.0,
        help="minimum card space to leave free after new writes (default: 10)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help=(
            "remove manifest-owned card episodes whose PinePods source file "
            "no longer exists; omitted by default"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show planned work without writing the card",
    )
    return parser.parse_args()


def require_tool(name: str) -> str:
    resolved = shutil.which(name)
    if not resolved:
        raise ValueError(
            f"{name} is required; install FFmpeg before running this sync"
        )
    return resolved


def parse_destination(raw: str) -> PurePosixPath:
    destination = PurePosixPath(raw)
    if (
        destination.is_absolute()
        or not destination.parts
        or any(part in ("", ".", "..") for part in destination.parts)
    ):
        raise ValueError("--destination must be a non-empty device-relative path")
    return destination


def truncate_utf8(value: str, max_bytes: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    encoded = encoded[:max_bytes]
    while encoded:
        try:
            return encoded.decode("utf-8").rstrip()
        except UnicodeDecodeError:
            encoded = encoded[:-1]
    return "_"


def safe_component(value: str, max_bytes: int) -> str:
    cleaned = unicodedata.normalize("NFC", value)
    cleaned = FAT_FORBIDDEN.sub("_", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "_"
    if cleaned.split(".", 1)[0].upper() in WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"
    return truncate_utf8(cleaned, max_bytes).strip(" .") or "_"


def parse_episode(source_root: Path, source: Path) -> tuple[str, str, str, str]:
    relative = source.relative_to(source_root)
    podcast = safe_component(relative.parts[0], 120)
    match = EPISODE_PATTERN.match(source.stem)
    if match:
        published = match.group("date")
        title = safe_component(match.group("title"), 220)
        episode_id = match.group("id")
    else:
        published = dt.datetime.fromtimestamp(
            source.stat().st_mtime,
            tz=dt.timezone.utc,
        ).date().isoformat()
        title = safe_component(source.stem, 220)
        episode_id = hashlib.sha256(
            relative.as_posix().encode("utf-8")
        ).hexdigest()[:12]
    return podcast, title, published, episode_id


def output_filename(
    published: str,
    title: str,
    episode_id: str,
    max_bytes: int = 180,
) -> str:
    prefix = f"{published} - "
    suffix = f" [{episode_id}].mp3"
    title_budget = max_bytes - len(prefix.encode("utf-8")) - len(
        suffix.encode("utf-8")
    )
    bounded_title = truncate_utf8(title, max(16, title_budget)).strip(" .")
    return f"{prefix}{bounded_title or '_'}{suffix}"


def run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise ValueError(f"command failed: {message}")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("media probe did not return valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("media probe returned an unexpected result")
    return value


def probe_source(ffprobe: str, source: Path) -> tuple[str | None, float]:
    value = run_json(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,codec_type:format=duration",
            "-of",
            "json",
            str(source),
        ]
    )
    streams = value.get("streams")
    if not isinstance(streams, list):
        streams = []
    audio = next(
        (
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "audio"
        ),
        None,
    )
    if audio is None:
        raise ValueError(f"{source} has no audio stream")
    codec = audio.get("codec_name")
    if codec is not None and not isinstance(codec, str):
        codec = None
    raw_format = value.get("format")
    if not isinstance(raw_format, dict):
        raw_format = {}
    raw_duration = raw_format.get("duration")
    try:
        duration = max(0.0, float(raw_duration))
    except (TypeError, ValueError):
        duration = 0.0
    return codec, duration


def load_manifest(path: Path, destination: PurePosixPath) -> dict[str, Any]:
    if not path.exists():
        return {
            "schemaVersion": SCHEMA_VERSION,
            "destination": str(destination),
            "episodes": {},
        }
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"refusing non-regular manifest {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read valid manifest {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError(f"{path} has an unsupported schema version")
    if value.get("destination") != str(destination):
        raise ValueError(
            f"{path} manages {value.get('destination')!r}, not {str(destination)!r}"
        )
    if not isinstance(value.get("episodes"), dict):
        raise ValueError(f"{path} has no valid episodes object")
    return value


def safe_owned_output(
    device: Path,
    destination: Path,
    relative: str,
) -> Path:
    pure = PurePosixPath(relative)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        raise ValueError(f"unsafe manifest output path {relative!r}")
    candidate = device.joinpath(*pure.parts)
    try:
        candidate.relative_to(destination)
    except ValueError as exc:
        raise ValueError(
            f"manifest output is outside {destination}: {relative!r}"
        ) from exc
    reject_symlink_chain(device, candidate)
    return candidate


def reject_symlink_chain(root: Path, target: Path) -> None:
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path is outside device root {root}: {target}") from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"refusing symlink in managed path: {current}")


def source_audio_files(source_root: Path) -> list[Path]:
    files: list[Path] = []

    def raise_walk_error(error: OSError) -> None:
        raise error

    for directory, directory_names, file_names in os.walk(
        source_root,
        topdown=True,
        onerror=raise_walk_error,
        followlinks=False,
    ):
        directory_path = Path(directory)
        directory_names[:] = [
            name
            for name in directory_names
            if not (directory_path / name).is_symlink()
        ]
        for name in file_names:
            source = directory_path / name
            if source.is_symlink():
                continue
            if source.suffix.lower() in AUDIO_EXTENSIONS:
                files.append(source)
    return sorted(files)


def discover_episodes(
    source_root: Path,
    source_files: list[Path],
    device: Path,
    destination_relative: PurePosixPath,
    manifest: dict[str, Any],
    ffprobe: str,
) -> tuple[list[Episode], int]:
    episodes: list[Episode] = []
    unchanged = 0
    records = manifest["episodes"]
    destination = device.joinpath(*destination_relative.parts)
    for source in source_files:
        resolved_source = source.resolve()
        try:
            resolved_source.relative_to(source_root)
        except ValueError as exc:
            raise ValueError(f"source escapes {source_root}: {source}") from exc
        stat_result = source.stat()
        source_relative = source.relative_to(source_root).as_posix()
        podcast, title, published, episode_id = parse_episode(source_root, source)
        output = destination / podcast / output_filename(
            published,
            title,
            episode_id,
        )
        output_relative = output.relative_to(device).as_posix()
        existing = records.get(source_relative)
        if (
            isinstance(existing, dict)
            and existing.get("sourceSize") == stat_result.st_size
            and existing.get("sourceMtimeNs") == stat_result.st_mtime_ns
            and existing.get("output") == output_relative
            and output.is_file()
            and not output.is_symlink()
        ):
            unchanged += 1
            continue
        codec, duration = probe_source(ffprobe, source)
        estimated = (
            stat_result.st_size
            if codec == "mp3"
            else max(64 * 1024, int(duration * 128_000 / 8 * 1.05))
        )
        episodes.append(
            Episode(
                source=source,
                source_relative=source_relative,
                source_size=stat_result.st_size,
                source_mtime_ns=stat_result.st_mtime_ns,
                podcast=podcast,
                title=title,
                published=published,
                episode_id=episode_id,
                output_relative=output_relative,
                audio_codec=codec,
                estimated_output_size=estimated,
            )
        )
    return episodes, unchanged


def verify_compiled(ffprobe: str, output: Path) -> None:
    value = run_json(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,codec_type",
            "-of",
            "json",
            str(output),
        ]
    )
    streams = value.get("streams")
    if not isinstance(streams, list):
        streams = []
    audio_codecs = [
        stream.get("codec_name")
        for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == "audio"
    ]
    video_count = sum(
        1
        for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == "video"
    )
    if audio_codecs != ["mp3"] or video_count:
        raise ValueError(
            f"compiled output is not one audio-only MP3 stream: {output}"
        )
    if output.stat().st_size <= 0:
        raise ValueError(f"compiled output is empty: {output}")


def compile_episode(
    episode: Episode,
    device: Path,
    destination: Path,
    ffmpeg: str,
    ffprobe: str,
) -> Path:
    output = safe_owned_output(
        device,
        destination,
        episode.output_relative,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    reject_symlink_chain(device, output.parent)
    if output.is_symlink():
        raise ValueError(f"refusing symlink output {output}")
    temp = output.parent / f".{output.name}.{uuid.uuid4().hex}.tmp.mp3"
    command = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(episode.source),
        "-map",
        "0:a:0",
        "-vn",
        "-map_metadata",
        "-1",
    ]
    if episode.audio_codec == "mp3":
        command.extend(["-c:a", "copy"])
    else:
        command.extend(
            [
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                "-ar",
                "44100",
                "-ac",
                "2",
            ]
        )
    command.extend(
        [
            "-metadata",
            f"title={episode.title}",
            "-metadata",
            f"artist={episode.podcast}",
            "-metadata",
            f"album={episode.podcast}",
            "-metadata",
            "album_artist=* PODCASTS *",
            "-metadata",
            f"date={episode.published}",
            "-metadata",
            "genre=Podcast",
            "-id3v2_version",
            "3",
            "-write_id3v1",
            "1",
            str(temp),
        ]
    )
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip()
            raise ValueError(f"FFmpeg failed for {episode.source}: {message}")
        verify_compiled(ffprobe, temp)
        with temp.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temp, output)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
    return output


def remove_empty_parents(path: Path, stop: Path) -> None:
    parent = path.parent
    while parent != stop:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def atomic_write_manifest(path: Path, value: dict[str, Any]) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def main() -> int:
    args = parse_args()
    try:
        if args.min_free_percent < 0 or args.min_free_percent >= 100:
            raise ValueError("--min-free-percent must be at least 0 and below 100")
        ffmpeg = require_tool("ffmpeg")
        ffprobe = require_tool("ffprobe")
        source = args.source.expanduser().resolve()
        device = args.device.expanduser().resolve()
        if not source.is_dir():
            raise ValueError(f"PinePods source is not a directory: {source}")
        if not device.is_dir():
            raise ValueError(f"ECHO device root is not a directory: {device}")
        if (
            source == device
            or source.is_relative_to(device)
            or device.is_relative_to(source)
        ):
            raise ValueError(
                "PinePods source and ECHO device must be separate trees"
            )
        destination_relative = parse_destination(args.destination)
        destination = device.joinpath(*destination_relative.parts)
        if destination.exists() and destination.is_symlink():
            raise ValueError(f"refusing symlink destination {destination}")
        manifest_path = device / MANIFEST_NAME
        manifest = load_manifest(manifest_path, destination_relative)
        records: dict[str, Any] = dict(manifest["episodes"])
        source_files = source_audio_files(source)
        episodes, unchanged = discover_episodes(
            source,
            source_files,
            device,
            destination_relative,
            manifest,
            ffprobe,
        )
        current_sources = {
            path.relative_to(source).as_posix()
            for path in source_files
        }
        stale = sorted(set(records) - current_sources)
        estimate = sum(episode.estimated_output_size for episode in episodes)
        usage = shutil.disk_usage(device)
        minimum_free = int(usage.total * args.min_free_percent / 100)
        if usage.free - estimate < minimum_free:
            raise ValueError(
                "planned writes would violate the card free-space floor: "
                f"free={usage.free} estimate={estimate} minimum={minimum_free}"
            )

        for episode in episodes:
            action = "update" if episode.source_relative in records else "add"
            codec_action = (
                "retag/audio-copy"
                if episode.audio_codec == "mp3"
                else f"transcode {episode.audio_codec or 'unknown'}->mp3"
            )
            print(
                f"{action}: {episode.source_relative} -> "
                f"{episode.output_relative} ({codec_action})"
            )
        if stale:
            stale_action = "prune" if args.prune else "retain"
            for source_relative in stale:
                print(f"{stale_action}: {source_relative}")
        if args.dry_run:
            print(
                "dry-run summary: "
                f"writes={len(episodes)} unchanged={unchanged} "
                f"stale={len(stale)} estimated_bytes={estimate}"
            )
            return 0

        added = 0
        updated = 0
        for episode in episodes:
            previous = records.get(episode.source_relative)
            output = compile_episode(
                episode,
                device,
                destination,
                ffmpeg,
                ffprobe,
            )
            if isinstance(previous, dict):
                updated += 1
                old_relative = previous.get("output")
                if isinstance(old_relative, str) and old_relative != episode.output_relative:
                    old_output = safe_owned_output(
                        device,
                        destination,
                        old_relative,
                    )
                    if old_output.is_file() and not old_output.is_symlink():
                        old_output.unlink()
                        remove_empty_parents(old_output, destination)
            else:
                added += 1
            records[episode.source_relative] = {
                "sourceSize": episode.source_size,
                "sourceMtimeNs": episode.source_mtime_ns,
                "output": output.relative_to(device).as_posix(),
                "outputSize": output.stat().st_size,
                "codec": "mp3",
            }

        pruned = 0
        if args.prune:
            for source_relative in stale:
                previous = records[source_relative]
                output_relative = (
                    previous.get("output") if isinstance(previous, dict) else None
                )
                if isinstance(output_relative, str):
                    output = safe_owned_output(
                        device,
                        destination,
                        output_relative,
                    )
                    if output.is_file() and not output.is_symlink():
                        output.unlink()
                        remove_empty_parents(output, destination)
                records.pop(source_relative, None)
                pruned += 1

        manifest = {
            "schemaVersion": SCHEMA_VERSION,
            "sourceRoot": str(source),
            "destination": str(destination_relative),
            "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
            "policy": {
                "output": "audio-only MP3",
                "nonMp3Bitrate": "128k",
                "albumArtist": "* PODCASTS *",
                "pruneMissingSources": bool(args.prune),
            },
            "episodes": records,
        }
        atomic_write_manifest(manifest_path, manifest)
        print(
            "summary: "
            f"added={added} updated={updated} unchanged={unchanged} "
            f"retained={0 if args.prune else len(stale)} pruned={pruned}"
        )
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
