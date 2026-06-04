"""mdup — export Markdown files to DOCX and/or PDF.

Pure-Python, cross-platform, minimal dependencies. The two features that cannot
be rendered statically in pure Python — mermaid diagrams and LaTeX math — use an
optional renderer if present and fall back gracefully (with a warning) otherwise.

Public API
----------
    from mdup import convert, MarkdownConverter

    convert(["doc.md"], formats=["pdf", "docx"], output="out/")
"""

from .core import MarkdownConverter, convert

__version__ = "0.1.0"
__all__ = ["MarkdownConverter", "convert", "__version__"]
