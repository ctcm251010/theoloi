# AudioTP Windows MVP implementation plan

**Minimal UI follow-up 12/10/2026 — DONE source/local validation:** header + horizontal navigation + search/three uncounted tabs, plain rows, compact responsive fixed player, settings/filter/playback dialogs. Frontend 34 PASS; Python 165 PASS / 2 symlink SKIP; real Chrome Bang playback guide/instrumental/silent, search/filter/favourites/history/theme, responsive 320/355/768/1745 CSS px; screenshots captured. Independent review: no Critical/Important findings. Native EXE remains BLOCKED by missing toolchain. Details: `docs/minimal-player-redesign.md`. Original milestone ledger below is historical.

**Goal:** Build a Windows-oriented listening MVP with three separate catalogs and two quick-play cards, using the existing verified identities. User explicitly requests implementation without intermediate approval gates; no live deployment is authorized.

**Architecture:** Static ES modules + a single HTML audio element, packaged by Tauri 2/WebView2. A safe client projection removes source HLS/local/object paths. Development playback uses self-generated tones, visibly labelled demo; private R2 access stays unavailable until authenticated backend and distribution policy are reviewed.

**Scope:** Read-only WATV UI research, independent quick-play metadata, offline tests and browser smoke tests. No R2 calls, credential access, BookVN assets, audio catalog/manifest mutations or new production downloads. Rust/MSVC are not currently on PATH; native compilation may require a user-run prerequisite step.

## Tasks

- [x] Observe pinned items, three tabs, search and player in Chrome Bang; record observed behavior separately from unknown source internals and end-to-end sequence behavior.
- [x] Export client catalog with 485 guide, 485 instrumental, 13 silent; validate complete manifest joins and protect original hashes. Keep quick-play records separate and fail closed on unverified source/rights.
- [x] Implement UI/player ES modules and unit tests (search/filters, tabs, one active audio, races, pause/seek/volume, queue/end modes, failure/retry). Sidebar, favourites/history, theme and keyboard accessibility; no persisted credentials.
- [x] Provide a loopback-only preview server and generated permitted sample audio. Test Range/HEAD/traversal/security boundaries and portability without project data folders.
- [x] Add minimal Tauri configuration/Rust shell, least privileges, restrictive CSP and build instructions. Compile attempted; cargo missing. Native build/runtime are BLOCKED, not complete.
- [x] Exercise actual browser UI at wide/narrow widths, media switching and errors; save own-app screenshots/evidence. Run offline regression suite, update handoff docs and verify protected hashes.

## Interfaces

`apps/windows/web/catalog.client.json`: `{schemaVersion:1, revision:string, tracks:[{id, logicalId, mode:'guide'|'instrumental'|'silent', section:'main'|'appendix'|null, number:number, title, category, durationSeconds:number}]}`. Track ID is existing asset ID; silent numbers are sourceDisplayNumber, independent namespace.

`apps/windows/web/quick-play.json`: array of `{id,title,available:false,reason,assetIds:[],sourceStatus,rightsStatus}`. No raw WATV URL is shipped. Research evidence is stored separately from playable authorization.

Frontend imports `./catalog.client.json` and `./quick-play.json` via fetch. Demo resolver provides only `./fixtures/guide.wav`, `instrumental.wav`, `silent.wav` (self-created 12-second tones, not actual songs). Actual duration comes from media. Live resolver is a separate interface and deny-by-default until configured authentication is implemented.

Root owns exporter/server/fixtures/Tauri/docs; frontend implementer owns web HTML/CSS/modules/tests only. Independent work may run in parallel under dispatching-parallel-agents skill. No Git repository exists, so no worktree/commit is created.

## Review focus

- A stale ticket/play completion must not revive old audio after a new selection.
- Changing visible tab does not implicitly change currently playing variant or captured queue.
- Quick-play approval is separate from source identity; no confidence-based permission.
- Silent category/number does not cause joining to guide/instrumental.
- Missing backend, non-finite duration, timeout and denied playback produce recoverable states without fabricated URLs.

## Verification ledger

Follow-up 2026-10-12, user-requested Quick Listening: implemented compact three-item region beneath tabs; explicit snapshot-ordered silent queue (first 19977), prayer placeholders fail closed, search/manual-collapse precedence, persistent manual preference, reserved layout for automatic hiding. Offline frontend 37 PASS; Python 167 PASS + 2 platform SKIP. Browser regression includes active shortcut restoring silent/all view before pause/resume, >50% priority guards, continuous ended transition and 320px dark/light layout. Full local media SHA check 983/983 and protected metadata hashes unchanged. Evidence/report: docs/quick-listening-report.md. No new audio, R2 or native binary changes.

2026-10-12: Python 159 total / 157 PASS / 2 symlink SKIP; Node 24 PASS. Real Chrome smoke and separate portable web-root copy with self-authored quick fixtures exercised; error/retry verified using missing/restored sample WAV. Client projection 485/485/13 and five protected baseline hashes PASS. Tauri CLI 2.12.2 JSON schema PASS. Actual native build failed before compilation: cargo program not found. No live R2/authenticated API or native runtime results claimed. Evidence and commands in docs/audiotp-windows-implementation.md and apps/windows/README.md.

Review rulings: quick state handling was completed for loading/pause/error/retry instead of only eligibility; production quick records remain unavailable/unknown. Whitespace normalization added after a failing Unicode search regression. Player late-play timeout/media-error regressions pass. Browser copy fixtures exposed PowerShell pipe encoding loss in temporary labels; production UTF-8 files and Vietnamese search are unaffected. Native build, source/rights review, live API, app-managed cache and production signing/updater remain follow-up work, with no fabricated endpoint/download command.

## Autonomous P0–P4 continuation — 12/10/2026

The user rejected mock tones under actual hymn titles. Browser reproduced `fixtures/guide.wav` selected for main:1; all 983 completed M4A files still exist. Never fall back to demo for an actual catalog item again.

- P0 DONE source + local integration / BLOCKED live deployment: shared Worker, exact pinned allowlist, group auth + scoped media tickets, GET/HEAD/Range/ETag/integrity, CORS/rate limits. Actual M4A tested through read-only file adapter; bundle also tested in local workerd R2. No live R2 or credential read.
- P1 DONE UI/gating / BLOCKED new source/rights review: both quick items separate and unavailable, no audio fallback; main 983 unaffected.
- P2 BLOCKED native compilation: Node/npm/Tauri CLI available, WebView2 registry entry found; Rust/Cargo absent, MSVC build tool installation not found. Prepare setup/preflight and continue code independently.
- P3 DONE offline/mock/local tests / NOT VERIFIED native/live: Python 167 (165 PASS, 2 symlink SKIP), frontend 33 PASS, backend 15 PASS, typecheck/dry-run/schema PASS; 30 browser observations with real M4A, seek, repeat/continuous and actual outage/retry. Screenshot capture blocked; no fabricated screenshot. Workerd rootPath/CWD startup issue fixed and npm suite passed from Worker folder.
- P4 DONE release/preflight/secrets tooling and docs / BLOCKED artifacts: build lock, config backup/restore, no demo/audio in staged release, pre-copy binary validation, source/API/CSP configuration and user guides tested. Native toolchain and user-approved deployment still required; no EXE/installer/live E2E claim.

Design: no access code or session persisted in browser storage. Group code entered by authorized user, HMAC session in memory, asset-bound expiring media URL; no arbitrary object key accepted. Session epoch allows group-wide revocation. Production serving remains disabled by default until user review. Worker logs must not capture signed URL queries. Local adapter is loopback-only and cannot write R2; it uses actual local M4A for personal verification, not a substitute claim for live R2 E2E.
