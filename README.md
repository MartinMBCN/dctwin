# Digital Career Twin

The Digital Career Twin (DCT) is a canonical, evidence-based representation of a person's professional identity. Documents and conversations update the Twin; Career Mirrors, CVs and other views are generated projections.

This repository is currently implementing Sprint 2: adapt a CV into a schema-valid candidate Twin and emit the first Career Mirror as JSON.

## Current vertical slice

```text
CV source
  → Source Adapter registry
      → PDF CV strategy
      → DOCX CV strategy
  → separated outputs
      → minimized normalized source document
      → private unverified enrollment candidates
  → Source Adapter Agent / model provider
  → candidate Digital Career Twin
  → deterministic acceptance validation
  → JSON Career Mirror
```

PDF and DOCX are formats, not source types. Both strategies produce the same source contract. Future LinkedIn, portfolio, interview and correction sources can add strategies without changing downstream orchestration.

## Repository map

- `schemas/` — strict JSON Schema contracts for normalized sources, enrollment candidates, Twins and tag catalogs.
- `catalogs/` — controlled capability and narrative-theme tags.
- `src/dctwin/adapters/` — source-format strategies and registry.
- `src/dctwin/agent.py` — Source Adapter Agent orchestration boundary.
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

## Privacy

CVs and generated personal artifacts belong under the ignored `private/` directory or outside the repository. The PDF and DOCX strategies remove email addresses, international-format phone numbers and common street-address forms before model invocation.

Email addresses are emitted separately as unverified account-enrollment candidates. They must be stored by the account system, verified before use, and linked to the Twin through an opaque owner ID. They are not model input or canonical career evidence. This separation does not make career history anonymous; deployment geography and user consent still matter.

## Azure status

The local contracts, adapter boundary and deterministic provider are usable without Azure quota. The Foundry provider will be added after the EU Data Zone model deployment is available. The provider boundary keeps model and deployment selection configurable.
