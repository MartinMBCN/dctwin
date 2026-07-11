**Backlog item: Mirror interaction model**

Problem:
Sprint 5 improved the Career Mirror UX and Overview Brief, but deferred direct user negotiation of Mirror items. The rest of the Mirror needs the same quality-contract rigor before interaction capabilities are added.

Goal:
Turn the Mirror into a negotiation surface where users can inspect, challenge, correct, confirm and refine the Digital Career Twin.

Candidate capabilities:
- Explain a Mirror item by showing supporting evidence and reasoning.
- Challenge an interpretation and mark it as disputed.
- Correct an interpretation by adding clarifying evidence.
- Confirm an interpretation as accepted by the user.
- Add evidence from a specific Mirror item.
- Calibrate tags by accepting or rejecting capability/theme assignments.
- Move unresolved questions into a dedicated Interview feature.

Principle:
User actions should modify the Twin or add evidence to it. They should not merely edit display text.

**Backlog item: Source removal and provenance subtraction**

Problem:
The Source materials page should eventually let users remove a CV, pasted CV or manually added source. This is not a simple delete operation because evidence may have originated in one source and later been corroborated by another.

Goal:
Allow users to remove source material while preserving any career facts that remain supported by other sources.

Principle:
Removing a source removes that source's contribution to provenance, not necessarily the canonical evidence item. Evidence should be removed only when it has no remaining source support.

Expected behavior:
- Show a confirmation before removing a source.
- Subtract the removed source from each evidence item's provenance.
- Preserve evidence that is still supported by at least one remaining source.
- Delete evidence that was supported only by the removed source.
- Recompute inferences, recurring themes, strengths and Overview Brief from the remaining evidence.
- Persist the rebuilt Twin immediately when the user is signed in.
- Log or summarize what changed: source removed, evidence removed, evidence preserved, inferences updated.

Important edge case:
If CV A first creates an evidence item and CV B later corroborates the same fact, deleting CV A must not delete the evidence item. The evidence should survive with CV B as its remaining provenance.

Candidate reverse wizard:
- Removing source material
- Checking which evidence depends on this source
- Updating the evidence base
- Reconstructing your digital twin
- Rendering your digital twin for presentation

Acceptance test sketch:
1. Upload CV A.
2. Upload CV B containing overlapping achievements.
3. Confirm duplicate achievements merge into single evidence items with provenance from both sources.
4. Remove CV A.
5. Confirm overlapping evidence remains, now supported only by CV B.
6. Confirm evidence unique to CV A disappears.
7. Confirm the Overview Brief and other Mirror sections are rebuilt from the surviving evidence.

**Backlog item: Tag learning and calibration**

Problem:
The fast deterministic mapper assigns useful but shallow tags. Manual keyword expansion helps individual cases but does not scale.

Goal:
Improve tag assignment quality over time without turning the tagger into a pile of hard-coded examples.

Likely direction:
- Capture user corrections to tags.
- Store accepted/rejected tag assignments as training/evaluation examples.
- Add tag assignment evaluation fixtures.
- Let the model propose tags from the controlled catalog.
- Keep deterministic validation against the catalog.
- Periodically refine tag rules or prompts from observed corrections.

**Backlog item: Temporal Evidence Weighting**

Observation

Professional evidence does not lose validity over time, but its relevance varies depending on context.

Principle

The Twin should preserve historical evidence without modification.

Reasoning and projections may weight evidence differently based on factors such as:

Age
Recurrence
Magnitude
Relationship to current objectives
Reference model
Historical significance

Examples

Executive CV emphasizes recent leadership evidence.
Career history emphasizes foundational early experience.
Objective alignment may increase the importance of older but highly relevant evidence.

Architectural implication

Weighting belongs in the reasoning/projection layer, not the canonical Twin.

**Backlog item: evidence quality assistance**

Not automatic rewriting. 
For example:
Detect weak entries: vague, no outcome, no action, no context, no metric.
Surface a gentle prompt: “This is saved, but could be strengthened. What changed as a result?”
Offer optional improvement, not silent mutation.
Keep original text as source quote.
Store any improved wording as a derived/refined evidence text with provenance back to the original.

**Backlog item: Credential/session protection must be hardened before production.** 
Specifically:
real email delivery instead of displayed local codes
secure, HttpOnly, SameSite cookies instead of localStorage session token
HTTPS-only transport
CSRF/session-rotation considerations
audit logging for account access and destructive actions

**Backlog item: External Perspectives and elicited evidence**

Status

Backlog (Post-MVP)

Overview

Extend the Digital Career Twin to incorporate attributed observations from other people who have worked with the user, including third-party artefacts and evidence elicited specifically for the Twin.

The objective is not to collect endorsements or testimonials, but to enrich the Twin with additional evidence from independent professional perspectives.

Source categories

Sources divide into three broad categories:

Self-authored

The user describing themselves.

Examples:
CV
Interview
Career story
LinkedIn profile
Manually entered achievements

Third-party artefacts

Documents produced by other people or institutions before being submitted to the Twin.

Examples:
Performance review
Promotion recommendation
Reference letter
Award citation

Elicited evidence

Evidence generated specifically for the Twin through a designed collection process.

Examples:
Confidential manager interview
Peer interview
Direct-report interview
Client interview

Motivation

The current Twin is constructed almost entirely from self-authored evidence.

Third-party artefacts and elicited evidence introduce additional classes of evidence that may:

reveal characteristics the user has overlooked;
corroborate recurring professional patterns;
expose differences between self-perception and external perception;
strengthen inferences through genuinely independent observations.
Architectural Fit

External perspectives are simply additional evidence sources, but their source category and observer perspective should be preserved as provenance metadata.

Professional Life
        ↓

Sources
├── CV
├── Career story
├── LinkedIn
├── Manual evidence
├── Performance review
├── Promotion recommendation
├── Reference letter
├── Manager interview
├── Peer interview
├── Direct report interview
└── Client interview

        ↓
Evidence
        ↓
Inferences
        ↓
Reflection

The existing architecture remains unchanged: source category and perspective enrich provenance and inference weighting, but do not create a competing model.

New Concept: Perspective

Unlike CVs, external interviews introduce observer perspective.

Potential perspectives include:

Self
Manager
Peer
Direct Report
Client
Mentor

Perspective becomes metadata attached to evidence rather than a new reasoning layer.

Evidence Principle

External observations are evidence, not facts.

For example:

Former manager: "Martin consistently brought clarity to ambiguous situations."

This is stored as attributed evidence.

The Twin may later infer:

Multiple independent observers describe a recurring ability to bring structure to ambiguity.

Reasoning

Unlike repeated CVs, independently collected perspectives can legitimately strengthen higher-order inferences because they represent independent observations rather than repeated self-description.

This complements the DCT principle:

Repeated sources strengthen provenance.
Independent evidence strengthens inference.

External interviews introduce genuinely independent evidence.

Reflection

The Mirror may eventually distinguish between:

Self-described characteristics
Externally observed characteristics
Areas of convergence
Areas of divergence

These differences may become valuable reflection points.

Non-Goals

This capability is not intended to become:

LinkedIn recommendations
Performance reviews
360° feedback
Reputation scoring
Social validation

The objective remains increasing professional self-awareness through evidence.

Open Questions
Invitation workflow
Identity verification
Consent and privacy
Handling conflicting perspectives
Weighting different observer types
Visibility controls
Persistence and revocation of contributed evidence
