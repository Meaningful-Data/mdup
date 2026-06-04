"""Orchestration: read Markdown inputs, render once to HTML, write the requested
output formats — either one file per input (default) or a single merged file.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path

from . import assets, backends, render

log = logging.getLogger("mdup")

VALID_FORMATS = ("pdf", "docx")
_EXT = {"pdf": ".pdf", "docx": ".docx"}

# Page break inserted between documents in a merged output.
_PAGE_BREAK = '\n<div class="mdup-page-break"></div>\n'


def _make_work_dir() -> Path:
    """Create a scratch directory for generated/downloaded images.

    Uses the system temp dir by default. If the only mermaid renderer is a snap
    package (a common Linux install method), snap confinement cannot read ``/tmp``
    or hidden dot-directories, so we instead create a non-hidden temp dir directly
    under the user's home, which snap can access. The directory is always removed
    when conversion finishes.
    """
    from . import mermaid

    if mermaid.is_snap_confined():
        try:
            return Path(tempfile.mkdtemp(prefix="mdup-", dir=Path.home()))
        except OSError:
            pass
    return Path(tempfile.mkdtemp(prefix="mdup-"))


def _is_dir_like(path: Path) -> bool:
    """True if *path* should be treated as a directory rather than a target file."""
    if path.exists():
        return path.is_dir()
    s = str(path)
    return s.endswith(("/", os.sep)) or path.suffix == ""


def _write(body: str, out_path: Path, fmt: str, *, title: str,
           pdf_backend: str, work_dir: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "docx":
        backends.to_docx(body, out_path)
    else:
        backends.to_pdf(body, out_path, backend=pdf_backend, title=title,
                        work_dir=work_dir)
    log.info("wrote %s", out_path)
    return out_path


class MarkdownConverter:
    """Convert one or more Markdown files to DOCX and/or PDF."""

    def __init__(self, formats=("pdf",), *, pdf_backend: str = "xhtml2pdf",
                 merge: bool = False, toc: bool = False):
        formats = [f.lower() for f in formats]
        bad = [f for f in formats if f not in VALID_FORMATS]
        if bad:
            raise ValueError(f"Unknown format(s): {bad}. Choose from {VALID_FORMATS}.")
        if not formats:
            raise ValueError("At least one output format is required.")
        if pdf_backend not in ("xhtml2pdf", "weasyprint"):
            raise ValueError(f"Unknown pdf_backend: {pdf_backend!r}.")
        # Preserve order, drop duplicates.
        self.formats = list(dict.fromkeys(formats))
        self.pdf_backend = pdf_backend
        self.merge = merge
        self.toc = toc

    def _render_body(self, md_path: Path, work_dir: Path):
        """Render one file to ``(body, headings)`` with image srcs resolved.

        No TOC is inserted here; insertion happens per-output (per file when writing
        separately, or once consolidated when merging).
        """
        try:
            text = md_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"{md_path}: not valid UTF-8 text — is it really a Markdown file? "
                f"(if a glob like '*' pulled in a binary file, narrow it to '*.md'). "
                f"[{exc}]"
            ) from exc
        body, headings = render.parse(text, work_dir=work_dir)
        body = assets.resolve_images(body, base_dir=md_path.parent, work_dir=work_dir)
        return body, headings

    def convert(self, inputs, output=None) -> list:
        paths = [Path(p) for p in inputs]
        if not paths:
            raise ValueError("No input files provided.")
        missing = [p for p in paths if not p.is_file()]
        if missing:
            raise FileNotFoundError(
                "Input file(s) not found: " + ", ".join(str(p) for p in missing)
            )

        out = Path(output) if output is not None else None
        work_dir = _make_work_dir()
        written: list[Path] = []
        try:
            # Each entry: (path, body_html, headings).
            rendered = [(p, *self._render_body(p, work_dir)) for p in paths]

            if self.merge and len(rendered) > 1:
                written = self._write_merged(rendered, out, work_dir)
            else:
                if self.merge:
                    log.info("merge requested with a single input; writing one file.")
                written = self._write_separate(rendered, out, work_dir)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
        return written

    # ---------------------------------------------------------------- writers

    def _write_merged(self, rendered, out: Path | None, work_dir: Path) -> list:
        # A merged document gets a single consolidated TOC at the top, covering the
        # headings of every input in order (each file's title heads its own block),
        # rather than one TOC per file scattered through the document.
        want_toc = self.toc or any(render.has_toc_marker(b) for _, b, _ in rendered)
        parts, all_headings = [], []
        for i, (_, body, headings) in enumerate(rendered):
            body = render.strip_toc_markers(body)
            if want_toc:
                # Namespace anchors per file so the TOC links unambiguously even when
                # two files share a heading title.
                body, headings = render.prefix_anchors(body, headings, f"f{i}-")
                all_headings.extend(headings)
            parts.append(body)
        merged = _PAGE_BREAK.join(parts)
        if want_toc:
            toc_html = render.build_toc(all_headings)
            if toc_html:
                merged = toc_html + "\n" + merged

        if out is None:
            out_dir, stem = rendered[0][0].parent, "merged"
        elif _is_dir_like(out):
            out_dir, stem = out, "merged"
        else:
            out_dir, stem = out.parent, out.stem
        title = stem
        written = []
        for fmt in self.formats:
            target = out_dir / f"{stem}{_EXT[fmt]}"
            written.append(_write(merged, target, fmt, title=title,
                                  pdf_backend=self.pdf_backend, work_dir=work_dir))
        return written

    def _write_separate(self, rendered, out: Path | None, work_dir: Path) -> list:
        single = len(rendered) == 1 and len(self.formats) == 1
        # Allow naming one exact output file: single input, single format, file path.
        exact = single and out is not None and not _is_dir_like(out)

        written = []
        for md_path, body, headings in rendered:
            body = render.apply_toc(body, headings, self.toc)
            for fmt in self.formats:
                if exact:
                    target = out
                elif out is None:
                    target = md_path.parent / f"{md_path.stem}{_EXT[fmt]}"
                elif _is_dir_like(out):
                    target = out / f"{md_path.stem}{_EXT[fmt]}"
                else:
                    # File-ish path but multiple inputs/formats: use its directory.
                    target = out.parent / f"{md_path.stem}{_EXT[fmt]}"
                written.append(_write(body, target, fmt, title=md_path.stem,
                                      pdf_backend=self.pdf_backend, work_dir=work_dir))
        return written


def convert(inputs, formats=("pdf",), output=None, *, merge: bool = False,
            pdf_backend: str = "xhtml2pdf", toc: bool = False) -> list:
    """Convenience wrapper around :class:`MarkdownConverter`.

    Returns the list of written output paths.
    """
    converter = MarkdownConverter(
        formats, pdf_backend=pdf_backend, merge=merge, toc=toc
    )
    return converter.convert(inputs, output=output)
