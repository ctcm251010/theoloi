# AudioTP Windows 0.2

**Đã bỏ WAV demo khỏi luồng nghe.** Mỗi bài lấy nguồn theo assetId qua API, không fallback theo tên tab. Đã thử M4A thật qua local integration; chưa có EXE đã build hoặc live R2 E2E.

## Nghe đúng audio đang có trên máy

```powershell
cd D:\Workspace\AudioTP
node workers/media-api/local-preview.mjs
```

Mở **http://127.0.0.1:8766/**. Hoặc command cũ:

```powershell
.\.venv\Scripts\python.exe -X utf8 apps/windows/serve.py
```

Python command nay gọi Node adapter với cùng handler Worker, đọc M4A từ manifest, kiểm tra size/SHA và stream có Range. Không tải thêm, upload R2 hoặc thay media/state. Nếu cổng đang chạy, mở trang thay vì khởi động thêm. Ctrl+C dừng helper ở PowerShell của bạn. Có thể dùng `--port 8767` khi cổng bận.

Preview này cần Node/workspace/media trên máy phát triển; **ứng dụng đã build kết nối Worker sau này không cần các thứ đó**. `serve.py --static` chỉ xem catalog, không phát âm thay thế.

## Giao diện

Giao diện thu gọn: header, điều hướng ngang, tìm kiếm và danh sách, không hiện thống kê. **Nghe nhanh** nằm ngay dưới ba tab; **Cài đặt** chứa theme/kết nối; **Bộ lọc** chứa chủ đề/phần danh mục; dấu **…** ở player chứa chế độ phát. [Báo cáo Nghe nhanh và kiểm thử](../../docs/quick-listening-report.md).

Ba tab riêng: **485 Hướng dẫn / 485 Nhạc đệm / 13 Nhạc ngẫm nghĩ**. Tìm không dấu, số thật hoặc `PL 1`, lọc chủ đề/nhóm, yêu thích/lịch sử, sáng/tối. Đổi tab giữ bài/queue đang phát. Nghe nhanh → Nhạc ngẫm nghĩ mở tab tương ứng và bắt đầu bằng asset `watv:vi:silent:19977` từ thứ tự snapshot; bấm lại để tạm dừng/phát tiếp. Hai mục cầu nguyện khóa vì chưa có file được nhập/xác minh. Có từ khóa sẽ ẩn Nghe nhanh; thu gọn thủ công được nhớ trên máy.

Một player: Play/Pause, tua, volume/mute, trước/sau, repeat/shuffle/continuous; loading/buffering/error và retry giữ vị trí. Space phát/dừng, ←/→ tua 5 giây, N/P đổi bài, M mute khi không nhập liệu. Tabs có ←/→, Home/End. Lịch sử demo cũ không được tính như nghe thật; yêu thích/theme được giữ.

App không lưu mã truy cập/session/ticket vào localStorage. Audio disk cache tắt, không prefetch cả thư viện. Player dùng URL vé ngắn hạn để thẻ audio hỗ trợ Range mà không cần Bearer header.

## API và test

[Worker README: source, xác thực, test, deploy user-run](../../workers/media-api/README.md). Worker private R2 chưa deploy; mặc định serving disabled. Không có R2 access key trong frontend.

```powershell
cd D:\Workspace\AudioTP\apps\windows
npm.cmd test
```

Test backend cần `npm.cmd run check` trước `npm.cmd test` trong folder Worker. Lệnh, kết quả mock/local/runtime và giới hạn: [báo cáo P0–P4](../../docs/autonomous-implementation-report.md). Không chạy live B10/deploy trong Codex.

## Build Windows

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 scripts/build-windows.py --check
```

Máy hiện thiếu Rust/Cargo, MSVC và Windows SDK; WebView2 có sẵn. Exit 2 của preflight nghĩa cần cài dependency. Theo [Tauri prerequisites](https://tauri.app/start/prerequisites/), cài C++ Build Tools với **Desktop development with C++** và Windows SDK. Rust: `winget install --id Rustlang.Rustup`, sau đó mở terminal mới và `rustup default stable-msvc`. Các cài đặt hệ thống do người dùng tự thực hiện.

Sau khi đủ toolchain và có HTTPS Worker đã deploy:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build-windows.py --build --api-base (Read-Host 'HTTPS URL Worker đã deploy') --installer
```

Builder stage web assets **không có WAV/demo/audio local**, cấu hình API/CSP, test rồi build. Chỉ khi có binary thật mới tạo `release/windows/0.2.0-<timestamp>/` với EXE/installer, hướng dẫn và SHA. Config Tauri được khôi phục sau build kể cả lỗi. Lệnh `npm.cmd run build` trực tiếp vẫn dùng được để compile source chưa cấu hình production; đây không phải bản phát hành đã kiểm thử.

Portable EXE cần WebView2; NSIS có bootstrapper khi thiếu runtime. Người nhận không cần Python/Node/FFmpeg/source/M4A local. **Chưa xác minh native build, installer, máy sạch, dung lượng/RAM, Authenticode hoặc live E2E**; không gọi source hiện tại là app production hoàn tất. CLI 2.12.2 được lock, Cargo.lock chờ build đầu.

[Hướng dẫn người dùng cuối](../../docs/windows-user-guide.vi.md) · [Khảo sát WATV](../../docs/watv-player-ui-analysis.md) · [Báo cáo hiện hành](../../docs/autonomous-implementation-report.md)
