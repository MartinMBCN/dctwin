from __future__ import annotations

import argparse
from pathlib import Path

from dctwin.adapters import AdapterRegistry, DocxCvAdapter, PdfCvAdapter
from dctwin.io import load_json, write_json
from dctwin.validation import (
    validate_enrollment_document,
    validate_source_document,
    validate_tag_catalog,
    validate_twin,
)


def _root() -> Path:
    candidates = [Path.cwd(), *Path(__file__).resolve().parents]
    for candidate in candidates:
        if (candidate / "schemas/digital_career_twin.schema.json").is_file():
            return candidate
    raise RuntimeError(
        "Cannot locate DCT contracts; run from the repository root or set up the "
        "application with explicit contract paths"
    )


def _schemas() -> tuple[dict, dict, dict, dict, dict]:
    root = _root()
    source_schema = load_json(root / "schemas/source_document.schema.json")
    enrollment_schema = load_json(root / "schemas/enrollment_candidates.schema.json")
    twin_schema = load_json(root / "schemas/digital_career_twin.schema.json")
    tag_schema = load_json(root / "schemas/tag_catalog.schema.json")
    catalog = load_json(root / "catalogs/tag_catalog.json")
    return source_schema, enrollment_schema, twin_schema, tag_schema, catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dctwin")
    subcommands = parser.add_subparsers(dest="command", required=True)

    adapt = subcommands.add_parser("adapt-cv", help="Normalize and minimize a PDF or DOCX CV")
    adapt.add_argument("document", type=Path)
    adapt.add_argument("--output", "-o", type=Path)
    adapt.add_argument(
        "--enrollment-output",
        type=Path,
        help="Write private, unverified enrollment candidates separately",
    )

    validate = subcommands.add_parser("validate", help="Validate a Digital Career Twin JSON file")
    validate.add_argument("twin", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    source_schema, enrollment_schema, twin_schema, tag_schema, catalog = _schemas()
    validate_tag_catalog(catalog, tag_schema)

    if args.command == "adapt-cv":
        registry = AdapterRegistry()
        registry.register(PdfCvAdapter())
        registry.register(DocxCvAdapter())
        adapted = registry.adapt("cv", args.document)
        validate_source_document(adapted.model_document, source_schema)
        validate_enrollment_document(adapted.enrollment_document, enrollment_schema)
        write_json(adapted.model_document, args.output)
        if args.enrollment_output is not None:
            write_json(adapted.enrollment_document, args.enrollment_output)
    elif args.command == "validate":
        twin = load_json(args.twin)
        validate_twin(twin, twin_schema, catalog)
        print(f"Valid Digital Career Twin: {args.twin}")
