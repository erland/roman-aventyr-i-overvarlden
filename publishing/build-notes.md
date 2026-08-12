# Build notes

Markdown-filerna i `kapitel/` är kanonisk manusKälla. `kapitelnoteringar.md` exporteras inte.

## GitHub Actions-publicering

- Validate körs på pull request och push till `main` när relevanta projektfiler ändras.
- Build Preview startas manuellt via `workflow_dispatch`.
- Preview bygger EPUB + PDF och laddar upp dem som ett gemensamt artifact: `aventyret-i-overvarlden-preview`.
- Release triggas av taggar som matchar `v*` och publicerar EPUB/PDF som separata GitHub Release-assets.
- Pandoc är låst till version `3.1.11.1`.
- PDF byggs med XeLaTeX och TeX Gyre Pagella.
- Kapitel 1–12 exporteras i numerisk ordning och `kapitel/epilog.md` läggs sist.
- EPUB har omslag, separat titelsida, ingen synlig TOC-sida och navigeringsindex med `1. Rubrik`.
- Kapitelnummer och kapitelrubrik renderas på två centrerade rader.
- PDF använder bokformat 140 × 216 mm, helsidesomslag, separat titelsida och klickbar innehållsförteckning.
