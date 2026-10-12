# THEOLOI repository implementation plan

Goal: publish safe source without moving/changing working AudioTP data. Retain apps/windows, workers/media-api and root pipeline paths. Keep operational datasets/generated catalogs local; publish schemas and audited self-authored fixtures. No empty packages.

Execution: inline, authorized by the user's end-to-end request. No intermediate approval gates/worktree relocation; initialize the specified existing workspace.

## Constraints / review focus

No media/download/upload/deploy, force-push, reset, credential or live R2 changes. Audit exact index, preserve remote history, hash original metadata/media before/after. Document private-input requirements for a clean clone; no fake audio or native/live success claims.

## Tasks

- [x] Inventory/dependencies/hashes; docs/repository-audit.md.
- [x] Normalize ignore, README/PROJECT/SETUP/AGENTS and repository-structure docs.
- [x] Redacted staged audit + Gitleaks; preserve local files (rerun before commit).
- [x] Python/frontend/backend, validators, integrity, Windows preflight. Browser smoke BLOCKED empty inventory; native BLOCKED missing toolchain. HTTP local PASS.
- [ ] Independent review, commit/push origin/main, verify remote SHA or document blocker.

## Ledger

No prior Git repository/history. Initialized main; remote fetch succeeded with no refs. Anonymous GitHub metadata 404: visibility not yet confirmed, conservative source-only publication regardless. Git uses exact process-scoped safe.directory because sandbox owns new .git; no global trust or ownership changes. Auto-review rejected requested .git ownership correction; no retry of that mutation.

Validation: Python167 PASS/2 symlink SKIP, frontend37 PASS, Worker15 PASS + dry-run/typecheck, benchmark metrics1 PASS. Catalog/delivery PASS; all983 media SHA/size exact; all18 original metadata/state/WAL/SHM hashes unchanged. Independent review found no blocker, checked exact staged vendor/fixture hashes and license presence. Optional cookie/session/HTML-snapshot guards added; pending audit-doc link resolved. No runtime source/path changes or native/live success claim.

Deferred minor: git diff --check reports 8 pre-existing whitespace/blank-EOF warnings in 4 old source/docs/generated-type files; retained bytes rather than unrelated formatting. No test failure or sensitive content is associated with these warnings.
