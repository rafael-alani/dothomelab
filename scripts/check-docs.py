#!/usr/bin/env python3
"""Check this repo's Markdown entry pages, local links/anchors, and history index.

Stdlib only. No network, command-example execution, or live-system access.
Supports inline Markdown links, reference definitions, ATX headings, and HTML
anchor IDs. It is a navigation check, not a full CommonMark or prose validator.
"""

from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md", "AGENTS.md", "CONTRIBUTING.md", "USER_DOC.md",
    "docs/README.md", "docs/status.md", "docs/architecture.md",
    "docs/development.md", "docs/operations.md", "docs/decisions/README.md",
    "docs/reference/service-policies.md", "docs/evidence/README.md",
)
INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\((<[^>\n]+>|[^\s)]+)(?:\s+\"[^\"\n]*\")?\)")
REFERENCE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)", re.MULTILINE)


def prose(text):
    """Hide fenced code without changing line numbers."""
    lines = []
    fence = None
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence):
                fence = None
            lines.append("")
        elif match:
            fence = match[1]
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines)


def anchors(text):
    found = set(re.findall(r'<a\s+(?:id|name)=["\']([^"\']+)', text))
    for line in prose(text).splitlines():
        heading = re.match(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not heading:
            continue
        value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading[1])
        value = re.sub(r"<[^>]+>", "", value).lower()
        base = re.sub(r"[^\w\- ]", "", value).replace(" ", "-")
        slug = base
        suffix = 0
        while slug in found:
            suffix += 1
            slug = f"{base}-{suffix}"
        found.add(slug)
    return found


def documents():
    paths = set(ROOT.glob("*.md"))
    for directory in ("docs", "hosts", "clients", "backup"):
        paths.update((ROOT / directory).rglob("*.md"))
    return sorted(paths)


def check():
    errors = []
    links = 0
    local_targets = {}
    anchor_cache = {}
    paths = documents()
    for required in REQUIRED:
        if not (ROOT / required).is_file():
            errors.append(f"Missing required entry page: {required}")
    for source in paths:
        content = prose(source.read_text(encoding="utf-8"))
        # Inline code may contain illustrative Markdown rather than real links.
        content = re.sub(r"(`+)(.+?)\1", lambda m: " " * len(m[0]), content)
        targets = set()
        for match in list(INLINE_LINK.finditer(content)) + list(REFERENCE.finditer(content)):
            url = match[1].strip("<>")
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc:
                continue
            links += 1
            line = content.count("\n", 0, match.start()) + 1
            location = f"{source.relative_to(ROOT)}:{line}"
            target = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source
            try:
                target.relative_to(ROOT)
            except ValueError:
                errors.append(f"{location}: local link escapes the repository: {url}")
                continue
            targets.add(target)
            if not target.exists():
                errors.append(f"{location}: missing target: {url}")
                continue
            anchor_target = target / "README.md" if target.is_dir() else target
            if parsed.fragment and anchor_target.suffix.lower() == ".md" and anchor_target.is_file():
                if anchor_target not in anchor_cache:
                    anchor_cache[anchor_target] = anchors(anchor_target.read_text(encoding="utf-8"))
                if unquote(parsed.fragment) not in anchor_cache[anchor_target]:
                    errors.append(f"{location}: missing heading anchor: {url}")
        local_targets[source] = targets

    # Every dated report and the original migration/snapshot must stay browsable.
    history = {p.resolve() for p in (ROOT / "docs").glob("*.md")
               if re.search(r"\d{4}-\d{2}-\d{2}", p.name)
               or p.name in {"current-state.md", "compose-project-migration.md"}}
    history.update(p.resolve() for p in (ROOT / "docs/evidence").glob("*.md")
                   if p.name != "README.md")
    indexed = local_targets.get(ROOT / "docs/evidence/README.md", set())
    for missing in sorted(history - indexed):
        errors.append(f"docs/evidence/README.md: unindexed report: {missing.relative_to(ROOT)}")

    if errors:
        print("Documentation checks failed:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    print(f"Documentation checks passed: {len(paths)} Markdown files, "
          f"{links} local links, {len(history)} indexed historical/evidence reports.")
    print("Not checked: external URLs, command execution, UI behavior, or prose accuracy.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
