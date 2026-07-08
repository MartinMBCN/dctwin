Architecture DRAFT
Technical view
                Outputs
                    ▲
                    │
      Career Mirror │
              CV    │
     Company Fit    │
 Interview Brief    │
                    │
             Digital Career Twin
                    │
                    ▼
               Twin Update
                    ▲
                    │
        Semantic Interpretation
                    ▲
                    │
               Extraction
                    ▲
                    │
          CV  Interview  Story  ...

Conceptual view
Reality
        │
        ▼
Evidence
        │
        ▼
Digital Career Twin
        ▲
        │
Preferences
        │
        ▼
Reference Models
        │
        ▼
Reasoning
        │
        ▼
Visualizations / Displays

Azure Architecture
Browser
      │
      ▼
Web App
      │
      ▼
Orchestrator
      │
      ├── Azure AI Foundry
      │        ├── CV Digest Agent
      │        ├── Interview Agent
      │        └── Mirror Agent
      │
      ▼
Digital Career Twin Store

Agentic Architecture
Source Adapter
──────────────
"I know how to normalize supported source material."

        ↓

Role & Evidence Extractor
──────────────────
"I know how to identify roles and extract professional evidence within each role."

        ↓

Candidate Matching
──────────────────
"I think these objects may refer to the same thing."

        ↓

Merge Decision
──────────────────
"Should they actually become one object?"

        ↓
        
Twin Mapper
───────────
"I know how to represent evidence using the DCT schema."

        ↓

Twin Repository
───────────────
"I own the canonical Twin."

Conceptual Architecture
Professional Life (the real world)
 → the reality.
Digital Career Twin
 → the canonical model.
Career Mirror
 → private reflection.
Gallery
 → public space.
Displays
 → individual public views.

The primary models
Twin

The user's evidence-based professional model.

The Twin represents the best current understanding of the user's professional identity, constructed from accumulated evidence and refined over time. It exists in the present and is the canonical representation from which all interpretations are derived.

Preferences

The user's desired future.

Preferences capture what the user wants rather than what the evidence currently supports. They describe aspirations, objectives, constraints, motivators, and trade-offs, and provide direction for interpreting the Twin.

Reference Models

External models of the professional world.

Reference Models describe the capabilities, expectations, structures, and patterns that exist outside the Twin. They are acquired as needed from trusted external sources and provide the context against which the Twin can be interpreted.

Data acquisition architecture
Each layer answers a different question.
Sources: Where did this information come from?
Roles: When and in what context did it happen?
Evidence: What actually happened?
Inferences: What does this collectively suggest?
Reflection: How should the user understand themselves?
Sources
    ↓
Roles
    ↓
Evidence
    ↓
Inferences
    ↓
Reflection

Evidence architecture

Role
└── Evidence
    ├── Achievement
    ├── Responsibility
    ├── Decision
    ├── Technology
    ├── Metric
    ├── Behaviour
    └── Outcome

Implemented Sprint 2 slice

Raw source file
      │
      ▼
Source Adapter registry
      ├── cv / PDF strategy
      └── cv / DOCX strategy
      │
      ▼
Normalized Source Document
      │ stable blocks, locators, content hash, privacy metadata
      ▼
Source Adapter Agent
      │ source-specific instructions + DCT schema + tag catalog
      ▼
Candidate Digital Career Twin
      │
      ▼
Acceptance Gate
      ├── JSON Schema
      ├── source and block references
      ├── role and evidence references
      ├── controlled tag references
      └── inference support
      │
      ▼
Accepted Twin + JSON Career Mirror

In parallel, source normalization may emit a private enrollment candidate:

Extracted email
      │ excluded from normalized model document
      ▼
Unverified Enrollment Candidate
      │ possession verification + user confirmation
      ▼
Account Identity Store
      │ opaque owner ID
      ▼
Digital Career Twin ownership link

The Account Identity Store owns authentication and contact identifiers. The Twin owns professional facts, evidence and inferences. Neither duplicates the other's data.

The model provider is an orchestration seam. A deterministic static provider supports local development and evaluation; the Foundry provider implements the same interface. Model output never writes directly to the canonical repository.

Architecture Decisions

ADR-013: Overview Brief is assembled from structured brief items

Status: Accepted.

Context: Sprint 5 showed that asking the model to emit a complete Overview Brief as prose creates a brittle presentation problem. The model often identifies useful observations, interpretations, uncertainties and attention items, but the UI must then reverse-engineer headings and bullets from generated paragraphs. Small wording changes produce unstable formatting and move the product away from the desired confidential executive briefing genre.

Decision: The model may emit transient `OverviewBriefItem` objects, each representing one professionally salient observation, interpretation, uncertainty, attention item or confidence statement. The application owns the canonical Overview Brief sections, ordering and rendering. The model should not emit the final displayed brief as its primary contract.

Consequences:
- Overview Brief content becomes inspectable and negotiable at item level.
- The UI can render stable sections without parsing prose.
- Future user capabilities can target one brief item at a time: explain, challenge, correct, confirm or add supporting information.
- The transient item contract must remain a presentation/interpretation contract, not a competing domain model. The Twin remains canonical.

ADR-014: Overview Brief quality is governed by an explicit quality contract

Status: Accepted.

Context: Iterating on the Overview Brief exposed multiple independent failure modes: missing or duplicated content, weak ordering, weak evidence, presentation density, shallow reasoning and incompleteness. Treating all of these as a single "summary quality" problem made tuning slow and imprecise.

Decision: The Overview Brief is governed by the Quality Contract in `docs/sprints/sprint5b.md`. The contract separates quality into six dimensions: Information Architecture, Editorial Quality, Evidence Quality, Presentation, Reasoning Quality and Completeness. Extraction prompts, reconciliation heuristics and UI rendering should be evaluated against these dimensions separately.

Consequences:
- Sprint feedback can name the failing quality dimension rather than requesting generic improvement.
- Model extraction remains responsible for candidate observations, but the application remains responsible for canonical sectioning, validation, deduplication and presentation.
- Future evaluation fixtures can score Overview Briefs against the six dimensions.
