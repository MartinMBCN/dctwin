Backlog item: Tag learning and calibration

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
