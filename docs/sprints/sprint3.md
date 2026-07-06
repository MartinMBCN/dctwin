Sprint Goal

The system can ingest additional user-provided evidence, whether from a second CV or free-form entry, and update the existing Twin without duplicating evidence already represented.

Verify whether the Twin is genuinely persistent rather than a one-shot CV transform.

There are two workstreams.

First, multi-source reconciliation:

Second CV
 → extract roles/evidence
 → match roles against existing roles
 → detect duplicate / near-duplicate evidence
 → add only new or materially different evidence
 → update inferences/reflection

Two very similar bullets should resolve to the same evidence item, with the second source added as provenance, not a new evidence item.

Second, manual evidence capture:

Select role
 → add free-form evidence
 → classify evidence type and assign to a role
 → tag capabilities/themes
 → update inferences/reflection

That gives the user a non-document ingestion path while preserving the same architecture.

Architecturally, this introduces a new component:

Role & Evidence Extractor
        ↓
Reconciliation Agent
        ↓
Twin Mapper

The Reconciliation Agent’s job is:

“Given newly extracted roles/evidence and the existing Twin, decide what is new, what is duplicate, what is a refinement, and what requires user confirmation.”

For Sprint 3, three statuses are enough:

new

duplicate

possible_duplicate

Sprint 3 performance requirement

CV ingestion should produce a rendered Career Mirror in under 10 seconds for a normal two-page text-based CV, excluding first-time cold starts. If local execution exceeds this threshold, the system must expose step-level timing so we can distinguish local environment issues from structural bottlenecks.

Add instrumentation before optimization:

upload_received
text_extraction_started
text_extraction_completed
model_call_started
model_call_completed
json_validation_completed
mirror_rendered

Log elapsed time for each step. You need to know whether the latency is coming from PDF extraction, Azure round-trip/model latency, JSON validation, rendering, or local app overhead.

Sprint 3 acceptance criteria:

User can upload a second CV.

System matches existing roles rather than creating duplicates.

System identifies exact and near-duplicate evidence.

Duplicate evidence gains additional source provenance rather than becoming a new evidence item.

New evidence is added to the correct role.

User can manually add free-form evidence to a selected role.

Manually added evidence is treated like any other evidence source: classified, tagged, and available for inference.

Each ingestion step logs duration.

Total ingestion duration is visible in dev mode.

Text-based two-page CV completes under 10 seconds in deployed Azure environment, or bottleneck is identified.

Duplicate-detection/reconciliation does not add more than 3 seconds for a second CV of similar size.
