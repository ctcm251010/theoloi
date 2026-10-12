# THEOLOI — Repository audit

Ngày 12/10/2026, Windows, workspace `D:\Workspace\AudioTP`. Nhiệm vụ: chuẩn hóa/publish source, không triển khai dịch vụ hoặc thay dữ liệu AudioTP.

## Cấu trúc trước và sau

```text
Trước:                         Sau:
apps/windows                   apps/windows                 (giữ nguyên)
workers/media-api              workers/media-api            (giữ nguyên)
scripts/tests/schemas          scripts/tests/schemas        (giữ nguyên)
benchmarks/score-viewer         benchmarks/score-viewer      (giữ nguyên)
docs + bookvn-pdf-analysis.md   docs + bookvn-pdf-analysis.md (giữ nguyên)
catalog/delivery/source        catalog/delivery/source      (local inputs)
config/reviews/state/media     config/reviews/state/media   (local inputs)
.secrets/.venv/logs/tmp         .secrets/.venv/logs/tmp       (local-only)
AGENTS/SETUP/.gitignore         cập nhật + .gitattributes
                               README/PROJECT/.env.example
                               config/r2.example.json
                               docs/ROADMAP/TASKS
                               docs/repository-{audit,structure}.md
                               .git (main, origin theo yêu cầu)
```

**Files moved: 0; files deleted: 0.** Không rewrite module hoặc đổi runtime paths, imports, assetId/objectKey/schema/production URL. AudioTP giữ tên ứng dụng; THEOLOI là hệ sinh thái/monorepo. Không tạo packages/apps rỗng.

Inventory ban đầu (bỏ qua dependency/cache `.venv`, `node_modules`, `target`, `.wrangler`, `__pycache__`, `.secrets`; chỉ đếm tên/size, không đọc credential): media 983 file / 2,506,137,889 bytes; source snapshots 2 file / 479,926 bytes; catalog 2 file / 1,279,084 bytes; delivery 4 file / 1,062,555 bytes; scripts 33 file; tests 14 file; benchmarks 49 file / 6,452,374 bytes; docs 31 file; apps 73 file và workers 14 file gồm source/evidence/generated metadata. Tmp có 2,963 file / 265,112,253 bytes; giữ nguyên, không dọn xóa.

## Phân loại / quyết định publish

| Nhóm | Quyết định |
|---|---|
| Windows web/Tauri, Worker source, pipeline, tests | Version control, paths giữ nguyên |
| JSON schemas, package lockfiles, build config/types | Version control; không chứa credential |
| Benchmark score PDF/raster/vector | Tự tạo từ fixture.py; giữ source + fixtures, không phải BookVN |
| PDF.js/Noto vendor | Có license Apache-2.0/OFL và provenance; staged bytes khớp hash |
| Ba WAV fixtures, icons, ba ảnh UI Nghe nhanh | Tự tạo; không thuộc 983 media, WAV không được dùng làm fallback audio thật |
| WATV/BookVN snapshots | Local-only; không mặc định có quyền phân phối snapshot |
| Production catalog/delivery/sheet mapping và projections | Local-only; có origin URLs, metadata nguồn/đường dẫn vận hành, giữ riêng với source |
| config/r2.json | Local-only, có thông tin account; commit template placeholder thay thế |
| Reviews/SQLite/WAL/SHM/lock/session | Local runtime/decision store; không publish |
| .secrets/env/dependencies/tmp/logs/media/build/installer | Ignore; không xóa local |
| Raw browser evidence | Ignore vì có thể chứa trang bên thứ ba/URL session; chỉ giữ ba ảnh UI tự tạo đã kiểm tra |
| Docs lịch sử | Giữ, không di chuyển/xóa; hai báo cáo account-specific bị ignore |

Không ignore mù toàn bộ source/config/state/reviews. Chỉ các nhóm dữ liệu/snapshot/session cụ thể bị loại. Hai báo cáo local-only: `docs/r2-setup-report.md`, `docs/superpowers/plans/2026-10-11-r2-b9.md`; chúng chứa account identifiers và vẫn nguyên vẹn trên máy. Báo cáo P0–P4/redesign là ledger lịch sử; các ghi chú cũ về sidebar/quick chưa khả dụng được cập nhật bởi báo cáo Nghe nhanh. Không coi file cũ là rác.

## Security / copyright audit

Không có Git history trước init, không có nested Git repository trong các module đã kiểm kê; không có lịch sử local cũ để rewrite hoặc cần purge. Remote fetch thành công và không trả refs/commit tại lần kiểm tra đầu. Không force/reset hoặc xóa history.

Audit trên index thật trước commit: danh sách path/size/hash, forbidden-path check, binary review, private-key/session/signed-URL/account-email patterns và **Gitleaks 8.30.1** với redact=100. Lần scan hợp lệ đã đọc khoảng **5.1 MB text**, **0 leaks**; lần đầu scanner không đọc được Git do ownership đã bị loại khỏi bằng chứng PASS. Initial exact index: **178 file / 8,448,043 bytes**, **0 forbidden paths / 0 content findings**, 23 binary đã review, binary lớn nhất 569,208 bytes. Số cuối cùng có thể tăng do chính báo cáo/tài liệu audit được stage; kết quả cuối nằm trong local evidence và phải kiểm tra lại sau restage.

Final pre-commit restage: **179 file**, zero forbidden paths/content findings; Gitleaks đọc **5.11 MB**, zero leaks. `git diff --cached --check` có 8 cảnh báo whitespace/blank-EOF đã tồn tại trong 4 file cũ (2 docs, một helper preview và generated Worker types). Không format source/types không liên quan chỉ để xóa cảnh báo; ghi nhận WARN này riêng, không coi lệnh đó PASS hoặc lỗi runtime do refactor.

Không đưa 983 M4A, BookVN PNG/PDF, credential, cookie, session, account config, production datasets hoặc raw website screenshots vào commit. Kiểm tra bytes staged của licensed vendor/fixtures khớp provenance; review độc lập không có blocking finding. Thêm ignore guard cho cookie/session/HTML snapshot tương lai; không dùng allowlist rộng để bỏ qua secret findings.

Repo visibility chưa xác minh được bằng UI: API anonymous trả 404, trong khi authenticated Git fetch thành công. Điều đó phù hợp repo private nhưng không được coi là xác nhận visibility. Áp dụng cùng tiêu chuẩn source-only có thể công khai; không dùng Private làm sự cho phép phân phối nội dung bên thứ ba. Không thêm license cho toàn bộ source thay chủ sở hữu.

## Validation sau chuẩn hóa

| Kiểm tra | Kết quả thực tế |
|---|---|
| Python unittest discover | 169 tổng: **167 PASS / 0 FAIL / 2 SKIP**, 103.567s |
| Frontend Node | **37 PASS / 0 FAIL / 0 SKIP** |
| Worker Node | **15 PASS / 0 FAIL / 0 SKIP**; mock/local workerd + HTTP integration |
| Benchmark Node metrics | **1 test-file PASS** (assertions trong file), không diễn giải thành số case khác |
| Wrangler dry-run bundle / TS typecheck | **PASS**, exit 0/0, không deploy; telemetry tắt theo tiến trình |
| Catalog validator | **PASS**: 480 main + 5 appendix, 485 guide/485 instrumental/13 silent, tổng 983 |
| Delivery validator | **PASS**: 983 unique SHA/objectKeys; 0 missing/duplicate/hash mismatch/invalid; 12 warning assets đã có |
| Media before/after | 983 file / 2,506,137,889 bytes, toàn bộ size/SHA đúng manifest; xem integrity-after local report |
| Input/state hash | **18/18 SHA giữ nguyên**, gồm metadata và SQLite/WAL/SHM; integrity-after không có changedMetadata |
| Browser UI smoke mới | **BLOCKED**: browser inventory rỗng; không dùng kết quả phiên trước để báo PASS mới |
| Local playback mapping | **PASS HTTP**: full SHA/HEAD/Range đúng guide/instrumental/silent; ba nhóm 485/485/13 |
| Windows native preflight | **BLOCKED**: thiếu cargo/rustc/MSVC x64/Windows SDK; Node/npm/Tauri/WebView2 có; không build EXE |
| R2/B10/live deployment | **NOT RUN**, ngoài phạm vi |

Hai Python SKIP: Windows không cho tạo symlink trong hai bài test traversal. Không gọi SKIP là PASS. HTTP tests kiểm tra file thật nhưng không chứng minh âm thanh người dùng nghe hoặc UI Chrome hiện tại; browser đang chờ người dùng kết nối lại extension.

Các lệnh thật đã dùng (full regression cần private inputs theo SETUP):

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
npm.cmd test --prefix apps/windows
npm.cmd run check --prefix workers/media-api
npm.cmd test --prefix workers/media-api
npm.cmd run typecheck --prefix workers/media-api
node --test benchmarks/score-viewer/metrics.test.mjs
.\.venv\Scripts\python.exe -X utf8 scripts/validate-catalog.py
.\.venv\Scripts\python.exe -X utf8 scripts/validate-delivery.py
.\.venv\Scripts\python.exe -X utf8 scripts/build-windows.py --check
gitleaks git --pre-commit --staged --redact=100 --no-banner .
```

## Hash dữ liệu gốc

| File | SHA-256 baseline |
|---|---|
| catalog/catalog.vi.json | e449b3a25ed49c6879bf06c72219863857632491f4a2ca424c2bc692e45ca8d4 |
| delivery/manifest.vi.json | b54965fd3c612439ba2ef503bd502abbab11fadcd6b1e16857c2ef0403051a4c |
| source/snapshots/watv-vi-2026-10-10.audio.json | febb88a7aa08ada4bac3abb78176112ce3a35c42673f100771dfb15ecfe8ac97 |
| source/snapshots/bookvn-vi-2026-10-12.sheets.json | 6d1eb5e44446fa67e3d2d04989c84ad34be8474916375e7d4accb1a7dd725307 |
| catalog/sheet-sources.vi.json | 7c1376ada16f6d66d8d93527c4bc4ac0996f23199e754e5bcf3a10cbb317a15e |

SHA là integrity evidence, không phải quyền phân phối. Toàn bộ per-file original/state hashes và test logs giữ ở ignored `logs/repository-audit/`, không đưa credential hoặc file dữ liệu lên Git.

## Git / giới hạn vận hành

Branch `main`, remote `https://github.com/ctcm251010/theoloi.git`. **Push source thành công**: commit `4dd8065fb6322a0c828fe9e3969db414b0a53d35` (`chore(repo): organize Theoloi monorepo and initialize project`), 179 files / 8,460,135 staged bytes. `git ls-remote origin refs/heads/main` đã trả đúng SHA bằng local HEAD, không suy từ fetch. Không force-push. Follow-up documentation commit ghi nhận kết quả sau source publication; SHA cuối cùng trong báo cáo bàn giao.

[Repository](https://github.com/ctcm251010/theoloi) · [Source commit đã verify](https://github.com/ctcm251010/theoloi/commit/4dd8065fb6322a0c828fe9e3969db414b0a53d35).

Git init trong sandbox tạo owner .git khác chủ workspace; scoped Git override chỉ tin đúng đường dẫn cho tiến trình hiện tại, không global safe.directory. Auto-review đã từ chối đổi owner vì chưa có explicit approval; không đổi ACL/owner. Nếu user chưa cho phép sửa owner, lệnh Git có thể cần `git -c safe.directory=D:/Workspace/AudioTP ...` trên checkout này; clone mới bình thường không bị vấn đề đó. Đây là trở ngại tool, không phải secret hoặc hỏng history.

Không đọc credential hoặc thay auth; Git fetch dùng cơ chế credential sẵn có mà không xuất giá trị. Không cài thêm GitHub CLI/toolchain. Roadmap tiếp: user-run B10, quyền serving, Worker live, native build/installer và sheet review. Không bắt đầu các milestone đó trong nhiệm vụ repository.
