# Phase 01 — Online Audio Implementation Plan

> Execute inline with superpowers:executing-plans; user authorized the whole phase, excluding production changes.

**Goal:** Harden existing private R2 API and online client, prove source-only reproducibility without publishing private data.

**Architecture:** Preserve Worker service, signed sessions/tickets, allowlisted R2 binding and one HTML audio player. Separate public type contracts from ignored production projections. Use synthetic local workerd tests plus optional real-media integration; never substitute fixtures in the app.

**Tech Stack:** Existing Node/JS/JSDoc, TypeScript, Wrangler/Miniflare, Python test tools, Tauri source.

**Spec:** docs/MASTER_ROADMAP.md Phase 01 and latest user instructions.

## Constraints / review focus

- No live R2/deploy, secret reads, audio/catalog/manifest/state changes, dependency upgrades or new framework.
- Empty clean clone must typecheck and run source tests; production bundle must fail when private inputs are missing.
- Session expiry/logout during a pending request must not revive playback or replace a new session.
- Shared cache must never bypass authentication; invalid requests must not reach R2.
- R2 replacement, missing objects, invalid range and upstream errors must fail closed with safe messages.
- Native/live acceptance stays separate and unverified until performed.

## Task 1 — Contracts and clone independence

Files: workers/media-api/src/contracts.d.ts, generated-data.d.ts, validate-data.mjs; service.mjs; tests/fixtures.mjs, service.test.mjs, source-runtime.test.mjs; package.json, tsconfig.json; optional private integration tests.

- [x] Add failing tests: reject unexpected private fields/invalid catalog, nonfinite duration, duplicate keys and unsafe object paths.
- [x] Run tests and observe failures; add explicit catalog/asset contracts and runtime boundary validation. Ambient declarations describe missing generated JSON without producing files or masking production bundle errors.
- [x] Add isolated workerd test bundled from synthetic entry, GET/HEAD/Range/conditional checks; private integrations explicitly skip with reason in source-only clone.
- [x] Run typecheck + full npm test in clone with no generated JSON, and private dry-run + integration in workspace.

## Task 2 — HTTP service hardening

Files: service.mjs, service.test.mjs, wrangler.jsonc if needed, Worker README.

- [x] Tests for public readiness without R2 calls, no-store/CDN bypass headers, CORS errors, limiter faults, missing/replaced object, 5xx and cancellation, range validators/HEAD, exact operation counts.
- [x] Implement minimal fixes and sanitized structured diagnostics (no URL/IP/session/body/key logging); keep get/head only, bounded body and no automatic upstream retry.
- [x] Verify 200/206/304/401/403/404/405/409/416/429/503 and document non-atomic metadata SHA limits and cost model.

## Task 3 — Online client/player lifecycle

Files: apps/windows/web/api-client.mjs, player.mjs, app.mjs as needed; matching tests.

- [x] Failing tests for expired tickets during seek/resume, duplicate ticket requests, logout/new login while request pending, network/429/5xx, malformed response, position-preserving retry.
- [x] Fix stale session/request handling and reuse valid in-memory tickets without persistent credentials/audio cache or retry loops.
- [x] Run frontend suite and real local browser smoke if tools available; distinguish local browser from live online/native.

## Task 4 — Acceptance and handoff

Files: docs/phases/phase-01.md, docs/phase01-operations.md; SETUP/README/Worker README; CURRENT_PHASE/ROADMAP/TASKS/CHANGELOG/DECISIONS/BACKLOG.

- [x] Read existing B10 summary only, verify mapping/pins and all 983 local hashes/18 baseline metadata hashes.
- [x] Run full offline regression, source-only clone tests/typecheck/runtime, private bundle integration, secret scan and independent review; resolve findings.
- [x] Document reviewed production config, request costs/cache policy, exact user-run deploy/rollback/live acceptance; no live execution.
- [x] Mark READY FOR REVIEW (not DONE: live approval/E2E pending), audit exact Git index, commit/push branch if safe; suggest Phase 02 then stop. Source4fc4d8d published and clean clone verified; docs ledger follows.
