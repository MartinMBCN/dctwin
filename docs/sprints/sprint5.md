Sprint 5 — Career Mirror
Objective

Transform the Career Mirror from a generated report into an interactive reflection surface through which the user inspects, negotiates and refines their Digital Career Twin.

The Mirror should become the primary interface to the Twin rather than merely a representation of it.

Principles
The entire Career Mirror is the Reflection.
Every section represents the Twin's current understanding.
Every section is negotiable - note, this does not mean that in every case, the user can change it directly.
Every interpretation can be explained by evidence.
The user edits their Twin through the Mirror.

Sprint Goals
1. Rearrange the UI to make the Career Mirror more user-oriented.
2. Adjust the summary/reflection section so it speaks conversationally rather than as a detached report.
3. Add user capabilities that let the user negotiate and refine the Twin through the Mirror.

Initial Scope
1. Write timings to a log.
2. All current tabs can be deprecated - they are mechanical features that the user doesn't need direct access to.
3. The current career mirror should be split into multiple tabs:
    1. Overview (reflection and current hypotheses)
    2. Career themes
    3. Questions
    4. Career timeline
    5. Education/Training (we are not currently displaying this even though it’s in the DCT)
  
Overview Summary (currently titled 'Reflection')

Rewrite as a conversation with the user rather than a detached analysis.

Note: the more precise Overview Brief specification in `docs/sprints/sprint5b.md` supersedes the exploratory Mirror Voice Contract below. The Overview Brief should be treated as an objective, evidence-based executive briefing rather than conversational or persona-led prose.

Mirror Voice Contract

The overview should be evidence-led, not persona-led. It should sound like a professional reflection generated from the user’s evidence, not like a ghost in the machine interpreting their life.

Prefer:

- “Your CV presents you as…”
- “The evidence presents…”
- “There is less clarity about…”

Avoid:

- “I’m reading your career as…”
- “I’m less certain about…”
- “If this feels directionally right…”
- Coaching-style next-step prompts inside the summary.

The summary should foreground concrete observations where the evidence supports them:

- number of roles;
- visible time span;
- locations or markets;
- seniority and management emphasis;
- consulting versus permanent-role patterns;
- quantified outcomes and scale indicators.

Instead of:

"The CV documents..."

Prefer:

"Your CV presents you as..."

Section Review

Each section should communicate:

"This is my current understanding."

Interaction Model

Each section should eventually support actions such as:

Explain
Challenge
Correct
Add evidence
Confirm

These modify the Twin rather than the displayed text directly.

Design Philosophy

The Mirror should feel like an ongoing conversation with the user's Digital Career Twin.

It is not a report.

It is not a dashboard.

It is a living reflection of the current evidence.

The Twin is the canonical model.

The Mirror is the interface.

User-editable evidence tags: As a user, I can add, edit, or remove tags associated with an evidence item so that the Twin reflects my own understanding of what that evidence demonstrates.
If a user adds a new tag, the system should review its suitability on other evidence and dynamically add it, rather than forcing the user to add it to each relevant item by hand.
