Sprint Goal

The system can ingest additional user-provided evidence, whether from a second CV or free-form entry, and update the existing Twin without duplicating evidence already represented, demonstrating that the Twin is a persistent canonical model rather than a one-shot CV transformation.

Details
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

“Given newly extracted roles/evidence and the existing Twin, decide what is new, what is duplicate, what is a refinement, and what requires user confirmation, and determine whether existing inferences require regeneration.”

For Sprint 3, three statuses are enough:

Match classification

NEW
DUPLICATE
POSSIBLE_DUPLICATE

Reconciliation action

ADD
MERGE_PROVENANCE
REQUEST_USER_CONFIRMATION

Additional CV requirement
Manual source ingestion: pasted CV / career text
As a user, I can paste CV-style text into the system so that it is treated as an evidence source and reconciled against my existing Twin.

Therefore, Source can be any of the following, for the first or subsequent CV:
├── PDF
├── DOCX
├── Pasted Text
└── (Future) LinkedIn

Sprint 3 performance requirements
CV ingestion should produce a rendered Career Mirror in under 10 seconds for a normal two-page text-based CV, excluding first-time cold starts. If local execution exceeds this threshold, the system must expose step-level timing so we can distinguish local environment issues from structural bottlenecks.

Add instrumentation before optimization:

upload_received
text_extraction_started
text_extraction_completed
model_call_started
model_call_completed
json_validation_completed
mirror_rendered

Instrumentation

roles_detected
evidence_extracted
evidence_matched
evidence_added
evidence_merged
possible_duplicates

Log elapsed time for each step. You need to know whether the latency is coming from PDF extraction, Azure round-trip/model latency, JSON validation, rendering, or local app overhead.

Sprint 3 acceptance criteria:

User can upload a second CV.

The Twin remains canonical after repeated ingestion.

Existing inferences and the Career Mirror are regenerated following successful reconciliation.

System identifies exact and near-duplicate evidence.

The existing evidence item gains an additional supporting source.

New evidence is added to the correct role.

User can manually add free-form evidence to a selected role.

Manually added evidence is treated like any other evidence source: classified, tagged, and available for inference.

Each ingestion step logs duration.

Total ingestion duration is visible in dev mode.

Text-based two-page CV completes under 10 seconds in deployed Azure environment, or bottleneck is identified.

Repeated ingestion of the same source is idempotent.

Duplicate-detection/reconciliation does not add more than 3 seconds for a second CV of similar size.

Out of Scope
Persistent user accounts (Sprint 4)
Mirror UX redesign and editing experience (Sprint 5)
LinkedIn ingestion
Advanced conflict resolution beyond REQUEST_USER_CONFIRMATION
Performance optimization beyond instrumentation and bottleneck identification

Implementation status — 2026-07-07

Completed locally:

- Local session Twin state stored as ignored development JSON under `.dctwin-local/`.
- Pasted CV text path treated as source type `cv` and media type `text/plain`.
- User-facing manual entry renamed to "Add an achievement"; internally it becomes `user_entered_data`.
- Reconciliation Agent with deterministic role matching, evidence similarity matching, duplicate provenance merge and possible-duplicate append.
- Local UI tabs for file upload, pasted CV text and adding an achievement.
- Dev-facing reconciliation summary and stage timings surfaced in the UI.
- Automated tests for pasted CV adaptation, duplicate reconciliation and adding an achievement.

Pending:

- End-to-end test with a second real CV through Foundry.
- Tune near-duplicate thresholds against multiple real CVs.
- Decide whether possible duplicates should remain appended silently or become a review surface in a later sprint.
