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
- Artifact SHA và hướng dẫn khớp; Gitleaks stage/index/history0 finding. Index có ba WAV tự tạo dùng test đã tồn tại, không đổi và không nằm trong payload EXE; không có audio WATV/media/state/credential bị commit.
- Đọc SHA/size983 media/2,506,137,889 bytes:0 mismatch;18 metadata/state so baseline:0 thay đổi. Không R2 object mutation, B10 hoặc tải thêm audio.
- Portable đã được mở từ TEMP ngoài workspace với PATH chỉSystem32; process Responding/titleAudioTP. Đây là kiểm tra khởi động, không xác nhận thao tác phát native trên chính1.0.0.
- Clone sạch tại tagv1.0.0: frontend60 PASS, Worker22 PASS/3 private-input SKIP, typecheck PASS. Không thêm generated production JSON vào source để làm tests pass.

## Hợp nhất và tag đã hoàn tất

- [PR#1](https://github.com/ctcm251010/theoloi/pull/1) MERGED:6158cf9ef062af0f93a19e8210ab0358f58c0f7e.
- [PR#2](https://github.com/ctcm251010/theoloi/pull/2) MERGED:0f49c91925f676b3ace8c31ab86f5321099c51d0.
- Release sourcec783ad96f4ef4288c8e03ec76d90d120ea900282; merged tree khớp toàn bộ source branch đã build/test. Frontend trên main60 PASS sau merge.
- Annotated tagv1.0.0 trỏ tới main0f49c91925f676b3ace8c31ab86f5321099c51d0; đã push và đối chiếu remote SHA, không force/update tag. Mọi ledger docs sau đó không đổi runtime artifact.

## Publish — BLOCKED bởi quyền upload Chrome

Đã lưu [draft Release](https://github.com/ctcm251010/theoloi/releases/edit/untagged-ae2bbccf5c6bc54257e1) với tagv1.0.0/title/notes. Chưa publish và chưa đính kèm binaries. Browser Use file chooser trả lỗi extension thiếu **Allow access to file URLs**; người dùng cần tự bật quyền trong chrome://extensions hoặc tự upload bốn file đã chuẩn bị. Không tự đổi quyền extension, không đọc/export GitHub token và không dùng cách khác để vượt giới hạn này. Đây là lỗi capability upload, không phải secret scan hoặc auto-review rejection.

## Artifact

Folder local `release/windows/1.0.0-20261013T045937886373Z/`.

| File | Bytes | SHA-256 |
|---|---:|---|
| AudioTP.exe |3188736|378fa640a4d8e44804e9a64586feffe4686236f779d43de379bcced1a1a7987a|
| AudioTP_1.0.0_x64-setup.exe |1161480|62ede148f31c178e2d4f69cc57ef7843a6f3ae25536ed60faf134566a15e444b|

Payload GitHub chỉ gồm hai EXE trên, `SHA256SUMS.txt` và `HUONG-DAN.md`. Không upload build-report nội bộ, media, source snapshots hoặc thông tin đăng nhập. Release notes tại [v1.0.0](releases/v1.0.0.md); repository ctcm251010/theoloi hiện private và không đổi visibility.

## Còn chờ nghiệm thu

Merge/tag đã đối chiếu URL/SHA; publish còn chờ quyền upload. Chưa dùng số phiên bản để đánh dấu toàn bộ Phase01/02 DONE. Cần thử trên máy khác: cài/gỡ ONLINE/WebView2 bootstrap, native Play/pause/seek/queue/logout trên1.0.0, mất mạng/reconnect và formal Range/R2 metadata. Chưa ký Authenticode hoặc hỗ trợ updater. Không có quyền phát hành thư viện rộng rãi được suy ra từ việc đưa EXE lên Release private.
