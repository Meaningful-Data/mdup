# mdup

Export Markdown files to **DOCX** and/or **PDF** — pure-Python, cross-platform,
minimal dependencies.

A single Markdown → HTML pass feeds both writers. The two features that can't be
rendered statically in pure Python (mermaid diagrams and LaTeX math) use an
**optional** renderer if one is available and fall back gracefully otherwise — so
the base install stays small and works everywhere.

## Install

```bash
pip install mdup
```

The core install is pure-Python (no native libraries):
`markdown-it-py`, `mdit-py-plugins`, `htmldocx`/`python-docx`, `xhtml2pdf`.

Optional extras:

```bash
pip install "mdup[math]"        # render LaTeX math (adds matplotlib)
pip install "mdup[weasyprint]"  # higher-fidelity PDF (needs native Pango/Cairo)
pip install "mdup[all]"         # both of the above
```

For **mermaid diagrams**, install the mermaid CLI separately (optional):
`npm install -g @mermaid-js/mermaid-cli` (provides `mmdc`).

## Usage

```bash
mdup notes.md                          # -> notes.pdf
mdup notes.md -f docx,pdf -o out/      # both formats into ./out/
mdup a.md b.md -f docx                 # -> a.docx and b.docx (one per input)
mdup a.md b.md --merge -f pdf -o book.pdf   # one merged PDF
mdup report.md --toc -f pdf            # insert a table of contents
mdup report.md -f pdf --pdf-backend weasyprint
```

| Option | Meaning |
| ------ | ------- |
| `-f, --format` | `pdf`, `docx`, or both (comma-separated). Default `pdf`. |
| `-o, --output` | Output directory, or a file path. Default: alongside each input. |
| `--merge` | With multiple inputs, produce one merged file per format. |
| `--toc` | Insert a table of contents (or honour a `[TOC]` marker). |
| `--pdf-backend` | `xhtml2pdf` (default) or `weasyprint`. |
| `-v, --verbose` | Verbose logging. |

Also runnable as `python -m mdup ...`.

### Library API

```python
from mdup import convert

convert(["report.md"], formats=["pdf", "docx"], output="out/")
convert(["a.md", "b.md"], formats=["pdf"], output="book.pdf", merge=True)
```

## Supported Markdown

CommonMark plus: GFM tables, task lists, strikethrough, footnotes, auto table of
contents, fenced code, embedded images (relative paths resolved against the source
file; remote URLs downloaded), LaTeX math, and mermaid diagrams.

## Notes & limitations

- **PDF backend.** `xhtml2pdf` (default) is pure-Python and runs anywhere, with a
  pragmatic subset of CSS. `weasyprint` produces nicer output but needs native
  Pango/Cairo libraries, so it is an opt-in extra.
- **Math** uses matplotlib's *mathtext* engine (a large LaTeX-math subset, no system
  LaTeX required) rendered to images. Full LaTeX environments (e.g. `align`) are not
  supported. Without matplotlib, math is shown as literal source with a warning.
- **Mermaid** requires the `mmdc` CLI. Without it, diagrams are shown as styled code
  blocks with a warning. A snap-installed `mmdc` is supported (mdup places its
  scratch files where snap confinement can read them).

## License

MIT
