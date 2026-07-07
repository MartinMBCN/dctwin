# Sprint 2 evaluation plan

Evaluation has three layers. A valid JSON document is necessary but not sufficient.

## 1. Contract checks — deterministic

- All three JSON Schemas are themselves valid Draft 2020-12 schemas.
- The normalized source and candidate Twin conform to their schemas.
- The private enrollment artifact conforms to its schema and is absent from model input.
- IDs are unique within their entity type.
- Source, block, role, evidence and tag references resolve.
- Twin tag-catalog version matches the loaded catalog.
- Every evidence item has at least one capability and one narrative theme.
- Every inference cites at least one existing evidence item.
- A structurally invalid model candidate is rejected and may receive up to two validator-driven repair passes; every repaired candidate passes through the full gate.

## 2. Source fidelity — reviewed against the CV

- Role count and chronology are recognizably correct.
- Facts are directly stated rather than inferred.
- Evidence text preserves the action, context and outcome of the source claim.
- Quotes and block locators genuinely support their claims.
- No employer, metric, technology or qualification is invented.
- Ambiguities are represented as gaps rather than silently resolved.
- Extracted email is preserved only as an unverified enrollment candidate and requires verification before account use.

## 3. Semantic usefulness — human review

- Capability tags are useful retrieval concepts, not restatements of evidence.
- Narrative themes recur across more than one item where claimed.
- Career stage and professional identity are supported, calibrated and negotiable.
- Alternatives are plausible rather than token disclaimers.
- Reflection is materially different from reconstructing the CV.
- At least one pattern is useful and not immediately obvious from a linear reading.

## Initial evaluation fixture

Committed automated tests use a fictional CV and Twin. The project owner's real CV is a private local evaluation fixture and must not be committed. Its first run will establish a reviewed baseline after the Foundry model deployment becomes available.

## Initial pass criteria

- 100% deterministic contract checks pass.
- No unsupported fact or fabricated evidence in the reviewed sample.
- At least 90% of material CV bullets represented by one or more evidence items.
- All inference confidence scores have rationales and cited support.
- Reviewer recognizes the output as the same person and identifies at least one cross-role pattern.
