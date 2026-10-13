# Phase02 — Live R2 API và Windows online

Thực hiện nối tiếp trên `phase/02-windows-installer`; không merge Phase01 hoặc chuyển Phase03.

Người dùng đã duyệt bốn bước: triển khai API private, build bản Windows dùng HTTPS thật, bàn giao installer, kiểm tra phát trên máy đích với mã truy cập riêng. Account đích là `ctcm251010`; người thao tác là `nguyenducbang.uit`. Không đổi bucket thành public, subscription, dữ liệu audio hoặc credential R2.

## 1. Preflight và API

- [x] Toolchain Windows đã có; không cần tải thêm phần mềm trước bước này.
- [x] Đối chiếu account dashboard với config R2 local không bí mật: bucket `audiotp-media`, Public Access Disabled, 2.51 GB hiển thị.
- [x] Member `nguyenducbang.uit` đã Active; policy hiển thị quyền quản trị. Không gửi lại lời mời hoặc tăng quyền.
- [x] Phát hiện OAuth Wrangler cũ chỉ thấy account khác. Mở xác thực lại bằng scope hiện có, chọn riêng account đích; người dùng tự Authorize.
- [x] Helper secrets yêu cầu account ID rõ ràng, xác minh membership trước input/ghi secret; sáu test mock PASS, dry-run không network.
- [x] Người dùng hoàn tất OAuth; `whoami --json` thấy đúng account đích, login `nguyenducbang.uit` và bốn scope đã review.

Preflight 13/10: OAuth đầu hết thời gian chờ; lần mở lại bị callback/state không khớp, Wrangler từ chối lưu phiên. Không bỏ kiểm tra state hoặc đọc token. Chuyển bước login sang PowerShell người dùng để chỉ có một flow và họ tự chọn account/Authorize. CLI read-only cuối cùng vẫn chỉ thấy account cũ; chưa deploy. Regression sau account guard: Python191 total,188 PASS/3 symlink SKIP; `git diff --check` PASS. Log offline tại `logs/repository-audit/phase02-live-preflight-python.txt`.

Cập nhật tiếp theo: user-run OAuth đã thành công; browser báo “Authorization granted to Wrangler”, CLI xác minh đúng login và account. Read-only `deployments list --name audiotp-media-api` ở account đích trả10007 (Worker chưa tồn tại), không phải lỗi quyền hoặc một deployment đã tạo. Chưa cấu hình secret/deploy. Bước kế tiếp: người dùng chạy helper tương tác để tự đặt mã nhóm mới; helper tạo signing key và gửi hash/key qua stdin, không dùng R2 credentials.

Dashboard Workers plans xác minh **Free / Current plan**; không bấm Upgrade hoặc thay subscription. `prepare-worker.py` xác minh983 IDs/keys và giữ nguyên source catalog/manifest. Wrangler dry-run bundle542.79KiB/gzip97.95KiB, bindingMEDIA đúng bucket, serving vẫn false; log `logs/repository-audit/phase02-live-worker-dry-run.txt`. Chưa phải deploy hoặc nghiệm thu CPU/streaming live.
- [x] Worker name/version và Free plan đã kiểm tra; pin account ID cho mọi lệnh. Giữ hai namespace ID đã review của project; chưa inventory namespace của toàn bộ Worker khác trong account.
- [x] Người dùng nhập group code ẩn bằng helper; không gửi code qua chat hoặc đóng gói trong app.
- [x] Deploy đầu giữ serving tắt; lưu URL/version thực và kiểm tra khóa phục vụ. Sau đó bật authenticated serving theo phê duyệt.
- [ ] Live smoke nhỏ: auth, origin, catalog485/485/13, HEAD và Range của ba đại diện. Không tải toàn kho hoặc chạy lại B10.

## 2. Windows online

- [x] Build EXE/NSIS bằng `scripts/build-windows.py --build --installer --api-base` với URL HTTPS deploy thật, không dùng LOCAL/TEST flags.
- [x] Kiểm tra stage983 asset ID/0 test IDs/0 media, PE/hash và startup TEMP/PATH chỉ System32.

## 3. Installer và máy đích

- [x] Bàn giao installer/hash/hướng dẫn WebView2; không yêu cầu Node/Python/thư viện local trên máy đích.
- [ ] Native cài/gỡ/startup và phát thực tế; báo rõ phần cần người dùng nghiệm thu khi công cụ không expose native UI.

## 4. Access và nghiệm thu

- [ ] Mã nhóm trao riêng qua kênh người quản lý; nhập lúc chạy, chỉ giữ RAM.
- [ ] Kiểm tra nghe/pause/seek/resume, đổi variant/tab, lỗi mạng và khởi động lại trên máy đích.
- [x] Roadmap/report/secret scan/integrity/Git; source đã push. Giữ Phase01 formal live checks và Phase02 target acceptance pending khi chưa kiểm tra.

## Bổ sung được người dùng duyệt — Nhớ đăng nhập

- [x] DPAPI current-user + exact HTTPS origin; native main-window guard, không plaintext/localStorage hoặc credential trong EXE.
- [x] Startup/session-loss restore có cancellation, checkbox/logout tôn trọng ý định; fail-safe errors không retry vô hạn.
- [x] Reviewer tìm ra stale staging sau crash; RED test, OS cross-process lock/recovery/logout cleanup, native subprocess tests và re-review PASS.
- [x] Frontend58, Worker24/typecheck, Python188 PASS/3 SKIP, Rust5 PASS + helper chạy2 lần;983 media/18 metadata giữ nguyên.
- [ ] Người dùng kiểm tra native login/Play/seek/remember restart/logout. Không dùng unit/DPAPI/startup để thay UI acceptance.

User đã xác nhận bản ONLINE đầu hoạt động và tự kết nối sau restart. Formal Range/metadata trực tiếp và installer/máy đích vẫn pending. Bản cuối040214 bổ sung first-connect prompt theo feedback, frontend59 PASS/targeted review sạch; artifact/stage hashes đã kiểm tra.

Chi tiết artifact/bằng chứng tại [báo cáo ONLINE](../../phase02-online-beta.md).
