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

Evidence Extractor
──────────────────
"I know how to find professional evidence."

        ↓

Twin Mapper
───────────
"I know how to represent evidence using the DCT schema."

        ↓

Twin Repository
───────────────
"I own the canonical Twin."
