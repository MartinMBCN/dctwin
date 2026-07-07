# Digital Career Twin

The Digital Career Twin (DCT) is a canonical, evidence-based representation of a person's professional identity. Documents and conversations update the Twin; Career Mirrors, CVs and other views are generated projections.

This repository is currently implementing Sprint 3: update a local session Twin from additional CV sources and user-entered achievements without duplicating evidence already represented.

## Current vertical slice

```text
CV source or user-entered achievement
  → Source Adapter registry
      → PDF CV strategy
      → DOCX CV strategy
      → pasted-text CV path
  → separated outputs
      → minimized normalized source document
      → private unverified enrollment candidates
  → Source Adapter Agent / model provider
  → transient CVExtractionResult
  → deterministic DCT builder
      → stable IDs
      → canonical source references
      → full Digital Career Twin schema
  → Reconciliation Agent
      → add new evidence
      → merge duplicate provenance
      → append possible duplicates with context
  → deterministic acceptance validation
  → updated JSON Career Mirror
```

PDF and DOCX are formats, not source types. Both strategies produce the same source contract. Future LinkedIn, portfolio, interview and correction sources can add strategies without changing downstream orchestration.

## Repository map

- `schemas/` — strict JSON Schema contracts for normalized sources, enrollment candidates, Twins and tag catalogs.
- `catalogs/` — controlled capability and narrative-theme tags.
- `src/dctwin/adapters/` — source-format strategies and registry.
- `src/dctwin/agent.py` — Source Adapter Agent orchestration boundary.
- `src/dctwin/reconciliation.py` — deterministic Sprint 3 reconciliation boundary.
- `src/dctwin/twin_builder.py` — deterministic mapping from compact extraction into the DCT contract.
- `src/dctwin/validation.py` — schema and referential-integrity acceptance checks.
- `prompts/` — source-agnostic agent and CV-specific instructions.
- `tests/` — synthetic fixtures; personal CVs are never committed.
- `docs/` and `decisions.md` — product concepts and architectural reasoning.

## Local setup

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Normalize a CV without invoking a model:

```bash
dctwin adapt-cv path/to/cv.pdf --output private/source.private.json
dctwin adapt-cv path/to/cv.docx \
  --output private/source.private.json \
  --enrollment-output private/enrollment.private.json
```

Validate an existing candidate Twin:

```bash
dctwin validate path/to/twin.json
```

Run the local preview UI:

```bash
dctwin-web
```

Then open `http://127.0.0.1:8765`. The preview binds only to the local machine, processes uploads in a temporary file that is deleted after each request, and does not call Foundry.

When the Foundry environment variables are set, the preview can create and update a local session Twin:

- upload a PDF or DOCX CV;
- paste CV-style text as the first or subsequent CV source;
- add an achievement to a selected role;
- inspect reconciliation decisions and stage timings.

The session Twin is stored in ignored local development state under `.dctwin-local/`. This is not account persistence.

By default, the local Foundry path uses staged extraction: the model emits a transient `CVExtractionResult` containing compact roles, achievements, source snippets and interpretation, then deterministic code maps that into the full DCT schema. Set `DCTWIN_MODEL_PATH=full` to compare against the older one-shot full-DCT generation path. Source-derived candidates are cached by content hash under `.dctwin-local/cache/`.

## Privacy

CVs and generated personal artifacts belong under the ignored `private/` directory or outside the repository. The PDF and DOCX strategies remove email addresses, international-format phone numbers and common street-address forms before model invocation.

Email addresses are emitted separately as unverified account-enrollment candidates. They must be stored by the account system, verified before use, and linked to the Twin through an opaque owner ID. They are not model input or canonical career evidence. This separation does not make career history anonymous; deployment geography and user consent still matter.

## Azure status

The local contracts, adapter boundary, reconciliation boundary, staged DCT builder and deterministic tests are usable without Azure quota. The Foundry provider is available when a configured deployment is present. The provider boundary keeps model and deployment selection configurable.
