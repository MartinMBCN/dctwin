# Digital Career Twin schema

Roles organize experience. Evidence supports reasoning. Inferences emerge from evidence, not from chronology.

## Status

`schemas/digital_career_twin.schema.json` is the canonical machine-readable contract. It uses JSON Schema Draft 2020-12. The schema version is independent of the application version and begins at `0.2.0`.

The previous file was a useful example document but not a JSON Schema: it described one possible value rather than the rules that all valid Twins must follow. Version 0.2.0 turns those ideas into a strict, testable contract and adds the Sprint 2 acceptance criteria.

## Main concepts

### Sources

A Twin records the sources that support it, but not the source document's full contents. Source content is normalized separately according to `schemas/source_document.schema.json`.

Source type and file format are intentionally separate. `cv` is a source type; PDF, DOCX and pasted text are currently registered or supported format paths. Adding another CV format must not change the normalized contract or downstream agent.

User-entered achievements are represented as source type `user_entered_data`. The UI should describe this as adding an achievement; the internal schema treats the achievement as evidence only after it has been classified, tagged, reconciled and validated.

Account enrollment is a separate concern. `schemas/enrollment_candidates.schema.json` describes private, unverified contact candidates extracted alongside the model document. It is not part of the DCT schema and must never be included in an agent prompt. After verification, the account system owns the contact identifier and links to the Twin by an opaque owner ID.

### Facts

Facts are directly stated claims. Each fact has at least one source reference. `extraction_confidence` describes confidence that the source was read correctly; it does not turn the fact into an inference.

### Roles and evidence

Roles provide chronological and organizational context. Evidence is the atomic unit of professional proof. Evidence normally references a role, but may instead use another explicit context for education or cross-career material.

Every evidence item must have at least one entry in `tag_assignments.capabilities` and one in `tag_assignments.narrative_themes`. The assignment stores its own confidence and rationale because confidence belongs to the relationship, not to the tag itself.

### Inferences

Inferences include career stage, professional identity and conclusions drawn across evidence. Every inference requires supporting evidence, confidence, rationale, alternative interpretations and a negotiable status.

### Gaps

Missing and low-confidence fields are explicit gap objects. A gap explains what is uncertain, why it matters and what question or evidence could resolve it.

### Reflection

Reflection is the first JSON Career Mirror. It is a generated projection included in the Sprint 2 document for convenience; it is not canonical evidence and can later move into a separate representation contract.

## Controlled tags

`catalogs/tag_catalog.json` is the initial controlled vocabulary. `schemas/tag_catalog.schema.json` validates its structure. Runtime validation additionally checks that every tag reference exists and that the relationship's declared type matches the catalog entry.

The seed catalog is intentionally small. New tags should be added when existing concepts cannot represent evidence without distortion—not merely because the model generated a new phrase.

## Migration from the original example

| Original field | Version 0.2.0 |
| --- | --- |
| `person.name`, `location`, `work_authorization` | Typed `person.facts` with provenance |
| `roles[].evidence_ids` | `evidence_items[].role_id` |
| `evidence_items[].source` | Structured `source_refs` |
| `core_capabilities[].value` | Catalog tag assignments and capability inferences |
| `low_confidence_fields` | Structured `gaps` |
| Implicit schema shape | Strict JSON Schema with required fields and IDs |

## Validation beyond JSON Schema

JSON Schema validates document shape. The application additionally enforces:

1. Every `source_id`, `role_id` and supporting evidence ID resolves.
2. Every tag ID exists in the declared catalog version.
3. Tag types agree with the catalog.
4. Each evidence item has both a capability and a narrative theme.
5. Inference support is not empty or dangling.
