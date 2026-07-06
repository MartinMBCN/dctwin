# Architecture Decisions

## ADR-001
The Digital Career Twin is the canonical system of record.

Reason:
All representations (Career Mirror, CVs, Company Fit, etc.) are projections of the Twin.

---

## ADR-002
Evidence is grouped by role.

Reason:
Users experience their careers chronologically through roles. Inferences reason across evidence rather than chronology.

---

## ADR-003
Conversation is one input modality.

Reason:
The Twin evolves through evidence regardless of whether that evidence comes from conversation, documents or structured UI.
