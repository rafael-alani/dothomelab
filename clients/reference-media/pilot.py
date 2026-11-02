#!/usr/bin/env python3
"""Create a reproducible, non-private board acceptance clip (disposable transport)."""
import argparse
import hashlib
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
        "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=24",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=24",
        "-c:v", "libx264", "-preset", "fast", "-crf", "24", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-af", "volume=0.05", "-movflags", "+faststart",
        "-metadata", "title=Reference board calibration — 24 seconds",
        str(args.output),
    ], check=True)
    print(hashlib.sha256(args.output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
