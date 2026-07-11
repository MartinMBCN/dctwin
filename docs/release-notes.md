# Release notes

Terse user-facing and acceptance-testing notes for each app increment. The app version is exposed at `/api/health` as `app_version`.

## 0.3.39 — FAQ foundation

- Replaced the FAQ placeholder with initial product guidance for building, developing, reflecting on and eventually exploring the Digital Career Twin.
- Clarified that the Mirror is a negotiable reflection of the underlying Twin, not an immutable output.
- Introduced future visualizations as alternate views over the same canonical model.

## 0.3.38 — Start-of-day credential refresh

- Added `dctwin.dev --refresh-auth` to acquire Azure credentials before the local server starts accepting CV ingestion work.
- Reused a shared in-process Azure credential so the refreshed token is available to later Foundry calls in the same server process.
- Updated local startup instructions to refresh credentials at server start.

## 0.3.37 — Credential-first auth diagnostics

- Added `dctwin.ping --auth` to actively acquire an Azure token and report its expiry time.
- CV ingestion now logs Azure token expiry after successful token acquisition.
- README local troubleshooting now starts with credential expiry/auth validation before deeper investigation.

## 0.3.36 — Azure device-code prompt appears in the UI

- Added `/api/progress` so the browser can poll live backend ingestion progress.
- The upload wizard now surfaces Azure device-code sign-in instructions directly in the Career Twin UI.
- Starting a new upload clears the previous ingestion progress log so stale Azure prompts are not shown.

## 0.3.35 — Visible Azure token handshake

- Device-code authentication now prints the Azure sign-in URL, code and expiry directly in the terminal.
- CV ingestion logs explicit `azure_token_acquisition_started`, `azure_device_code_prompted` and `azure_token_acquisition_completed` events.
- Added `DCTWIN_AUTH_TIMEOUT_SECONDS` so local auth waits are bounded rather than appearing to hang indefinitely.
- `/api/health` now reports the selected local auth mode.

## 0.3.34 — Device-code auth is the local default

- Added `DCTWIN_AUTH_MODE` for local Azure authentication mode selection.
- Defaults to `device_code` so Azure login appears in the terminal instead of redirecting the app browser.
- Browser login remains available by setting `DCTWIN_AUTH_MODE=browser`; `auto` enables both device-code and browser fallbacks.
- `dctwin.ping` now reports and validates the selected auth mode.

## 0.3.33 — Tenant validation follows Azure Identity rules

- Relaxed `AZURE_TENANT_ID` validation to match Azure Identity: letters, numbers, hyphens and dots are accepted.
- `.env` loading now strips simple inline comments from values so copied configuration is less brittle.
- Runtime tenant validation now rejects labels, quotes, brackets and comments without requiring the tenant value to be GUID-shaped.

## 0.3.32 — Tenant ID validation in ping

- `dctwin.ping` added first-pass tenant validation, originally assuming GUID-shaped tenant IDs.
- Local auth normalized harmless `{tenant-id}` formatting before passing the tenant to Azure Identity.
- Superseded by 0.3.33 after confirming Azure Identity also accepts non-GUID tenant identifiers containing letters, numbers, hyphens and dots.

## 0.3.31 — Explicit Azure tenant for local auth

- Added `AZURE_TENANT_ID` support for browser, device-code, Azure CLI and Azure Developer CLI credentials.
- `/api/health` now reports whether the Azure tenant is configured.
- `dctwin.ping` warns when the tenant is missing because browser/device-code login may otherwise choose the wrong identity context.
- Updated `.env.example` to make tenant configuration part of the local setup path.

## 0.3.30 — Local environment ping

- Added a local environment ping to make Python, package import, Foundry configuration, Azure auth, writable state and port readiness explicit before CV ingestion.
- Added a guarded local dev runner that loads `.env`, runs ping, optionally resets local session/cache and then starts the preview server.
- Documented the repeatable local startup path so future test-environment failures have one clear front door.

## 0.3.29 — Browser/device-code Azure auth fallback

- Added Python-native Azure authentication fallbacks after `azd` and `az`: interactive browser login and device-code login.
- Local CV ingestion no longer requires installing Azure CLI or Azure Developer CLI when browser/device-code auth is available.
- `/api/health` now reports `interactive_browser` and `device_code` as available auth routes.

## 0.3.28 — Azure auth fallback

- Source Adapter authentication now supports either Azure Developer CLI (`azd`) or Azure CLI (`az`).
- Uses Azure Developer CLI first when available, then falls back to Azure CLI via chained credentials.
- `/api/health` now reports available local Azure auth methods and distinguishes missing auth tooling from missing Foundry configuration.
- CV ingestion preflight now fails early when neither supported Azure auth command is available.

## 0.3.27 — Live ingestion progress logging

- Added live ingestion progress events written to `.dctwin-local/logs/ingestion-progress.jsonl` as each backend stage begins or completes.
- Added explicit progress marks for model provider initialization, model provider close, reconciliation start and reconciliation completion.
- Makes stuck ingestion diagnosable before the request completes or fails.

## 0.3.26 — Runtime validation no longer imports jsonschema

- Replaced runtime `jsonschema` validation with a lightweight local validator for the schema subset used by DCT contracts.
- Keeps explicit DCT referential-integrity checks for source refs, role refs, evidence refs, tag refs and Overview Brief support.
- Removes another startup/downstream import-stall risk from the CV ingestion path.

## 0.3.25 — CV ingestion preflight health check

- Added a preflight health check before uploaded or pasted CV ingestion starts.
- The browser now verifies that the local server is reachable and the Source Adapter has a configured Foundry deployment before uploading or adapting CV material.
- The backend also rejects CV ingestion early when the model path is not configured, before text extraction or source adaptation work begins.
- Added a `system_health_checked` timing mark to successful CV ingestion runs.

## 0.3.24 — Startup import hardening

- Lazy-load PDF, DOCX and Foundry/Azure dependencies so the local web server can start before heavy adapter/model libraries are needed.
- Bypass optional `jsonschema` format-checker imports during contract validation; explicit DCT referential-integrity checks remain in place.
- Improves local startup reliability after virtualenv/Python import stalls.

## 0.3.23 — Header navigation alignment

- Reworked the product header so the main navigation aligns with the motto line rather than the large product title.
- Kept the desktop navigation on one line with tighter no-wrap button styling.
- Widened the desktop shell slightly so the product navigation breathes without wrapping awkwardly.

## 0.3.22 — Product navigation and source materials page

- Added top-level navigation for Your career twin, Visualizations, Source materials, Sign in/Your account, Interview and FAQ.
- Added placeholder pages for Visualizations, Interview and FAQ.
- Moved account access into the top navigation.
- Added a Source materials page listing uploaded/pasted sources and manually added achievements with upload time, text-block count, achievements added and achievements merged.
- Added session/persistent source-history metadata without storing uploaded CV files.
- Documented source removal as deferred because it needs careful evidence/provenance cascade rules.

## 0.3.21 — Sprint 5 scope clarification

- Re-scoped Sprint 5 as Career Mirror UX improvements plus Overview Brief quality work.
- Carved the Mirror user interaction model into a future sprint/backlog item.
- Documented that Explain, Challenge, Correct, Confirm, item-level Add evidence, tag calibration and Interview-style questions are intentionally deferred.

## 0.3.20 — Overview Brief editorial pass

- Added ADR-016: Overview Brief assembly now includes an explicit editorial pass between inference and final rendering.
- Updated the Overview Brief Quality Contract with coverage, uniqueness, hierarchy, proportionality, novelty and compression rules.
- Added section-aware editorial novelty filtering so bullets that do not add materially new information are dropped before section limits are applied.
- Added operating-model editorial compression for overlapping product-centric, team-of-teams and delivery-scaling observations.
- Added regression coverage for the Novelty rule.

## 0.3.19 — Provenance is not confidence

- Added ADR-015 distinguishing source provenance, evidence confidence and inference strength.
- Updated the Overview Brief Quality Contract to state that repeated user-authored sources strengthen provenance, not intrinsic evidence confidence.
- Updated duplicate evidence reconciliation actions to report `confidence_delta: none` and `inference_delta: none`.
- Prevented duplicate/remapped inference support from increasing inference confidence when no distinct new evidence was added.
- Added regression coverage for duplicate provenance not inflating tag confidence or inference confidence.

## 0.3.18 — Overview Brief evidence and ordering enforcement

- Enforced Evidence Quality by dropping model-generated interpretation and attention items that do not reference supporting evidence.
- Added contract validation that canonical interpretation and attention brief items require supporting evidence.
- Enforced Editorial Quality by ordering items within each section using an evidence-aware strength score, not salience alone.
- Added regression coverage for unsupported interpretation filtering, contract rejection and strongest-supported ordering.

## 0.3.17 — Overview Brief section budgets

- Added deterministic section budgets so Overview Brief sections remain scanable as more CVs are added.
- Refiled confidence-style observations into Confidence statement instead of Areas of less clarity.
- Suppressed speculative attention items about turnover or project-limited roles when not directly evidenced by the source.
- Added regression coverage for section limits, confidence refiling and speculation suppression.

## 0.3.16 — Overview Brief Quality Contract

- Added an explicit six-part Overview Brief Quality Contract covering Information Architecture, Editorial Quality, Evidence Quality, Presentation, Reasoning Quality and Completeness.
- Added ADR-014 to make the quality contract an architectural decision for Overview Brief extraction, reconciliation and rendering.
- Updated the Foundry extraction prompt to target the quality dimensions directly, especially section distinction, evidence strength, higher-order reasoning and completeness.
- Bumped the source-cache contract so quality-contract extraction is tested against fresh candidates.

## 0.3.15 — Overview Brief richness recovery

- Retuned compact extraction to aim for a fuller 8–12 item Overview Brief rather than overly terse coverage.
- Added schema-level caps for Overview Brief items, recurring patterns, capability hypotheses and unclear questions.
- Refiled governance/operating-model observations into Patterns and structural observations.
- Refiled P&L/reporting-line/detail caveats into Areas of less clarity.
- Suppressed non-CV-native caveats about retention outcomes, post-engagement impact and pure-contract status.
- Bumped the source-cache contract so new Overview Brief generation is tested without stale candidates.

## 0.3.14 — Strengths tab and leaner Overview

- Moved Current interpretation out of the Overview tab into a dedicated Strengths tab.
- Deprecated the Questions tab from the main Career Twin surface; unresolved questions remain internal until the future Interview feature.
- Kept Overview focused on the Overview Brief and account-save prompt.

## 0.3.13 — Overview Brief domain dedupe

- Merges career-scope bullets that describe the same seniority, date-range, industry and geography pattern even when phrased differently.
- Merges quantified-impact bullets by shared outcome domain and metrics, reducing repeated cost/reliability/release-frequency claims.
- Merges contract/frequent-transition attention items more aggressively.
- Suppresses handoff and long-term ownership gaps that a CV usually cannot answer reliably.

## 0.3.12 — Bounded compact extraction

- Increased the compact extraction output ceiling while keeping the extraction stage bounded.
- Instructed the model to keep source quotes, role summaries, achievements and interpretive items concise.
- Capped the interpretive layer conceptually: no more than 10 Overview Brief items, 6 recurring patterns, 6 capability hypotheses and 5 unclear questions.
- Bumped the source-cache contract so prior extraction candidates do not mask the bounded-extraction behavior.

## 0.3.11 — Overview Brief section normalization

- Normalizes structured Overview Brief items before deduplication so quantified outcome items file under Areas of higher confidence, contract/frequent-transition items file under professionally salient attention items, and team/leadership scale items file under patterns.
- Suppresses recruiter-logistics gaps that CV evidence cannot reasonably answer, such as availability, notice period, or reasons for short role duration.
- Added regression coverage for section normalization and logistical-gap suppression.

## 0.3.10 — Overview Brief confidence and capability dedupe

- Deduplicates confidence statements more aggressively when they share explicit source/fact/metric confidence language.
- Deduplicates capability-adjacent Overview Brief items when they share domain terms in the same section, such as MEL, frameworks, monitoring, dashboards, platform, automation, AI, health, KPIs and systems.
- Added regression coverage for confidence-statement and MEL/framework capability overlap.

## 0.3.9 — Overview Brief item deduplication

- Added section-aware fuzzy deduplication for structured Overview Brief items during reconciliation.
- Merges duplicate career-scope, contract-pattern, quantified-outcome, uncertainty and attention-item observations across multiple CVs.
- Preserves supporting evidence IDs, salience and confidence when duplicate brief items are merged.

## 0.3.8 — Overview Brief reconciliation references

- Fixed multi-source reconciliation so incoming Overview Brief item evidence references are remapped to the final canonical evidence IDs.
- Added regression coverage for duplicate evidence merging with structured Overview Brief items.

## 0.3.7 — Structured Overview Brief items

- Added ADR-013: Overview Brief is assembled from structured brief items.
- Added `OverviewBriefItem` extraction support so the model emits atomic brief-worthy observations rather than one prose brief.
- Added canonical DCT storage for `reflection.overview_brief_items`.
- Updated the UI to render structured Overview Brief items directly and keep prose parsing only as a backward-compatible fallback.
- Bumped the extraction cache contract to force regeneration under the structured brief-item contract.

## 0.3.6 — Canonical Overview Brief headings

- Normalized generated Overview Brief labels into the agreed executive-brief headings.
- Mapped `Recurring patterns`, `Interpretation`, `Seniority and scope`, and related generated labels into `Patterns and structural observations`.
- Preserved the full `Professionally salient attention items a recruiter or assessor would likely query` heading.
- Split confidence content into `Areas of higher confidence` and `Confidence statement` when the generated brief combines them.

## 0.3.5 — Overview Brief section parsing

- Expanded Overview Brief formatter recognition for model-generated labels including Observable facts, Education, Seniority and scope, Recurring patterns, Uncertainties and limits, and Confidence.
- Reduced wall-of-text bullets by splitting semicolon-separated list items while preserving punctuation inside parentheses.

## 0.3.4 — Overview Brief presentation

- Reformatted the Overview Brief for scanability using section headings, whitespace and bullets.
- Added parsing for common brief sections such as Career in brief, Patterns, Areas of less clarity, Attention items and Confidence statement.
- Split dense semicolon-heavy briefing text into scannable bullets and nested bullets where the brief introduces grouped examples.

## 0.3.3 — Overview Brief alignment

- Aligned Overview generation to `docs/sprints/sprint5b.md`.
- Reframed the overview as an objective confidential executive briefing rather than conversational Mirror prose.
- Updated prompt and fallback rules to establish observable facts before interpretation, include uncertainty neutrally and end with an evidence/confidence statement.
- Rendered the Overview Brief as briefing paragraphs instead of a single large headline.
- Bumped the extraction cache contract to force fresh extraction under the Overview Brief rules.

## 0.3.2 — Evidence-led Mirror voice

- Replaced first-person machine phrasing with evidence-led summary language such as `Your CV presents you as...`.
- Added a Sprint 5 Mirror Voice Contract covering concrete anchors, uncertainty phrasing and phrases to avoid.
- Updated the extraction prompt and app fallback to avoid coaching-style next-step prompts inside the overview summary.

## 0.3.1 — Conversational summary and education extraction

- Added education, certification, training and professional development to the compact CV extraction contract.
- Mapped extracted education/professional-development entries into canonical DCT person facts for the Education/Training tab.
- Tightened the reflection-summary prompt and mapper fallback toward a direct Mirror voice.
- Versioned the source cache by extraction-contract version so old cached candidates do not mask extraction changes.

## 0.3.0 — Sprint 5 Career Mirror surface

- Split the Career Mirror into Overview, Career themes, Questions, Career timeline and Education/Training tabs. Later 0.3.x increments replaced Questions with Strengths and deferred Questions to the future Interview feature.
- Moved mechanical views behind `?debug=true`: source blocks, reconciliation, timings, Twin JSON, local reset and technical input blurb.
- Rewrote the Overview summary into a more conversational “current understanding” voice.
- Added local timing JSONL logging for ingestion and manual-achievement updates.

## 0.2.11 — Account creation duplicate guidance

- Account creation with an existing email now says: `An account with this email address already exists. Please try logging in instead.`
- Duplicate-account checks now happen before one-time-code issuance and rate limiting.
- Fresh account creation no longer pre-populates the email field with a previous signed-in address.

## 0.2.10 — Account deletion wording and reuse

- Renamed signed-in destructive action from `Delete my DCT` to `Delete my account`.
- Kept the destructive action out of the immediate account-creation success state.
- Sign-in after account deletion now reports `No account found for this email`.
- Confirmed deleted account emails can be reused for a new account and Persistent Twin.

## 0.2.9 — Stable local account store

- Moved local account and Persistent Twin storage out of the repository working tree.
- Default local account path is `~/.dctwin/accounts.json`.
- Added `DCTWIN_STATE_DIR` override for local/dev state location.
- Kept Session Twin and source cache repo-local and disposable.
- Added regression coverage for account persistence across checkout/project-root changes.

## 0.2.8 — Persistent updates after sign-in

- Signed-in CV uploads, pasted CVs and added achievements now immediately save back to the Persistent Twin.
- Account dialog now shows creation date, last login, login count, last DCT change and session expiry.
- Restored `Delete my DCT` inside the signed-in account-management dialog.
- Added regression coverage for authenticated updates saving the Persistent Twin.

## 0.2.7 — Account modal state fixes

- Restored detected-email selection during account creation when a Session Twin exists.
- Kept detected emails hidden during sign-in.
- Logout now closes the account dialog instead of prompting immediate sign-in.

## 0.2.6 — Sign-in requires a saved Twin

- Split account creation from sign-in at the backend contract.
- Account creation now requires a current Session Twin.
- Sign-in now requires an existing account with a saved Persistent Twin.
- Prevented orphan email-only accounts from being treated as valid DCT accounts.

## 0.2.5 — Explicit no-saved-Twin state

- Added explicit UI handling for accounts that exist but have no saved Twin.
- Header distinguishes `Signed in` from `Saved Twin`.
- Added regression coverage for the no-saved-Twin edge case.

## 0.2.4 — Account dialog polish

- Post-account-creation dialog now offers `Log out` or `Continue`.
- Sign-in code screen now offers `Sign in` or `Cancel`.
- Successful sign-in closes the account dialog automatically.
- Removed account deletion from the post-creation success moment.

## 0.2.3 — Logout clears local Twin state

- Logout now clears the Session Twin and source cache from the browser/server session.
- Saved account/Persistent Twin remains intact.
- Refresh now recognises authenticated saved-account state.
- Added regression coverage for logout preserving account data while clearing local session state.

## 0.2.2 — Testable account UI flow

- Hid account controls until a Twin exists, except for returning sign-in.
- Split account modal into clearer create-code-verify-signed-in states.
- Added sign-in path after logout.

## 0.2.1 — First account UI slice

- Added account modal, email entry/candidate selection and local simulated code display.
- Added session duration controls and visible session expiry.
- Added conflict handling for saved Persistent Twin plus local Session Twin.
- Added logout and account deletion UI hooks.

## 0.2.0 — Sprint 4 account persistence foundation

- Added local account repository and passwordless email-code primitives.
- Added hashed one-time codes, 60-minute expiry, single-use enforcement, newest-code-only verification and rate limiting.
- Added auth sessions with `created_at`, `expires_at`, `revoked_at` and `last_seen_at`.
- Added Persistent Twin save/load/delete operations.
- Added local auth web routes for code request, verification, merge resolution, logout and account deletion.

## 0.1.3 — Product title typography

- Changed the `Digital Career Twin` product title to Helvetica Neue / sans-serif.

## 0.1.2 — Sprint 3 visual polish

- Removed the old four-step pipeline display after the wizard UX replaced it.
- Enlarged the product name and replaced the subtitle with “Reflect on your professional life”.
- Shifted page styling to the silver/grey visual direction.

## 0.1.1 — Versioned health and batched achievements

- Added semantic app version to `/api/health`.
- Added batched “Add achievements” support, one achievement per line.
- Updated UI labels for “Recurring career themes”.

## 0.1.0 — Local Sprint 3 DCT prototype

- Added local CV ingestion for PDF, DOCX and pasted CV text.
- Added staged extraction path: source adapter extraction, deterministic mapping and reconciliation into the DCT schema.
- Added local Career Mirror rendering with roles, achievements, tags, timings and reconciliation view.
- Added source cache and reset flow for local development.
- Added evidence display under roles and improved reconciliation/deduplication heuristics.
