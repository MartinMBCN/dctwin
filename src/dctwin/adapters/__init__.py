"""Source-specific strategies behind the Source Adapter boundary."""

from dctwin.adapters.docx_cv import DocxCvAdapter
from dctwin.adapters.pdf_cv import PdfCvAdapter
from dctwin.adapters.registry import AdapterRegistry

__all__ = ["AdapterRegistry", "DocxCvAdapter", "PdfCvAdapter"]
