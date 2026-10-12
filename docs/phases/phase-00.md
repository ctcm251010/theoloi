# THEOLOI — Phase 00: Repository Foundation

Status: **DONE**. Ngày 12/10/2026, Asia/Bangkok. Nghiệm thu source repository/clean-clone trong phạm vi Phase 00; không phải nghiệm thu Windows EXE hoặc live Cloudflare.

## Mục tiêu / phạm vi

Xác minh source monorepo từ GitHub có thể phát triển trong clone sạch bằng các test phù hợp, giữ nguyên 983 media, catalog/manifest/state gốc và Cloudflare. Không triển khai Phase 01. Spec: [MASTER_ROADMAP](../MASTER_ROADMAP.md), yêu cầu bổ sung của người dùng: giao một phase thì hoàn thành và đề xuất bước sau, không tự làm hết roadmap.

## Kế hoạch inline

- [x] Đọc context, Git status/remote/baseline và báo cáo trước.
- [x] Lưu master roadmap, phạm vi tự chủ và quản lý phase vào hệ thống docs có sẵn.
- [x] Clone remote main vào `tmp/phase00-clean-clone-20261012`; baseline `748d180404c44a2cd35b9c40fb44e81e7bac09cc`.
- [x] Cài dependency vào clone riêng theo SETUP và package-lock, kiểm tra không thay lockfiles/source.
- [x] Chạy frontend, Worker service/source-only, Python synthetic/offline và benchmark khả thi.
- [x] Kiểm tra path portability, thiếu private inputs và giới hạn native/live.
- [x] Self-review docs/acceptance và review độc lập không có finding; audit staged/history, commit/push source và xác minh remote SHA.
- [x] Ghi báo cáo và đề xuất Phase 01; dừng chờ người dùng, không có Phase 01 task đang chạy.

## Dependency / rủi ro / acceptance

Dependency: Git remote được phép truy cập; Python/Node/npm; các registry dependency theo tài liệu. Không cài system toolchain/admin trong phase này. Rủi ro: test production cần private snapshot/catalog/media ngoài Git; phải tách phạm vi và công bố phần chưa chạy, không copy dữ liệu hạn chế vào clone/commit hoặc fake production audio. Giữ lockfiles và dependency đã pin; không tự nâng phiên bản.

| Tiêu chí | Bằng chứng / trạng thái |
|---|---|
| GitHub/main hoạt động, giữ history | Clone baseline thành công; source commit11543ed8071d150b2d0a01871dd95906ba13b6ac trên local/remote bằng nhau, clone fast-forward tới đúng SHA |
| Không commit secret/media/private inputs | Exact index185 files/8,506,287 bytes,0 forbidden paths/0 content findings; Gitleaks staged44.24KB và4-commit history5.16MB:0 leaks |
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

Local evidence (ignored): `logs/repository-audit/phase00-*.txt`, `phase00-integrity.json`; clean clone nằm `tmp/phase00-clean-clone-20261012`. Hai test fixes được chép vào clone để nghiệm thu trước commit. Sau publish, overlay tạm được giữ trong clone stash (không xóa), clone fast-forward tới11543ed, tracked tree sạch; Python suite từ commit đã publish chạy lại94 tests/92 PASS/2 SKIP/0 lỗi trong46.176s. Đây không phải kiểm thử native app/live R2.

## Git / review

Baseline remote:748d180404c44a2cd35b9c40fb44e81e7bac09cc. Chỉ docs/workflow và hai test files thay đổi. Review độc lập không có finding; diff-check các file thay đổi PASS. [Source commit11543ed](https://github.com/ctcm251010/theoloi/commit/11543ed8071d150b2d0a01871dd95906ba13b6ac) đã push và verify bằng ls-remote + clone thực tế. Commit docs kết thúc phase theo sau, SHA cuối được bàn giao sau verify; không cần lặp tests khi chỉ cập nhật ledger kết quả. Không force/reset, không thay R2 hoặc credential.

User acceptance phase mới: chưa yêu cầu hoặc nhận nghiệm thu mới từ người dùng; DONE ở đây là acceptance kỹ thuật Phase 00 đã nêu. Native Windows runtime/live Cloudflare: NOT RUN. Full Worker typecheck clone: FAIL/precondition thiếu private inputs, giữ nguyên giới hạn công khai.

## Đề xuất sau nghiệm thu

Phase 01: đọc kết quả B10, audit mapping/config API có sẵn, hoàn thiện online client/Range/auth/error tests và chuẩn bị deploy/rollback để review. Không chạy live B10, public bucket hoặc deploy khi chưa có phê duyệt riêng.
