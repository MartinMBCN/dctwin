High level definition of each agent's capabilities

Source Adapter
──────────────
"I know how to read CVs."

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
