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

ADR-015: Evidence confidence, provenance and inference weighting are distinct

Status: Accepted.

Context: The system ingests multiple user-authored sources that may describe the same professional experience, including CVs, pasted text, interviews, LinkedIn profiles and future source types. Sprint testing showed that repeated ingestion of similar CVs could make recurring claims appear stronger, even when the repeated claim was not independent evidence. Multiple CVs are usually alternate representations of the same professional history, not independent witnesses.

Decision: The DCT distinguishes source provenance, evidence confidence and inference strength. Repeated sources strengthen provenance, not intrinsic evidence confidence. Evidence confidence is based on the quality of the evidence item itself: specificity, quantification, temporal precision, role/context clarity, internal coherence and explicitness in the source. Inference strength is based on convergence across multiple distinct evidence items, not repeated appearances of the same evidence item.

Implications:
- If a new source repeats an existing evidence item, reconciliation should merge provenance rather than create a new evidence item.
- Duplicate provenance must not materially increase evidence confidence or inference confidence.
- Near-duplicate evidence may refine canonical wording when the incoming source is clearer or more specific.
- Confidence may increase only because the canonical evidence has become intrinsically better, for example more specific, quantified or temporally precise; not because it appeared twice.
- Inference strength may increase when a source introduces genuinely new evidence that supports an existing inference.
- The Overview Brief may mention that the same evidence appears across multiple submitted sources, but must not imply independent corroboration from repeated user-authored CVs.

Consequences:
- Sources provide provenance.
- Evidence provides facts.
- Inferences emerge from distinct evidence.
- Reflection communicates the current state of the Twin without treating repeated CV wording as independent proof.

ADR-016: Overview Brief includes an editorial pass

Status: Accepted.

Context: Structured Overview Brief items improved formatting and evidence traceability, but repeated testing showed that semantically similar observations can still survive as separate bullets. This is not always a reasoning failure. It is often an editorial failure: the system has selected several true observations but has not compressed, ranked or organized them into a stable executive briefing.

Decision: Overview Brief assembly includes an editorial pass between inference and final rendering. The editorial pass does not generate new information. It merges semantically similar observations, removes redundancy, ranks observations by significance, ensures coverage, improves flow, removes repetition and preserves one material idea per bullet.

Editorial Quality Contract:
- Coverage: every professionally significant characteristic should appear at least once.
- Uniqueness: each observation should appear only once.
- Hierarchy: higher-order observations should precede supporting examples.
- Proportionality: space devoted to a topic should reflect its importance.
- Novelty: each bullet should contribute materially new information.
- Compression: observations that express substantially the same idea should be merged.

Consequences:
- Overview Brief generation becomes `Evidence -> Inference -> Editorial Pass -> Overview Brief`.
- The editorial pass may remove or merge candidate brief items, but must not invent new claims.
- Future assembly can become increasingly deterministic, with the model generating explanatory wording only where needed.
- Progression detection should become a first-class observation rather than a side effect of summary prose.

ADR-017: Sources are categorized by authorship and elicitation context

Status: Accepted.

Context: The initial DCT source model treats all source material as normalized professional evidence, but future capabilities will introduce materially different source origins. A CV, a performance review and a confidential manager interview may all produce evidence, but they do not carry the same independence, authorship, consent or inference-weighting implications.

Decision: DCT sources are classified into three broad categories:

1. Self-authored sources: the user describing themselves.
   Examples: CV, LinkedIn profile, career story, user interview, manually entered achievements.
2. Third-party artefacts: documents produced by other people or institutions before being submitted to the Twin.
   Examples: performance review, promotion recommendation, reference letter, award citation.
3. Elicited evidence: evidence generated specifically for the Twin through a designed collection process.
   Examples: confidential manager interview, peer interview, direct-report interview, client interview.

Implications:
- Source category is provenance metadata, not a separate reasoning layer.
- Self-authored repetition strengthens provenance but should not be treated as independent corroboration.
- Third-party artefacts may provide stronger independent support than self-authored sources, subject to authenticity, context and specificity.
- Elicited evidence can support future capabilities such as confidential reference collection, structured interviews and convergence/divergence analysis.
- The system should eventually distinguish source category, source author perspective and source format. For example, a PDF is a format; a performance review is a source type; third-party artefact is a source category; manager is a perspective.
- Confidence and inference weighting must account for category without blindly privileging any single category. A vague third-party artefact may be weaker than a precise self-authored achievement; an elicited interview may be rich but must preserve consent, attribution and confidentiality constraints.

Consequences:
- Source adapters should normalize content while preserving source category and perspective metadata.
- Reconciliation should continue to merge duplicate evidence, but inference weighting can later treat genuinely independent sources differently from repeated self-authored descriptions.
- The Mirror may eventually distinguish self-described, externally observed and elicited evidence, especially where they converge or diverge.
- Source removal and evidence revocation rules must respect source category, consent and provenance.

ADR-018: External service handshakes are first-class workflow states

Status: Accepted.

Context: Local Foundry-backed CV ingestion depends on Azure authentication. During Sprint 5 testing, an expired or missing Azure credential caused the user-facing workflow to appear stuck at a generic rendering step while the actual blocker was an Azure device-code sign-in prompt only visible in terminal logs. This cost disproportionate debugging time because authentication was treated as infrastructure plumbing rather than part of the observable Source Adapter workflow.

Decision: Any external service handshake required for a user-triggered workflow must be exposed as an explicit readiness/progress state. This includes local development auth, tenant selection, quota/configuration readiness, token acquisition and model-provider availability. The application should fail fast when configuration is missing, and should surface interactive handshakes in the UI when user action is required.

Implications:
- `dctwin.ping` is the local readiness boundary before meaningful CV ingestion testing.
- The start-of-day local workflow should refresh temporary Azure credentials before the server accepts CV ingestion work.
- Azure token acquisition is logged as its own progress phase, separate from model inference.
- Device-code sign-in prompts are surfaced in the UI and terminal.
- The upload wizard must distinguish “waiting for user authentication” from “model is thinking” and “rendering the Twin.”
- Credential expiry is the first hypothesis for Foundry-backed local failures, not a late-stage discovery.
- Future external integrations should follow the same rule: if a workflow cannot continue without external state or user action, that state must be observable within one to two minutes.

Consequences:
- Local test-environment failures collapse to a single ping/progress path instead of scattered symptoms.
- User trust improves because waits are explained honestly.
- Agentic orchestration remains debuggable: source adaptation, auth, model inference, reconciliation and rendering are distinct phases with distinct failure modes.
