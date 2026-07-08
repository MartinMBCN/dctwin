# Release notes

Terse user-facing and acceptance-testing notes for each app increment. The app version is exposed at `/api/health` as `app_version`.

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
