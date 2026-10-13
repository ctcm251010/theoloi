# AudioTP1.0.0 — Review, hợp nhất và phát hành nội bộ

Ngày13/10/2026, Asia/Bangkok. Người dùng xác nhận bản ONLINE/mã ngắn thử ổn, yêu cầu review/hợp nhất source và đưa bản1.0 lên GitHub. Đây là phạm vi phát hành1.0.0 riêng; không tự triển khai updater/Closed Beta, đổi Cloudflare, credential hoặc quyền nội dung.

## Review và nguồn

- Phase01 `ef7f50d..637fbd1` và Worker/client hiện tại được review độc lập: không Critical/Important;53 targeted tests/typecheck PASS. PR#1 đã merge vào main tại6158cf9.
- Phase02 `637fbd1..aa64bd1`: review độc lập native IPC/navigation, DPAPI/locking/logout, frontend cancellation và packaging/CSP; không Critical/Important. Review không thay nghiệm thu live hoặc máy sạch.
- Release branch `release/1.0.0`: chỉ nâng metadata app/npm/Cargo/lock/Tauri/default UI lên1.0.0 và tài liệu. Giữ nguyên identifierorg.audiotp.desktop, dependency, endpoint HTTPS đã duyệt, player/ba tab/Nghe nhanh. Worker không redeploy trong đợt phát hành này.
- `.env.example` đang có sửa riêng của người dùng, không đọc nội dung/stage/commit/revert. Operational data, credential và artifact không commit vào source.

## Kiểm thử và bảo toàn

- Python193 total:190 PASS/3 symlink SKIP. Frontend60 PASS. Worker25 PASS/typecheck PASS. Rust6 PASS;1 child helper ignored trong run chính nhưng parent chạy hai lần và PASS. Rustfmt PASS.
- Build release/NSIS exit0; PE/FileVersion/ProductVersion1.0.0. Stage983 ID thật,485/485/13,0 test ID,0 media/PDF/SQLite/env; source stage khớp files đã test.
- Artifact SHA và hướng dẫn khớp; Gitleaks stage0 finding. Kiểm tra index/history sẽ hoàn tất trước push.
- Đọc SHA/size983 media/2,506,137,889 bytes:0 mismatch;18 metadata/state so baseline:0 thay đổi. Không R2 object mutation, B10 hoặc tải thêm audio.
- Portable đã được mở từ TEMP ngoài workspace với PATH chỉSystem32; đây là kiểm tra khởi động, không xác nhận thao tác phát native trên chính1.0.0.

## Artifact

Folder local `release/windows/1.0.0-20261013T045937886373Z/`.

| File | Bytes | SHA-256 |
|---|---:|---|
| AudioTP.exe |3188736|378fa640a4d8e44804e9a64586feffe4686236f779d43de379bcced1a1a7987a|
| AudioTP_1.0.0_x64-setup.exe |1161480|62ede148f31c178e2d4f69cc57ef7843a6f3ae25536ed60faf134566a15e444b|

Payload GitHub chỉ gồm hai EXE trên, `SHA256SUMS.txt` và `HUONG-DAN.md`. Không upload build-report nội bộ, media, source snapshots hoặc thông tin đăng nhập. Release notes tại [v1.0.0](releases/v1.0.0.md); repository ctcm251010/theoloi hiện private và không đổi visibility.

## Còn chờ nghiệm thu

Merge/publish sẽ được đối chiếu URL/SHA sau hoàn tất; chưa dùng số phiên bản để đánh dấu toàn bộ Phase01/02 DONE. Cần thử trên máy khác: cài/gỡ ONLINE/WebView2 bootstrap, native Play/pause/seek/queue/logout trên1.0.0, mất mạng/reconnect và formal Range/R2 metadata. Chưa ký Authenticode hoặc hỗ trợ updater. Không có quyền phát hành thư viện rộng rãi được suy ra từ việc đưa EXE lên Release private.
