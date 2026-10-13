# Phase 02 — Windows Beta Implementation Plan

> Execute inline with superpowers:executing-plans and test-driven-development. User approved Phase02 continuous execution; native toolchain admin setup is user-run, live Cloudflare and Phase03 excluded.

**Goal:** Produce/test the existing Tauri Windows application where possible, with safe repeatable staging/build/artifact review and honest native/live acceptance.

**Architecture:** Preserve apps/windows frontend and Worker contract. Production build uses a validated HTTPS origin and isolated Tauri override config. Debug catalog-only build permits native UI smoke without inventing a production endpoint or audio. Media/credentials never enter release stages. Do not rewrite UI or add runtime services.

**Spec:** docs/MASTER_ROADMAP.md Phase02 and latest user instructions, existing docs/windows-app-architecture.md; Phase01 source637fbd1 is the parent.

## Constraints / review focus

- No merge/deploy/live R2/credential reads, BookVN downloads, original audio/data changes or Phase03 implementation.
- Phase01 PR review first; preserve READY FOR REVIEW/live gate, record browser-access blocker without extracting Git credentials.
- Toolchain installation requires user/admin; report immediately and keep independent source work moving. No command waits over15min without an update.
- Stale installers, leaked developer paths, missing frontend inputs, symlink escapes and build interruption must not yield a distribution marked valid.
- Debug catalog-only is explicitly not an online/listening release; no sample tones under real titles.
- Keep API origin/CSP explicit, no localhost or secret production embedded; prevent external page navigation and unneeded filesystem/shell capabilities.

## Task 1 — Phase01 technical review / PR

- [x] Verify branch ancestry, clean tree/diff/main, frontend49/Worker23/typecheck, exact index and secret history; Worker serving remains false.
- [x] PR #1 OPEN: https://github.com/ctcm251010/theoloi/pull/1 after user granted repository access. No merge; live gate retained.

## Task 2 — Native build safeguards

Files: scripts/build-windows.py, tests/test_windows_build.py, apps/windows/src-tauri/Cargo.toml, tauri.conf.json, src/main.rs; app.mjs/ui-core.mjs and corresponding tests if bootstrap mode needs support.

- [x] RED: prepare-only without toolchain; validate inputs/origin/metadata, allowlist stage, configuration unchanged even failed build, no symlink/media extras.
- [x] GREEN: implement prepare stage and override config without editing tracked Tauri config, version from metadata; compilation path and artifact freshness tested with mocks, then actual native builds.
- [x] RED/GREEN: catalog-only native debug mode cannot connect or play, HTTPS production mode stays unchanged; external navigation policy and Rust tests PASS.
- [x] Run offline build/frontend suites; actual compiled TEST EXE/installer recorded separately from mocks.

## Task 3 — Native acceptance / handoff

- [x] Recheck toolchain after user installs; actual debug/release/NSIS TEST builds PASS, preserve logs and original data.
- [x] Native startup/WebView2, disposable current-user install/uninstall and portable outside workspace PASS; browser mock audio/network/reload tests PASS. Native UI interaction/machine-clean/live explicitly pending, not counted as PASS.
- [x] Full regression,983 media/18 metadata integrity, artifact/no-credential review and independent final review.
- [x] Update docs/phases/phase-02.md, Windows instructions and current roadmap/tasks/decisions/changelog/backlog. Source commit7da2d00 verified in clean clone; no Phase03. Audit/commit/push handoff ledger follows; recommend Phase01 live acceptance then Closed Beta gates.

## Ledger

- User follow-up: TEST-only handoff không đáp ứng nghe thư viện thật trong EXE. Bounded correction trong Phase02: LOCAL build từ public projection983, explicit loopback backend read-only, native-origin CORS/bootstrap, một launcher backend+EXE; không thay kiến trúc production hoặc deploy. RED packaging/missing bootstrap/native403 đã tái hiện, GREEN; launcher double-open review finding được tái hiện rồi sửa bằng Windows byte lock. Build LOCAL thật, native session/catalog200; Python185 PASS/3 SKIP, frontend53, Worker24/typecheck,983/18 integrity. Native Play/seek/máy sạch/live không được suy ra từ bằng chứng này.

- Baseline637fbd1 clean; Phase02 branch created from exact Phase01 head, no divergence. Preflight missing cargo/rustc/MSVC/SDK, Node/Tauri/WebView2 available. User is installing tools externally.
- Ruling: continue in the authorized existing workspace on a dedicated branch, as in Phase01 — ignored operational inputs/dependencies already reside here; do not copy originals into a new checkout or recreate the project. Source-only clone remains the independent verification surface.
- Ruling: user explicitly authorizes complete phase implementation/review, so do not add intermediate design approval gates. Retain existing architecture and separate production permission gate.
- Native test builds will use a separate application identifier and explicit TEST titles with the three existing self-authored WAV fixtures over a loopback mock. These are acceptance artifacts, never a production or WATV audio release. Production keeps HTTPS-only origin validation; no fake endpoint will be invented to compile a release.
- Final evidence: toolchain READY; Python177 PASS/3 SKIP, frontend52, Worker23/typecheck, Rust1, metrics1. Clone source-only Python101 PASS/3 SKIP, frontend52, Worker21 PASS/2 SKIP/typecheck, metrics1; TEST prepare without private projections PASS. See Phase02 report for acceptance gaps and artifact hashes. Status READY FOR REVIEW.
