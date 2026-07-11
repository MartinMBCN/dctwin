Sprint 5 — Career Mirror UX and Overview Brief

Objective

Improve the Career Mirror as a user-facing reflection surface by making the UI more usable and making the Overview Brief materially better: more structured, more evidence-grounded, more scannable and less repetitive.

Sprint 5 is not the sprint for full user negotiation/editing of the Mirror. That work has been carved out into a future sprint after the same level of rigor has been applied to the other Mirror surfaces.

Accepted Sprint Scope

1. Rearrange the UI to make the Career Mirror more user-oriented.
2. Move mechanical/developer views behind `?debug=true`.
3. Split the Career Mirror into clearer user-facing tabs.
4. Surface Education/Training.
5. Rework the Overview into an evidence-based executive briefing.
6. Establish the Overview Brief quality contract.
7. Add architectural decisions needed to make Overview generation stable:
   - structured brief items;
   - evidence/provenance/inference separation;
   - explicit quality contract;
   - editorial pass.
8. Improve Overview behavior across repeated CV ingestion:
   - less duplicate wording;
   - stronger first-CV brief;
   - less overconfidence from repeated user-authored sources;
   - more stable briefing when subsequent CVs retell the same story.

Out of Scope for Sprint 5

The following user interaction capabilities are intentionally deferred:

* Explain a Mirror item.
* Challenge a Mirror item.
* Correct a Mirror item.
* Confirm a Mirror item.
* Add evidence directly from a specific Mirror item.
* Edit or negotiate tags from the Mirror.
* Turn open questions into an Interview feature.

These capabilities remain important, but they should be introduced only after the non-Overview parts of the Mirror have their own quality contracts and rendering discipline.

Implemented Career Mirror Surface

Default tabs:

1. Overview
2. Strengths
3. Career themes
4. Career timeline
5. Education/Training

Debug-only tabs behind `?debug=true`:

1. Source blocks
2. Reconciliation
3. Timings
4. Twin JSON

The Questions tab is deprecated from the main Mirror surface. Open questions remain internal for now and should re-emerge through a future Interview feature.

Overview Brief

The precise Overview Brief specification is maintained in `docs/sprints/sprint5b.md`.

The Overview Brief should be treated as an objective, evidence-based confidential executive briefing rather than conversational or persona-led prose.

Sprint 5 Acceptance Criteria

1. UI is user-oriented by default and developer/mechanical views are hidden unless debug mode is enabled.
2. Overview is presented as a structured executive briefing with stable section headings.
3. Overview Brief items are evidence-grounded and stored as structured items rather than parsed from model prose.
4. Overview Brief avoids unsupported interpretation and speculative claims.
5. Repeated CVs merge provenance without inflating evidence confidence.
6. Duplicate or non-novel Overview observations are compressed or removed by the editorial pass.
7. Overview sections are capped and ordered so the result remains scannable.
8. User interaction/negotiation capabilities are documented as future work rather than treated as incomplete Sprint 5 work.

Future Sprint — Mirror Interaction Model

Future objective:

Turn the Mirror from a reflective surface into a negotiation surface through which users can inspect, challenge, correct, confirm and refine the Digital Career Twin.

Candidate capabilities:

* Explain: show evidence and reasoning behind a Mirror item.
* Challenge: mark an interpretation as disputed.
* Correct: provide replacement or clarifying evidence.
* Confirm: mark an interpretation as accepted by the user.
* Add evidence: attach new source material to a specific role, evidence item or interpretation.
* Calibrate tags: allow users to accept/reject capability and theme assignments.

Principle:

User actions should modify the Twin or add evidence to it. They should not merely edit display text.
