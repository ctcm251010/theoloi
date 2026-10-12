# AudioTP 0.2 — Minimal Music Player

**Cập nhật tiếp theo:** ba mục Nghe nhanh đã chuyển xuống dưới tabs; shortcut silent hoạt động, hai mục cầu nguyện vẫn khóa. Xem [báo cáo hiện hành](quick-listening-report.md). Các mô tả Cài đặt/hai mục nhanh bên dưới là kết quả trước cập nhật này.

Ngày thực hiện: 12/10/2026, Asia/Bangkok. Hoàn tất UI và kiểm thử local. Native EXE build còn bị chặn bởi toolchain.

## Thay đổi

- Header chỉ có AudioTP và Cài đặt; điều hướng ngang Thư viện / Yêu thích / Gần đây. Bỏ sidebar, slogan, banner, phiên bản và thống kê khỏi giao diện chính.
- Ô “Tìm số hoặc tên bài ca...” và ba tab Hướng dẫn / Nhạc đệm / Ngẫm nghĩ không kèm số lượng. Dữ liệu vẫn 485 / 485 / 13, giữ nguyên namespace/asset ID.
- Danh sách: số bài, nút phát, tên, thời lượng và yêu thích. Bỏ cột chủ đề/badge; bài được chọn dùng nền xanh nhẹ. Tên dài có ellipsis desktop, tối đa hai dòng mobile và title đầy đủ.
- Bộ lọc chủ đề/phần danh mục chuyển vào dialog Bộ lọc; clear/reset và tìm kiếm không dấu/`PL 1` được giữ.
- Player cố định giữ tên/số, loại, Previous / Play-Pause / Next, tiến trình/thời gian. Desktop có volume/mute. Menu … chứa yêu thích bài hiện tại, shuffle, repeat và continuous.
- Cài đặt chứa theme, chế độ nghe, kết nối, phiên bản và hai mục nhanh chưa khả dụng. Giữ logic nguồn/quyền, không tạo URL thay thế.
- Không hiện nguồn kỹ thuật khi đã kết nối; khi chưa kết nối có một dòng ngắn và nút Kết nối. Loading/error/retry hiện khi cần.
- Dialog có tên trợ năng, nút đóng, Escape và trả focus về nút mở. Phím tắt nền không can thiệp trong dialog.

Không thêm dependency/framework. Không sửa player, API client, storage, Worker, audio catalog, manifest hoặc media; dùng read-only local adapter hiện có.

## File tạo/sửa

Source: `apps/windows/web/index.html`, `styles.css`, `app.mjs`, `ui-core.mjs`; test: `apps/windows/tests/ui-core.test.mjs`.

Tài liệu: báo cáo này, `apps/windows/README.md`, `docs/windows-user-guide.vi.md`, `docs/autonomous-implementation-report.md`, ledger `docs/superpowers/plans/2026-10-12-windows-mvp.md`.

Bằng chứng: `apps/windows/evidence/minimal-ui-browser.json`, `minimal-ui-frontend-tests.txt`, `minimal-ui-python-tests.txt`, `minimal-ui-protected-check.json` và bốn ảnh JPEG liên kết phía dưới. Không lưu query vé/session. Bản sao HTML/CSS/app trước đổi và capture lỗi nằm trong `tmp/minimal-ui-before/`; `tmp/redesign-ui.py` là script tạo bố cục một lần, không thuộc runtime/release.

## Kết quả kiểm thử

| Hạng mục | Kết quả và phạm vi |
|---|---|
| Frontend suite | **34 PASS, 0 FAIL, 0 SKIP**: API, search/catalog, player/races/error/retry, storage và UI core |
| Python toàn project | **167 tổng: 165 PASS, 0 FAIL, 2 SKIP**, 104,082s; SKIP do quyền tạo symlink trên Windows |
| JS syntax | `node --check` app và UI core: PASS |
| Review độc lập | Không có Critical/Important finding; read-only source/baseline |
| Browser | Chrome extension, profile Bang, tab người dùng `http://127.0.0.1:8766/` |
| Guide | 4177, duration 125,016236s; readyState 4, thời gian tăng; pause/resume/seek 45 và 60s PASS |
| Instrumental | 17407, duration 125,248435s; readyState 4, thời gian tăng; Next bài 2 / Previous bài 1 PASS |
| Silent | 19976, duration 56,958549s; readyState 4, thời gian tăng; phát trên mobile PASS; 13 dòng riêng |
| Chuyển tab khi phát | Giữ nguồn guide khi chọn tab instrumental; chỉ đổi nguồn khi chọn bài; một audio element |
| Search/filter | Không dấu và `PL 1` → đúng một dòng; chuỗi không tồn tại → empty state; phụ lục → 5 dòng; chủ đề Lễ trọng thể → 19 dòng; clear/reset PASS |
| Yêu thích/history | Toggle và các view PASS; favourite thử nghiệm đã trả về trạng thái cũ; history ghi actual playback |
| Menu phát | Bật/tắt ba chế độ và aria-pressed PASS; ended/repeat/continuous/shuffle được suite player kiểm tra |
| Volume/mute | Thao tác slider, mute/unmute desktop PASS; volume thu gọn khi màn hình hẹp |
| Catalog-only | Dừng nguồn, khóa phát; chuyển lại listen phát audio thật PASS |
| Theme | Sáng/tối và giữ lựa chọn qua reload PASS, có ảnh hai chế độ |
| Responsive | CSS viewport thực tế 1745×968, 1745×917, 768×1024, 355×767, 320×640; không cuộn ngang. 355px: player khoảng 154px, main padding-bottom 190px |
| Console | Không error/warn sau reload và lượt phát cuối |
| Native build | **BLOCKED**: thiếu cargo/rustc, MSVC x64 C++ Build Tools, Windows SDK/UCRT. WebView2 và Tauri CLI có sẵn |
| Lint/typecheck frontend | Project không cấu hình script riêng; không giả báo PASS |
| Dữ liệu bảo toàn | SHA-256 audio catalog/manifest/snapshot, sheet catalog và config R2 khớp 5/5 baseline |

Chỉ phát một số file local đại diện. Không download/upload/deploy, chạy live B10 hoặc đọc credential. Error/timeout/retry và race được unit test; không tuyên bố đã gây lỗi mạng live R2 trong lượt UI này. Responsive là Chrome viewport testing, chưa phải thiết bị vật lý hoặc native WebView2.

## Lỗi phát hiện và đã xử lý

1. Phím tắt có thể tác động nền trong dialog: thêm guard và regression test đã quan sát RED → GREEN.
2. Escape chưa đóng dialog trong lượt Browser Use đầu: thêm xử lý Escape; kiểm tra lại open:false và focus đúng nút mở.
3. Dấu ✓ CSS thay đổi tên trợ năng của mode button: thêm aria-label ổn định, bật/tắt lại cả ba nút PASS.
4. Helper local từ phiên trước đã dừng, connection refused: khởi động lại đúng adapter read-only cổng 8766, không đổi audio/cấu hình.
5. Screenshot trả JPEG, capture mobile mặc định bị thu nhỏ theo tỷ lệ desktop: lưu đúng đuôi, dùng viewport clip và kiểm tra ảnh thực tế. Capture không đạt giữ trong tmp.
6. Browser approval ban đầu lỗi 429: chỉ thử lại sau xác nhận của người dùng, đúng tab/profile, không dùng đường vòng.

## Mở và chạy test

Nếu server đang chạy, tải lại **http://127.0.0.1:8766/**. Tab mở từ bản cũ không tự cập nhật module đang ở RAM. Nếu server đã dừng:

```powershell
cd D:\Workspace\AudioTP
node workers/media-api/local-preview.mjs --port 8766
```

Test:

```powershell
cd D:\Workspace\AudioTP\apps\windows
npm.cmd test

cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

## Ảnh

[Desktop tối](../apps/windows/evidence/minimal-ui-desktop-dark.jpg) · [Desktop sáng](../apps/windows/evidence/minimal-ui-desktop-light.jpg) · [Mobile tối 355px](../apps/windows/evidence/minimal-ui-mobile-dark.jpg) · [Mobile sáng 320px](../apps/windows/evidence/minimal-ui-mobile-320.jpg).

## Chưa xác minh

Không còn quyết định UI nhỏ cần người dùng chốt. EXE/installer/native WebView2 vẫn cần toolchain Windows nêu trên; chưa có artifact production mới. Worker live và quyền/nguồn hai mục nhanh giữ blocker cũ, không nằm trong lượt UI này. Chưa kiểm thử máy khác, thiết bị vật lý hoặc người dùng screen reader.
