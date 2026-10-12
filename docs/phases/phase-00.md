# THEOLOI — Phase 00: Repository Foundation

Status: **READY FOR REVIEW**. Ngày 12/10/2026, Asia/Bangkok. Tests và integrity hoàn tất; final review/publication đang được xác minh.

## Mục tiêu / phạm vi

Xác minh source monorepo từ GitHub có thể phát triển trong clone sạch bằng các test phù hợp, giữ nguyên 983 media, catalog/manifest/state gốc và Cloudflare. Không triển khai Phase 01. Spec: [MASTER_ROADMAP](../MASTER_ROADMAP.md), yêu cầu bổ sung của người dùng: giao một phase thì hoàn thành và đề xuất bước sau, không tự làm hết roadmap.

## Kế hoạch inline

- [x] Đọc context, Git status/remote/baseline và báo cáo trước.
- [x] Lưu master roadmap, phạm vi tự chủ và quản lý phase vào hệ thống docs có sẵn.
- [x] Clone remote main vào `tmp/phase00-clean-clone-20261012`; baseline `748d180404c44a2cd35b9c40fb44e81e7bac09cc`.
- [x] Cài dependency vào clone riêng theo SETUP và package-lock, kiểm tra không thay lockfiles/source.
- [x] Chạy frontend, Worker service/source-only, Python synthetic/offline và benchmark khả thi.
- [x] Kiểm tra path portability, thiếu private inputs và giới hạn native/live.
- [ ] Self-review docs/acceptance, audit staged/history, commit/push và xác minh remote SHA.
- [ ] Báo cáo và đề xuất Phase 01; dừng chờ người dùng.

## Dependency / rủi ro / acceptance

Dependency: Git remote được phép truy cập; Python/Node/npm; các registry dependency theo tài liệu. Không cài system toolchain/admin trong phase này. Rủi ro: test production cần private snapshot/catalog/media ngoài Git; phải tách phạm vi và công bố phần chưa chạy, không copy dữ liệu hạn chế vào clone/commit hoặc fake production audio. Giữ lockfiles và dependency đã pin; không tự nâng phiên bản.

| Tiêu chí | Bằng chứng / trạng thái |
|---|---|
| GitHub/main hoạt động, giữ history | Clone baseline thành công; remote SHA đã khớp ở task trước, kiểm tra lại cuối phase |
| Không commit secret/media/private inputs | Audit exact tracked index + Gitleaks trước push |
| Setup đủ rõ / dependencies tái lập | Venv Python3.14.4 mới, pip install hai requirements PASS, pip check PASS; npm ci Windows2/Worker39 packages PASS, tracked lockfiles không đổi; postinstall warnings riêng bên dưới |
| Clean clone chạy test phù hợp | Frontend37 PASS; Worker service12 PASS; metrics1 test-file PASS; Python94 tổng:92 PASS/2 SKIP/0 lỗi. Lệnh thật trong SETUP |
| Không regression do refactor | 0 file moved; full Python workspace170 tổng:168 PASS/2 SKIP/0 lỗi,105.196s; manifest pin test chạy thật trong workspace, không skip |
| Không phụ thuộc absolute workspace runtime | Test chạy từ clone path khác, không copy production inputs; demo test dùng tempfile/audio fixture. Rà runtime source: đường D:\\Workspace chỉ có trong docstring hướng dẫn helper, không là fallback runtime |

Native Windows/EXE và live Cloudflare E2E nằm ngoài acceptance Phase 00; ghi NOT RUN, không suy từ mocks. Browser smoke của baseline đã thực hiện trên Chrome Bang ở repository-audit.md; không sửa UI trong phase này.

## Kết quả / lỗi đã xử lý / giới hạn

Lần chạy đầu có hai Python ERROR trong93 tests: production manifest không được publish và demo test giả định tmp/audio catalog có sẵn. Đã tách manifest pin integration (SKIP có lý do nếu thiếu private file) khỏi read-only SQLite status test, giữ nguyên pin983/schema guard. Demo truyền audio fixture tự tạo và dùng tempfile chuẩn, không cần tmp trong clone. Không sửa implementation downloader/uploader/player hoặc production manifest.

Chạy lại Python clone94 tests:92 PASS/2 SKIP,46.972s. Hai SKIP: private manifest và Windows symlink. Full workspace170 tests:168 PASS/2 SKIP; hai SKIP là symlink tests, private manifest test PASS. Không cộng các nhóm test trùng nhau thành một tổng giả.

Worker full typecheck trên clone trước prepare **FAIL exit1**: TS2307 thiếu generated/catalog.json/assets.json và TS7006 phát sinh từ thiếu inferred type. Lệnh này có precondition private inputs; không tính PASS, không nới TypeScript hoặc fake production JSON. Nhóm service12 vẫn chạy độc lập. Full Worker dry-run/runtime/HTTP tests không chạy trong clone; baseline workspace15 PASS trước đó không được nhận là run mới của phase này.

Npm ci Worker cảnh báo postinstall esbuild/workerd bị chặn bởi allowScripts. Không nới policy; nhóm tests thực thi đã nêu không cần postinstall đó, clone native Worker bundle/runtime chưa xác minh. Fixture font/PDF checks có ResourceWarning khi đóng HTTPError trong test; không phải FAIL, không sửa server để che warning.

Fresh integrity:983/983 media size/SHA đúng manifest,18/18 original metadata/state hashes không đổi. Không thêm dữ liệu private vào clone; dependencies chỉ trong clone .venv/node_modules ignored.

Local evidence (ignored): `logs/repository-audit/phase00-*.txt`, `phase00-integrity.json`; clean clone nằm `tmp/phase00-clean-clone-20261012`. Hai test fixes được chép vào clone để nghiệm thu trước commit; sau publish phải fast-forward clone tới commit đó và xác nhận tracked tree sạch. Đây không phải kiểm thử native app/live R2.

## Git / review

Baseline remote:748d180404c44a2cd35b9c40fb44e81e7bac09cc. Chỉ docs/workflow và hai test files thay đổi. Final review, exact-index audit/Gitleaks, push và clean-clone fast-forward đang chờ hoàn tất; SHA cuối được bàn giao sau verify. Không force/reset, không thay R2 hoặc credential.

## Đề xuất sau nghiệm thu

Phase 01: đọc kết quả B10, audit mapping/config API có sẵn, hoàn thiện online client/Range/auth/error tests và chuẩn bị deploy/rollback để review. Không chạy live B10, public bucket hoặc deploy khi chưa có phê duyệt riêng.
