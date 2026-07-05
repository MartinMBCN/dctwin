Sprint 2 
Objective
A CV can be automatically transformed into a semantic model that is recognizably describing the same person and conforms to the current Digital Career Twin schema.
By the end of the day, I can upload my own CV and receive a Career Mirror that is recognizably “me” and materially different from merely rebuilding the CV because it categorizes my experience using the current Digital Career Twin schema. The output is organized around the Digital Career Twin schema rather than the structure of the uploaded CV.
Validates the following hypotheses:
An LLM can reliably extract structured professional evidence from an unstructured CV.
The extracted evidence can be organized into a canonical Digital Career Twin that is materially different from the source document.
Organizing evidence according to the Digital Career Twin schema reveals meaningful patterns that are less obvious in the original CV.

Acceptance criteria
The system can extract:
facts,
roles,
evidence items,
candidate capabilities,
inferred career stage,
inferred professional identity,
missing or low-confidence fields.
The system tags every evidence item with one or more capabilities and one or more narrative themes, enabling later retrieval, visualization and inference.
Every inferred field includes confidence and rationale tags. Each tag includes confidence and rationale, and remains negotiable by the user. Have a controlled tag_catalog table or JSON file with canonical tags, IDs, type, description, and aliases.
Then evidence items reference tags by ID, with confidence and rationale stored on the relationship.

Stretch goal
The Career Mirror reveals at least one pattern that was not obvious from reading the CV alone.

Out of Scope
For Sprint 2:
No adaptive interview.
No editing.
No persistence beyond local storage.
No authentication.
No multiple CV reconciliation.
No visualizations beyond the Career Mirror.
