# Äventyret i Övervärlden

Detta är projektarkivet för romanen **Äventyret i Övervärlden: Hemligheten under berget** av **Erland Lindmark**.

## Rekommenderat arbetsflöde

1. Planera romankärnan: huvudperson, mål, hinder, insats och förändring.
2. Skriv ett kort kapitel i taget i chatten.
3. Justera kapitlet tills det är godkänt.
4. Spara kapitlet i `kapitel/kapitel-XX.md`.
5. Uppdatera projektstatus, kapitelplan, arbetslogg, tidslinje och kontinuitetsanteckningar.
6. Fortsätt med nästa kapitel.

## Projektets riktning

- Genre: Äventyr och mysterium
- Målgrupp: Lågstadiet, 7–9 år
- Ton: Spännande, varm och humoristisk
- Kapitel: 12 korta kapitel
- Rekommenderad längd per kapitel: cirka 700–1200 ord
- Perspektiv: Tredje person nära Leo
- Omslagsbild: Planerad

## GitHub Actions och publicering

Repositoryts `.github/`-katalog ligger i projektroten, på samma nivå som denna `README.md`.

- `Validate`: automatisk kontroll vid PR/push till `main`.
- `Build Preview`: manuell EPUB/PDF-byggning som ett gemensamt Actions-artifact.
- `Release`: bygg och publicering av separata EPUB/PDF-assets på `v*`-taggar.
- Lokal validering: `python3 scripts/validate_project.py .`
- Lokalt bygge: `python3 scripts/build_book.py --output-dir dist`
- Pandoc-version: `3.1.11.1`.

Se `publishing/build-notes.md` för layout- och byggdetaljer.
