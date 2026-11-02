#!/usr/bin/env python3
"""Install private comparison boards without overwriting any existing notes."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vault", required=True, type=Path)
    p.add_argument("--video", required=True, type=Path)
    p.add_argument("--transport-copy", type=Path, help="Verified temporary copy for frame extraction")
    a = p.parse_args()
    assert a.video.is_file()
    base = a.vault / "References" / "Board acceptance"
    base.mkdir(parents=True, exist_ok=True)
    if (base / "Canvas comparison.canvas").exists():
        raise SystemExit("Existing comparison board; refusing to overwrite")
    source = a.transport_copy or a.video
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    assert a.video.stem == digest, "Pilot must use an immutable content address"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
                    "-ss", "9", "-i", str(source), "-frames:v", "1", "-q:v", "3",
                    str(base / "Frame at 9 seconds.jpg")], check=True, timeout=30)
    notes = {}
    for name, start, end in [("Full video", 0, 24), ("Excerpt A", 3, 7), ("Excerpt B", 12, 18)]:
        notes[name] = (f"# {name}\n\n"
                       f"![{start}–{end} seconds|440]({a.video.as_uri()}#t={start},{end}&no_autoplay&load=eager)\n\n"
                       f"Source interval: **{start}–{end} seconds**.\n\nMy annotation: keep this when sources refresh.\n")
    notes["Captured frame"] = ("# Frame at 9 seconds\n\n![[References/Board acceptance/Frame at 9 seconds.jpg]]\n\n"
                               f"[Original at 9 seconds]({a.video.as_uri()}#t=9)\n\nAsset: `{digest}`\n")
    notes["Itinerary"] = ("# Delft — visual itinerary example\n\n"
                          "[Open Delft on OpenStreetMap](https://www.openstreetmap.org/search?query=Delft%2C%20Netherlands)\n\n"
                          "Place provenance: manually chosen demonstration; no location inferred from the calibration video.\n\n"
                          "Morning: explore the centre. Add your own notes and connect this card to a reference.\n")
    for name, content in notes.items():
        (base / (name + ".md")).write_text(content)
    nodes = []
    elements = []
    for i, name in enumerate(notes):
        node = {"id": f"reference{i}", "type": "file", "x": (i % 3) * 500, "y": (i // 3) * 420,
                "width": 460, "height": 380, "file": f"References/Board acceptance/{name}.md"}
        nodes.append(node)
        elements.append({"id": node["id"], "type": "embeddable", "x": node["x"], "y": node["y"],
                         "width": node["width"], "height": node["height"], "angle": 0,
                         "strokeColor": "#1e1e1e", "backgroundColor": "transparent", "fillStyle": "solid",
                         "strokeWidth": 1, "strokeStyle": "solid", "roughness": 0, "opacity": 100,
                         "groupIds": [], "frameId": None, "roundness": None, "seed": i + 1,
                         "version": 1, "versionNonce": i + 1, "isDeleted": False, "boundElements": None,
                         "updated": 0, "link": f'[[{node["file"]}]]', "locked": False})
    (base / "Canvas comparison.canvas").write_text(json.dumps({"nodes": nodes, "edges": []}, indent=2))
    drawing = {"type": "excalidraw", "version": 2, "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
               "elements": elements, "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None}, "files": {}}
    (base / "Excalidraw comparison.excalidraw.md").write_text(
        "---\nexcalidraw-plugin: parsed\n---\n\n# Excalidraw Data\n## Text Elements\n\n%%\n## Drawing\n```json\n"
        + json.dumps(drawing, indent=2) + "\n```\n%%\n")
    (base / "Second project.canvas").write_text(json.dumps({"nodes": [dict(nodes[2], x=0, y=0)], "edges": []}, indent=2))
    print("Created comparison boards, five notes and one still image:", base)


if __name__ == "__main__":
    main()
