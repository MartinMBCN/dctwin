High level definition of each agent's capabilities

Source Adapter
──────────────
"I know how to normalize supported source material."

        ↓

Role & Evidence Extractor
──────────────────
"I know how to find professional evidence."

        ↓

Twin Mapper
───────────
"I know how to represent evidence using the DCT schema."

        ↓

Twin Repository
───────────────
"I own the canonical Twin."

Implementation note — Sprint 2

The first implemented orchestration boundary is the Source Adapter Agent.

It does not mean "PDF agent." It accepts a declared source type and delegates file-format reading to a compatible strategy. The first source type is `cv`; its first format strategies are PDF and DOCX.

Source Adapter Agent
────────────────────
"I know how to turn supported professional source material into a validated candidate Twin."

Responsibilities:

1. Select a registered source strategy.
2. Normalize source content into stable blocks and locators.
3. Separate direct identifiers from model input and emit email as a private, unverified enrollment candidate.
4. Apply source-specific semantic instructions.
5. Ask the model provider for a schema-constrained candidate Twin.
6. Reject candidates that fail schema, provenance, tag or referential-integrity validation.

The agent does not create accounts or verify contact details. Enrollment candidates are routed to the account boundary, which requires proof of email possession and user confirmation.

For Sprint 2, evidence extraction and Twin mapping are explicit stages in the agent instructions and acceptance checks, but they are not separate deployed agents. This provides one observable vertical slice before introducing multi-agent coordination. They may be separated when independent evaluation, scaling or ownership justifies the additional orchestration cost.

Implementation note — Sprint 3

Sprint 3 introduces the Reconciliation Agent as a deterministic orchestration boundary.

Reconciliation Agent
────────────────────
"I know how to update an existing Twin without turning every source into a separate Twin."

Responsibilities:

1. Compare incoming roles with existing roles by title, organization and dates.
2. Compare incoming evidence with existing evidence by role context, normalized text similarity and shared metrics.
3. Classify matches as `NEW`, `DUPLICATE` or `POSSIBLE_DUPLICATE`.
4. Apply the corresponding action: `ADD`, `MERGE_PROVENANCE` or append with possible-duplicate context.
5. Refresh the local session Twin and validate the complete result.

The product UI does not use the internal term "evidence" for manual user entry. Users add an achievement; internally that achievement becomes user-entered evidence after classification, tagging, reconciliation and validation.
