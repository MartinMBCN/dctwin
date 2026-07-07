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

---

## ADR-004
The Source Adapter is source-agnostic; source-specific readers are strategies behind it.

Reason:
The orchestration layer should ask for a normalized source document without knowing whether the input was a CV, LinkedIn profile, interview transcript or future source type. Sprint 2 implements the PDF CV strategy first without making CV concepts part of the adapter contract.

Consequence:
All strategies emit the same block-based source document with stable locators and provenance. More than one strategy may support a source type: PDF and DOCX are both CV strategies. The Source Adapter Agent selects by source type and the registry selects a compatible format strategy.

---

## ADR-005
Model output is untrusted until it passes deterministic validation.

Reason:
Structured output reduces formatting errors but does not establish semantic correctness or referential integrity.

Consequence:
The orchestration boundary validates JSON Schema conformance, tag-catalog references, supporting-evidence references and evidence-tag coverage before accepting a Twin update.

---

## ADR-006
Extraction confidence and inference confidence are different concepts.

Reason:
A directly stated fact can be difficult to read, while an inference can be clearly expressed but weakly supported. Combining these uncertainties obscures what the system knows.

Consequence:
Facts and role fields may carry `extraction_confidence`; inferences and tag relationships carry `confidence` plus rationale.

---

## ADR-007
Direct identifiers are separated from career reasoning before model invocation.

Reason:
Phone numbers, email addresses and street addresses do not contribute to career reasoning and unnecessarily expand the model's personal-data surface. Email addresses can, however, provide a useful contact and enrollment mechanism.

Consequence:
Source strategies replace those values with typed placeholders before producing model input. Redaction metadata records categories and locations, never the original values. An extracted email is emitted separately as an unverified enrollment candidate; it is never included in the model document or accepted as an account identifier without verification. Phone numbers and street addresses are discarded unless a future, explicitly consented account use is defined. Career history remains personal data and still requires an appropriate processing location and user consent.

---

## ADR-008
Account identity is separate from the Digital Career Twin.

Reason:
An email address supports authentication, contact and enrollment, but it is not evidence of professional capability. Keeping identity and career content separate reduces coupling and allows account identifiers to change without rewriting the Twin.

Consequence:
The account system owns verified contact identifiers and links to the Twin through an opaque owner ID. The Source Adapter may propose an email as an enrollment candidate, but account creation requires possession verification and user confirmation. The candidate artifact is private, is not sent to the model, and is not part of the canonical DCT schema.
