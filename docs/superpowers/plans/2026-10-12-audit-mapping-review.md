# Audit and mapping review implementation plan

Execute inline with executing-plans and TDD. Spec: ../specs/2026-10-12-audit-mapping-review-design.md.

## Constraints / Review Focus

No secrets/live R2/B10/audio or bucket mutations. Test malformed S3 responses, duplicate expected records, partial reports, retry bounds, SDK guard before network. Review decisions must preserve source/audio catalogs, reject unknown IDs/stale pins, remain atomic under invalid batches/concurrency, keep history, prohibit implicit rights changes/automatic approval, sanitize HTML and protect Windows paths including hard-link aliases. Inspect partial workflows after process interruption. User explicitly requests autonomous A/B implementation; skill pauses for design approval are superseded. No Git in workspace; ledger retained here rather than Git helpers.

## Tasks

- [x] A: Add offline audit tests, demonstrate uncovered failures, fix verifier, test report/CLI with synthetic dependencies. Files verify-r2.py, tests/test_verify_r2.py, r2-verification.md.
- [x] B1: Review schemas/library/CLI and tests; priority queue, apply/dry-run/batch/revision/identity checks and verified export. Files sheet_review.py, review-mapping.py, schemas/sheet-review*.json, tests/test_sheet_review.py, reviews empty store/export.
- [x] B2: Static local review HTML generator with controlled proposal download, parser + actual generated JS constructor tested offline. Browser file interaction QA blocked by browser policy and disclosed; no workaround/server. Docs mapping-review.md.
- [x] C: Current official docs comparison and executable roadmap, docs/windows-app-architecture.md. No production implementation.
- [x] Final: all offline tests, independent final read-only review, regression fixes, baseline hashes, handoff report/file list/commands.

## Progress ledger

- Read-only context: no AGENTS.md/SETUP.md found in workspace/parent; user AGENTS instructions apply. Previous sheet context and user-specified reports read. Historical B8/B9 reports are dated snapshots, not new remote verdicts.
- Design: separate JSON review overlay rather than editing catalog or adding transfer-state tables. Static HTML proposal + CLI import chosen instead of a localhost write server. Approval validates musical identity assertions only, never usage rights.
- B10 remains user-run. Existing verifier permits only ListObjectsV2/HeadObject and flags contentSha256Verified false. No command invoking real verifier will run in Codex.
- Task A: 11 initial mock tests found duplicate expected IDs, malformed HEAD and cleanup report loss (RED → GREEN). SDK allowlist tested against every S3 service operation with transport blocked, only LIST/HEAD stubbed. No live client/credential access.
- Task B1/B2: 12 initial tests RED → GREEN for overlay/CLI/static UI. Actual empty store/queue/export initialized; 542 queue rows, main464 then ten duplicated appendix records, 0 actual events/verified links. A single main464 defer CLI dry-run ran without writes.
- Task C: Cloudflare/Context7 skills used; fetched current official Tauri, WebView2, Electron, .NET and R2 docs. Recommendations marked design inference/unbenchmarked; no app/deployment code.
- Final review: one independent read-only reviewer, two Important findings. One fix pass: require nonblank string LIST/HEAD ETags; require explicit reject before changing previously approved song even after defer. Both regressions observed RED then GREEN. 12 audit tests +14 review tests now GREEN.
- Final validation: concurrency/interruption test gap regraded Important because review-history preservation is essential. Added held OS lock + competing CLI writer and KeyboardInterrupt before os.replace tests; unchanged store and subsequent successful writer verified. No production change required for existing atomic/OS-lock behavior, no deferred minor remaining.
- Final: Ruling: live R2/credential/state/audio correctness excluded by user — no remote verdict, only offline mock preflight — cost if wrong: live discrepancy awaits user-run B10.
- Final: Ruling: musical identity/edition/rights require human evidence — no actual approvals or rights changes; overlay empty — cost if wrong: mappings remain pending until manual review.
- Final: Ruling: actual HTML browser interaction blocked by file: policy — disclose parser/JS-only QA, no server/alternate surface workaround — cost if wrong: user may find UI render/download issues during manual local use.
- Final: Ruling: external framework/deployment performance only proposal — root retrieved official docs independently, no runtime benchmark or deploy — cost if wrong: technology choice may change after prototype.
- Final: Ruling: power-loss durability not simulated — held-lock/interrupted replacement tested, retain backups, no broader durability promise — cost if wrong: restore decision store from backup after a filesystem failure.
- Final complete: 129 offline tests in 70.108s, 128 PASS / 0 FAIL / 1 SKIP (Windows file-symlink privilege); log tmp/review-final-full-tests.log. Audio catalog/manifest, sheet catalog/snapshot and R2 config hashes unchanged. Sheet validation PASS; real store 0 events / 0 verified, export 0 links, queue/HTML 542 sources. Handoff includes actual user-run commands and limitations. Live B10 remains unrun by design. Retained logs replace Git commit/task helpers because no Git repository exists.
