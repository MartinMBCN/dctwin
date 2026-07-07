"""Source-specific strategies behind the Source Adapter boundary."""

from dctwin.adapters.docx_cv import DocxCvAdapter
from dctwin.adapters.pdf_cv import PdfCvAdapter
from dctwin.adapters.registry import AdapterRegistry
from dctwin.adapters.text_cv import TextCvAdapter, adapt_cv_text

__all__ = [
    "AdapterRegistry",
    "DocxCvAdapter",
    "PdfCvAdapter",
    "TextCvAdapter",
    "adapt_cv_text",
]
