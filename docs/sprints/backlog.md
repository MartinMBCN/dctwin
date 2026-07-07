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
