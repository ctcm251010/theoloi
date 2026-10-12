# AudioTP — R2 audit preflight và Mapping Review

Ngày 12/10/2026. A/B đã triển khai và kiểm thử offline; C chỉ báo cáo kiến trúc. Không có live B10, R2 request, credential read, audio modification, BookVN media download hoặc decision approve thật.

## A — B10

`verify-r2.py` đã có test inventory/pagination, HEAD/checks, duplicate/missing/extra, 403/429/5xx/retry/interruption/report/SDK operation guard. Đã sửa duplicate expected identity, malformed HEAD response và report bị mất khi cleanup lỗi. Không thêm PUT/DELETE/COPY/GET, không mở upload SQLite. Import module uploader chỉ để tái sử dụng loader/client/error codes; không khởi tạo UploadRunner/UploadState.

**B10 remote chưa chạy, chưa thể tuyên bố remote PASS.** Người dùng chạy PowerShell ngoài Codex:

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 scripts\verify-r2.py --workers 2
$LASTEXITCODE
```

Không cần activate hoặc cài dependency mới. Giữ uploader dừng khi audit. Script tự đọc credential khi **người dùng** chạy; Codex không đọc/in credential trong bước chuẩn bị. SHA-256 chỉ so custom metadata với manifest, không hash remote body; report luôn contentSha256Verified=false. Xem [B10 verification](r2-verification.md) để mở report mới nhất và xử lý FAIL; không tự sửa/xóa/upload object nếu mismatch.

## B — Review

Catalog vẫn **542 nguồn / 489 candidate / 1 conflict / 52 unmatched**. Store mới rỗng, **0 events / 0 verified**; không ra quyết định hộ người dùng. Queue ưu tiên main464 `bookvn:vi:post:77217`, tiếp theo 10 nguồn trong năm cặp phụ lục; vẫn cần kiểm tra âm nhạc/ấn bản thực tế.

CLI/UI hướng dẫn: [Mapping Review](mapping-review.md). Lệnh mở đầu:

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 scripts\review-mapping.py status
.\.venv\Scripts\python.exe -X utf8 scripts\review-mapping.py html
```

Tự mở `reviews/sheet-review.html` qua File Explorer. Đây là UI offline tạo đề xuất, không phải HTTP server/store writer. Browser Use chặn `file:` nên chưa có kiểm chứng render thực; parser/JSON escaping và JavaScript batch constructor đã chạy offline. Không mở gián tiếp để né browser policy.

Approve/reject/defer có evidence/provenance, exact IDs, history/hash/revision và stale identity detection. Batch tối đa 50, dry-run mặc định; apply yêu cầu reviewed=true cho từng mục + confirm-count đúng. Export riêng `delivery/sheet-verified-mapping.vi.json`, hiện 0 links, không phải quyền phục vụ file. Không sửa catalog hoặc đổi restricted thành confirmed. Khi review xong phải export lại; API tương lai kiểm tra revision/pins và rights riêng.

## C — EXE

Đề xuất Tauri2 + WebView2 Evergreen, installer ký mã, private R2 qua authenticated Worker với asset-scoped play ticket và Range/HEAD streaming, cache có giới hạn, không nhúng R2 credential. Cần benchmark prototype trước khi chốt dung lượng thực tế; WPF/.NET và Electron được so sánh trong [báo cáo kiến trúc Windows](windows-app-architecture.md). Chưa phát triển app/Worker/API, chưa deploy, public bucket hoặc cấp quyền phân phối.

## Kiểm thử và review

**Toàn bộ test offline: 129 test, 128 PASS, 0 FAIL, 1 SKIP; 70.108 giây, exit 0.** Log: `tmp/review-final-full-tests.log`. Test bị SKIP là `test_delivery.DeliveryTests.test_redirected_file_is_rejected` vì tài khoản Windows không có quyền tạo file symlink; không thay đổi quyền máy. Các test junction vẫn PASS.

Hai module mới có **26 test PASS**: 12 audit (`tmp/review-b10-final-green.log`) và 14 review (`tmp/review-mapping-final-green.log`). Review độc lập phát hiện hai lỗi đã được tái hiện RED rồi sửa GREEN: ETag sai kiểu có thể bị coi là khớp; approve A → defer A → approve B có thể bỏ qua yêu cầu reject A. Verifier hiện yêu cầu ETag chuỗi không rỗng; lịch sử review yêu cầu reject rõ ràng trước khi đổi bài đã approve. Không còn finding chưa xử lý trong phạm vi review này.

Đã kiểm thử lock với writer cạnh tranh và ngắt ngay trước atomic replace: store giữ nguyên, writer kế tiếp hoạt động. Đây không phải mô phỏng mất điện; cần backup decision store sau các đợt review. Hash chain giúp phát hiện thay đổi lịch sử, không chứng minh người review hay quyền sử dụng.

Đối chiếu SHA-256 cuối xác nhận audio catalog, audio delivery manifest, sheet catalog, snapshot BookVN và config R2 không đổi. Chạy lại sheet validation PASS; store vẫn **0 events / 0 verified**, export **0 links** và HTML/queue 542 nguồn. Không có synthetic approvals trong store/catalog thật.

Giới hạn bàn giao: chưa có remote verdict B10; xác minh tác phẩm/ấn bản/quyền sử dụng vẫn cần người dùng; UI chưa kiểm chứng render/tải proposal bằng trình duyệt thật do browser policy; kiến trúc EXE chưa benchmark hoặc triển khai. Không có tải tài liệu BookVN hay thay đổi quyền restricted.

## File tạo/sửa

Tạo: `tests/test_verify_r2.py`, `tests/test_sheet_review.py`; `scripts/sheet_review.py`, `scripts/review-mapping.py`, `scripts/sheet_review_html.py`, `scripts/sheet-review-ui.js`; `schemas/sheet-review.schema.json`; `reviews/sheet-mapping-decisions.vi.json`, `reviews/sheet-review-queue.vi.json`, `reviews/sheet-review.html`; `delivery/sheet-verified-mapping.vi.json`; `docs/mapping-review.md`, `docs/windows-app-architecture.md`, `docs/audit-mapping-handoff.md`; `docs/superpowers/specs/2026-10-12-audit-mapping-review-design.md`, `docs/superpowers/plans/2026-10-12-audit-mapping-review.md`.

Sửa: `scripts/verify-r2.py`, `docs/r2-verification.md`, `.gitignore`, `docs/sheets-windows.md`, `docs/sheet-implementation-report.md`. Không sửa source/catalog/manifest audio, catalog sheet, source BookVN, config R2, uploader/transfer state hoặc credentials. HTML/queue/lock/proposal/log là artifact local được ignore; decision store/export là dữ liệu review riêng để backup/versioning.

## Bước tiếp theo

Người dùng chạy live B10 và tự review những cặp ưu tiên, gửi summary/issue không chứa secret. Sau đó review policy/quyền phục vụ và API contract, prototype desktop bằng dữ liệu tự tạo, chỉ tiến tới staging Cloudflare/EXE beta khi được duyệt riêng. Nguồn PDF/quyền sử dụng BookVN vẫn chưa được xác minh; không có downloader hay tài liệu BookVN được nhập trong bước này.
