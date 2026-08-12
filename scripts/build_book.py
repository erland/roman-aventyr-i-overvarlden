#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

PANDOC_VERSION = "3.1.11.1"

def simple_metadata(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        result[key.strip()] = value
    return result

def slugify(value: str) -> str:
    table = str.maketrans({"å":"a","ä":"a","ö":"o","Å":"A","Ä":"A","Ö":"O"})
    value = value.translate(table).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value

def pandoc_version() -> str:
    proc = subprocess.run(["pandoc", "--version"], text=True, capture_output=True, check=True)
    return proc.stdout.splitlines()[0].replace("pandoc ", "").strip()

def normalize_source(path: Path, output: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\ufeff", "")
    lines = text.splitlines()
    first = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if first is None:
        raise RuntimeError(f"{path} saknar H1.")
    heading = lines[first][2:].strip()
    m = re.match(r"Kapitel\s+0?(\d+)\s*[–-]\s*(.+)", heading)
    if m:
        label = f"{int(m.group(1))}. {m.group(2).strip()}"
    else:
        e = re.match(r"Epilog\s*[–-]\s*(.+)", heading)
        if not e:
            raise RuntimeError(f"Okänd H1 i {path}: {heading}")
        label = f"Epilog. {e.group(1).strip()}"
    lines[first] = "# " + label
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return label

def validate_epub(epub: Path, expected_labels: list[str], title: str) -> None:
    ns = {
        "opf": "http://www.idpf.org/2007/opf",
        "xhtml": "http://www.w3.org/1999/xhtml",
        "epub": "http://www.idpf.org/2007/ops",
    }
    with zipfile.ZipFile(epub) as archive:
        names = archive.namelist()
        if not names or names[0] != "mimetype":
            raise RuntimeError("EPUB-fel: mimetype ligger inte först.")
        info = archive.getinfo("mimetype")
        if info.compress_type != zipfile.ZIP_STORED:
            raise RuntimeError("EPUB-fel: mimetype är komprimerad.")

        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = container.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
        opf_name = rootfile.attrib["full-path"]
        opf = ET.fromstring(archive.read(opf_name))
        manifest = opf.find("opf:manifest", ns)
        spine = opf.find("opf:spine", ns)
        nav_item = next(
            item for item in manifest.findall("opf:item", ns)
            if "nav" in item.attrib.get("properties", "").split()
        )
        nav_name = str(Path(opf_name).parent / nav_item.attrib["href"])
        nav = ET.fromstring(archive.read(nav_name))
        toc = nav.find(".//xhtml:nav[@epub:type='toc']", ns)
        labels = ["".join(a.itertext()).strip() for a in toc.findall(".//xhtml:a", ns)]
        for label in expected_labels:
            if label not in labels:
                raise RuntimeError(f"EPUB-fel: TOC saknar '{label}'.")
        if title in labels:
            raise RuntimeError("EPUB-fel: titelsidan finns felaktigt med i TOC.")

        nav_id = nav_item.attrib["id"]
        nav_refs = [ref for ref in spine.findall("opf:itemref", ns) if ref.attrib.get("idref") == nav_id]
        if nav_refs and any(ref.attrib.get("linear") != "no" for ref in nav_refs):
            raise RuntimeError("EPUB-fel: nav.xhtml är linjär i spine.")

        split = 0
        for name in names:
            if not name.endswith(".xhtml"):
                continue
            data = archive.read(name).decode("utf-8", errors="replace")
            if 'class="chapter-number"' in data and 'class="chapter-title"' in data:
                split += 1
        if split != len(expected_labels):
            raise RuntimeError(
                f"EPUB-fel: {split} delade rubriker, väntat {len(expected_labels)}."
            )

def find_font_dir() -> Path | None:
    required = [
        "texgyrepagella-regular.otf",
        "texgyrepagella-bold.otf",
        "texgyrepagella-italic.otf",
        "texgyrepagella-bolditalic.otf",
    ]
    for candidate in [
        Path("/usr/share/texmf/fonts/opentype/public/tex-gyre"),
        Path("/usr/share/fonts/opentype/texgyre"),
        Path("/usr/share/fonts/opentype/tex-gyre"),
    ]:
        if all((candidate / name).is_file() for name in required):
            return candidate
    for base in [Path("/usr/share/texmf"), Path("/usr/share/fonts")]:
        if not base.exists():
            continue
        for regular in base.rglob(required[0]):
            candidate = regular.parent
            if all((candidate / name).is_file() for name in required):
                return candidate
    return None

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--name", default="")
    parser.add_argument("--formats", default="epub,pdf")
    parser.add_argument("--allow-pandoc-version-mismatch", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_dir = Path(args.output_dir).resolve()

    validation = subprocess.run([sys.executable, "scripts/validate_project.py", "."], cwd=root)
    if validation.returncode != 0:
        return validation.returncode

    version = pandoc_version()
    if version != PANDOC_VERSION and not args.allow_pandoc_version_mismatch:
        print(
            f"ERROR: Pandoc {PANDOC_VERSION} krävs; hittade {version}.",
            file=sys.stderr,
        )
        return 2

    metadata = simple_metadata(root / "publishing/metadata.yaml")
    title = metadata["title"]
    subtitle = metadata.get("subtitle", "")
    author = metadata["author"]
    base_name = args.name or slugify(title)
    formats = [x.strip().lower() for x in args.formats.split(",") if x.strip()]
    invalid = sorted(set(formats) - {"epub", "pdf"})
    if invalid or not formats:
        print("ERROR: --formats måste innehålla epub och/eller pdf.", file=sys.stderr)
        return 2

    chapters = sorted(
        (root / "kapitel").glob("kapitel-[0-9][0-9].md"),
        key=lambda p: int(re.search(r"kapitel-(\d+)", p.name).group(1)),
    )
    epilog = root / "kapitel" / "epilog.md"
    sources = chapters + ([epilog] if epilog.exists() else [])
    if not chapters:
        print("ERROR: Inga kapitelfiler hittades.", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="roman-build-") as tmp:
        temp = Path(tmp)
        normalized: list[Path] = []
        labels: list[str] = []
        for i, source in enumerate(sources, 1):
            target = temp / f"{i:02d}-{source.name}"
            labels.append(normalize_source(source, target))
            normalized.append(target)

        if "epub" in formats:
            output = output_dir / f"{base_name}.epub"
            title_page = temp / "00-title.md"
            title_page.write_text(
                '<section class="title-page">\n'
                f'<p class="book-title">{title}</p>\n'
                + (f'<p class="subtitle">{subtitle}</p>\n' if subtitle else '')
                + f'<p class="author">{author}</p>\n'
                '</section>\n',
                encoding="utf-8",
            )
            command = [
                "pandoc",
                str(title_page),
                *[str(p) for p in normalized],
                "--from=markdown+raw_html",
                "--to=epub3",
                "--output", str(output),
                "--metadata-file", str(root / "publishing/metadata.yaml"),
                "--css", str(root / "publishing/epub.css"),
                "--epub-cover-image", str(root / "omslag/omslag.png"),
                "--epub-title-page=false",
                "--toc",
                "--toc-depth=1",
                "--split-level=1",
            ]
            subprocess.run(command, cwd=root, check=True)
            subprocess.run(
                [
                    sys.executable,
                    str(root / "publishing/fix-epub-after-pandoc.py"),
                    str(output),
                    title,
                ],
                cwd=root,
                check=True,
            )
            validate_epub(output, labels, title)
            print(f"OK: EPUB skapad och verifierad: {output}")

        if "pdf" in formats:
            pdf = output_dir / f"{base_name}.pdf"
            if shutil.which("xelatex") is None:
                print("ERROR: xelatex krävs för PDF-bygget.", file=sys.stderr)
                return 2
            font_dir = find_font_dir()
            font_args = ["--variable", f"pdf-font-dir={font_dir.as_posix()}"] if font_dir else []
            command = [
                "pandoc",
                *[str(p) for p in normalized],
                "--from=markdown",
                "--to=pdf",
                "--pdf-engine=xelatex",
                "--output", str(pdf),
                "--metadata-file", str(root / "publishing/metadata.yaml"),
                "--template", str(root / "publishing/pdf-template.tex"),
                "--lua-filter", str(root / "publishing/pdf-filter.lua"),
                *font_args,
                "--top-level-division=chapter",
            ]
            subprocess.run(command, cwd=root, check=True)
            if not pdf.exists() or pdf.stat().st_size < 10000:
                print("ERROR: PDF-bygget gav ingen giltig PDF-fil.", file=sys.stderr)
                return 2
            print(f"OK: PDF skapad: {pdf}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
