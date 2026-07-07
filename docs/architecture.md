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
