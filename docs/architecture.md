Architecture DRAFT

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
"I know how to read CVs."

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
