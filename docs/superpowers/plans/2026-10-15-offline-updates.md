# AudioTP Offline & Updates Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans or subagent-driven-development task by task. User explicitly requested autonomous sequential stages; no redundant approval handoff.

**Goal:** Real verified native offline playback/download management and prominent signed startup updates, build/release after verification.

**Architecture:** Preserve current Tauri2/Worker/player/updater. Native owns managed files, UI owns presentation; current authenticated media API supplies bytes. Independent native offline, UI and updater modules share interfaces in spec.

**Tech Stack:** Rust/Tauri2, vanilla JS/CSS, Node workerd tests, existing Python build/publisher.

**Spec:** ../specs/2026-10-15-offline-updates-design.md

**User steering15/10:** finish local code/tests and export production EXE/NSIS ready for GitHub, then STOP for review. Do not push/tag/publish GitHub or deploy/publish R2 in this turn. Release steps below become a prepared handoff, not authorization to execute now.

## Global constraints

No original983media/catalog/manifest/state mutation, no secret read/output/commit, no bulk real downloads, retain identifier and signing key, keep R2 private. Windows app data outside installation; single player, one downloader; explicit install and bulk-delete confirmation. Use manifest count not hardcoded983 for completeness.

## Review focus

- Reparse points/hardlinks/path traversal must never expose or delete unrelated files.
- Pause/crash/expired token/HTTP200 instead of206 must preserve verified files and reject unsafe append.
- Hash failures/disk exhaustion cannot produce completed status; fresh startup detects invalid files.
- Offline startup/401 must not stop local playback or require login; queue must exclude unavailable tracks.
- Late updater/download completion after logout/cancel cannot resurrect credentials or install without click.

## Tasks

- [x] Backend metadata contract: RED tests for auth/membership/no key exposure, implement `/v1/offline-manifest`, update native-mock and adapter/packager static allowlists, run Worker tests/typecheck.
- [x] Native offline module: tests with temporary authorized bytes for download/skip/range/hash/disk/pause/retry/delete/restart; implement spec commands and scoped protocol, run Cargo tests including boundary regressions and pacing/429 cancellation.
- [x] UI offline module: injected-native tests for core counts/jobs/mode/fallback/selection/deletion; integrate existing UI/player/history/quick/search, responsive browser tests with clearly labelled fixtures.
- [x] Updater module: preserve official plugin + source pinning, tests startup/defer/progress/offline/error/cancel/version signature; modal integration, older client compatibility; prepare deployment config without leaking secrets.
- [x] Integrate commands/CSP/build inputs, affected regressions, independent Worker/frontend review + root native review/fixes, verify original data unchanged.
- [x] SemVer1.1.0 selected from actual tags; production EXE/NSIS/signature build, TEST installer app-data upgrade preservation; document native GUI/live limitations.
- [ ] Prepare validated selected installer/signature/hash/source release handoff; publishing/source push/tag/GitHub Release and Worker/R2 changes deferred by latest user instruction. Never use test audio under real titles or fake pass missing private inputs.
- [x] Update CURRENT_PHASE/TASKS/ROADMAP/CHANGELOG and learning guide requested by user; recommend next scoped work then stop.

Final local handoff: docs/release-1.1.0-report.md. Native GUI/live API/actual production updater install remain review gates; no claim DONE for those. Remote publication deliberately deferred, not silently skipped.
