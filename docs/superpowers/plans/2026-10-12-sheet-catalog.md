# Sheet Catalog Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation, with TDD and one final independent review.

**Goal:** Deliver the observed metadata catalog, reviewable audio mapping, and tested offline file pipeline.

**Architecture:** Safe retained snapshot → deterministic separate catalog/schema and mapping report. Local authorized input plan → rights checks, PDF/image validation, content-addressed artifacts, separate state and manifest.

**Tech Stack:** Python 3.13, existing jsonschema, pypdf, PyMuPDF, SQLite, unittest.

**Spec:** docs/superpowers/specs/2026-10-12-sheet-catalog-design.md; user's detailed implementation request.

## Global Constraints

- No audio/catalog/manifest/state modification, BookVN media downloads/screenshots, R2/credentials, HTTP downloader, or production bulk.
- Reuse the retained 542-row observation; observed scope only, not entire website.
- Explicit user instruction to implement autonomously takes precedence over extra design approval pauses. Execute inline in current workspace; no Git repository, worktree or commits.

## Review Focus

- Equal appendix numbers must never override mismatched titles.
- Unknown/restricted rights must not become authorization to store/convert/publish.
- Incomplete, renamed HTML, encrypted/repaired PDF and corrupt completed outputs must not pass.
- Windows path aliases, junctions and inputs/outputs colliding with audio must fail.
- Resume must validate input/output identity and preserve old verified artifacts on failures.

### Task 1 — Metadata catalog and matching

Files: source/snapshots/bookvn-vi-2026-10-12.sheets.json; schemas/sheet-catalog.schema.json; scripts/sheet_catalog.py; scripts/sheets.py; tests/test_sheets.py; catalog/sheet-sources.vi.json; docs/sheet-mapping-report.md; delivery/sheet-mapping.vi.json.

Interfaces: build_sheet_catalog(snapshot, audio); validate_sheet_catalog(catalog, audio, schema, snapshot=None); mapping_report(catalog, audio). Deterministic JSON/hashes via existing catalog_lib helpers.

- [x] Tests RED for missing builder/matcher/validator.
- [x] Implement strict metadata/schema and matching, then GREEN.
- [x] Build actual catalog; validate against snapshot; report exact matches/conflicts/duplicates/unmatched.

### Task 2 — Authorized local file pipeline

Files: scripts/sheet_media.py; scripts/sheet_pipeline.py; scripts/sheet-files.py; schemas/sheet-plan.schema.json; schemas/sheet-manifest.schema.json; tests/test_sheet_files.py; requirements-sheets.txt; .gitignore.

Interfaces: inspect_file(path); process_plan(plan, catalog, audio, root, state_path=None, manifest_path=None, dry_run=False, retry_failed=False, progress=None); validate_manifest(manifest, catalog, audio, root). Task 1 catalog rights/links consumed without mutation.

- [x] Tests RED with self-authored PDFs/images, malformed input, rights denial, path protection, dry-run/resume/retry and tamper cases.
- [x] Implement file verification, lossless raster conversion, separate state/lock and manifest; GREEN.
- [x] Small self-authored demo, inspect render, run process/resume/status/verify; no production processing.

### Task 3 — Handoff and final verification

Files: docs/sheets-windows.md; docs/sheet-implementation-report.md; this progress ledger and reference from bookvn-pdf-analysis.md.

- [x] Provide only CLI commands tested against real implementation, optional dependency setup and synthetic demo.
- [x] Run offline tests and final independent review; fix material findings with regression tests.
- [x] Verify pinned audio hashes unchanged; record blockers and deliver artifacts.

## Progress ledger

- Pre-flight: Task 2 consumes Task 1 source IDs, rights, audio links; shared schema fields locked by tests.
- Workspace: no Git repository; retain this ledger/artifacts instead of Git-specific helpers.
- Metadata: 542 rows and 7 observations exported from retained browser memory; no new media requests.
- Optional PDF dependencies: sandbox PyPI access failed; installing into project .venv via reviewed network escalation. Audio requirements unchanged.
- Task 1: 14 catalog tests GREEN after RED missing module/CLI; actual catalog validate PASS, 542 records, 489 candidate/1 conflict/52 unmatched, 0 verified. No source media requests.
- Task 2: 30 local-file tests GREEN. Demo 3 completed, resume 3 skipped, status/verify PASS; derived PDF render visually inspected. Synthetic tests verify embedded image pixels/order/dimensions.
- Review regression fixes: retain all valid prior editions across subset plans; retain last valid artifact on failed updates; reject populated manifest with fresh/missing state; validate DB/application ID/artifact JSON before writes; dry-run observes resume/retry selection; report duplicate hashes without merging editions. RED and GREEN logs retained in tmp/sheet-*.log.
- Final review: skill-required independent read-only reviewer; no remaining Critical/Important/Minor findings after fixes, including handoff docs and duplicate-hash summary. Review made no filesystem/network/secret changes.
- Declined-to-judge rulings: rights sufficiency and musical identity require human evidence, all production downloads/uploads/live behavior excluded as authorized; none treated as completed or bypassed.
- Final suite: 103 run, 102 PASS, 1 SKIP (existing delivery symlink test, Windows privilege unavailable); all 44 new sheet tests PASS. No changes to system privileges. Full log tmp/sheet-full-tests.log.
- Final validation: source-aware catalog PASS; BookVN manifest 0 assets/542 no-file PASS; synthetic demo 3 assets/4 files PASS. Audio catalog/manifest and metadata snapshot hashes unchanged. CLI/BAT dry-run/full/resume/status/verify/retry commands tested with synthetic data, no production batch.
- Completed feasible scope; blockers retained in docs/sheet-implementation-report.md: no permitted original PDF source, review of music/edition/rights, no remote sheet service/downloader/uploader. No pending implementation task within authorized feasible scope.
