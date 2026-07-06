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

Technical debt remediation: Identify the reason(s) why the process takes so long, and whether they are unique to the local environment or need to be addressed as structural/architectural improvements.

Sprint 3 acceptance criteria:

User can upload a second CV.
System matches existing roles rather than creating duplicates.
System identifies exact and near-duplicate evidence.
Duplicate evidence gains additional source provenance rather than becoming a new evidence item.
New evidence is added to the correct role.
User can manually add free-form evidence to a selected role.
Manually added evidence is treated like any other evidence source: classified, tagged, and available for inference.
