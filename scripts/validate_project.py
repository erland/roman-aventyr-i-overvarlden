#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

CHAPTER_RE = re.compile(r"kapitel-(\d{2,})\.md$")
CHAPTER_H1_RE = re.compile(r"^#\s+Kapitel\s+(\d+)\s*[–-]\s*(.+?)\s*$")
EPILOG_H1_RE = re.compile(r"^#\s+Epilog\s*[–-]\s*(.+?)\s*$")
MARKERS = ("TODO", "FIXME", "[PLACEHOLDER]")

REQUIRED_PATHS = (
    "README.md",
    "roman-bibel.md",
    "synopsis.md",
    "kapitelplan.md",
    "projektstatus.md",
    "project-index.md",
    "kapitelnoteringar.md",
    "kapitel",
    "omslag/omslag.png",
    "publishing/metadata.yaml",
    "publishing/epub.css",
    "publishing/fix-epub-after-pandoc.py",
    "publishing/pdf-template.tex",
    "publishing/pdf-filter.lua",
    "scripts/build_book.py",
)

REQUIRED_METADATA_KEYS = (
    "title",
    "subtitle",
    "author",
    "language",
    "cover-image",
)

EXPECTED_TITLE = "Äventyret i Övervärlden"
EXPECTED_AUTHOR = "Erland Lindmark"

def error(errors: list[str], message: str) -> None:
    errors.append(message)
    print(f"ERROR: {message}", file=sys.stderr)

def parse_simple_yaml_scalars(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values

def validate_markdown_links(root: Path, errors: list[str]) -> None:
    link_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for md in sorted(root.rglob("*.md")):
        if ".git" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        for target in link_re.findall(text):
            target = target.strip().strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            candidate = (md.parent / target).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                continue
            if not candidate.exists():
                error(errors, f"Trasig intern Markdown-länk i {md.relative_to(root)}: {target}")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors: list[str] = []

    if not root.is_dir():
        error(errors, f"Projektkatalogen finns inte: {root}")
        return 1

    for rel in REQUIRED_PATHS:
        if not (root / rel).exists():
            error(errors, f"Obligatorisk projektsökväg saknas: {rel}")

    chapter_dir = root / "kapitel"
    canonical: dict[int, Path] = {}
    if chapter_dir.is_dir():
        for path in sorted(chapter_dir.iterdir()):
            if not path.is_file():
                continue
            match = CHAPTER_RE.fullmatch(path.name)
            if match:
                canonical[int(match.group(1))] = path

    numbers = sorted(canonical)
    if not numbers:
        error(errors, "Inga kapitel hittades.")
    else:
        expected = list(range(1, numbers[-1] + 1))
        missing = sorted(set(expected) - set(numbers))
        if missing:
            error(errors, "Kapitel saknas: " + ", ".join(map(str, missing)))

    for number, path in sorted(canonical.items()):
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            error(errors, f"{path.relative_to(root)} är tom.")
            continue
        first_line = text.strip().splitlines()[0].strip()
        match = CHAPTER_H1_RE.fullmatch(first_line)
        if not match:
            error(errors, f"{path.relative_to(root)} har fel H1-format.")
        elif int(match.group(1)) != number:
            error(errors, f"{path.relative_to(root)} har fel kapitelnummer i H1.")
        for marker in MARKERS:
            if marker in text:
                error(errors, f"{path.relative_to(root)} innehåller arbetsmarkören {marker}.")
        if re.search(r"Kapitelnotering|Kort kapitelnotering|##\s+Efter kapitel", text, re.I):
            error(errors, f"{path.relative_to(root)} innehåller kapitelnoteringar som ska ligga i kapitelnoteringar.md.")

    epilog = chapter_dir / "epilog.md"
    if epilog.exists():
        text = epilog.read_text(encoding="utf-8")
        first_line = text.strip().splitlines()[0].strip() if text.strip() else ""
        if not EPILOG_H1_RE.fullmatch(first_line):
            error(errors, "kapitel/epilog.md har fel H1-format.")

    metadata_path = root / "publishing" / "metadata.yaml"
    if metadata_path.exists():
        metadata = parse_simple_yaml_scalars(metadata_path)
        for key in REQUIRED_METADATA_KEYS:
            if not metadata.get(key):
                error(errors, f"publishing/metadata.yaml saknar värde för '{key}'.")
        if metadata.get("title") != EXPECTED_TITLE:
            error(errors, "Metadatafältet title matchar inte projektets fastställda titel.")
        if metadata.get("author") != EXPECTED_AUTHOR:
            error(errors, "Metadatafältet author matchar inte projektets fastställda författare.")
        cover = metadata.get("cover-image", "")
        if cover and not (root / "publishing" / cover).resolve().exists():
            error(errors, f"Metadatafältet cover-image pekar på en fil som saknas: {cover}")

    validate_markdown_links(root, errors)

    if errors:
        print(f"\nValidation failed: {len(errors)} error(s).", file=sys.stderr)
        return 1

    print(
        f"OK: projektvalidering godkänd. {len(numbers)} kapitel"
        + (" + epilog." if epilog.exists() else ".")
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
