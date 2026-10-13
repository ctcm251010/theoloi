# AudioTP Windows 0.2

Mỗi bài lấy nguồn theo assetId qua API, không fallback theo tên tab. Phase02 đã build EXE/NSIS **TEST** riêng với âm tự tạo; chưa có bản online production/live R2 E2E được nghiệm thu. Xem [Phase02](../../docs/phases/phase-02.md).

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

Máy phát triển đã READY: Rust/Cargo1.99, MSVC, SDK và WebView2. Máy khác thiếu toolchain: người dùng chạy PowerShell Administrator, theo [Tauri prerequisites](https://tauri.app/start/prerequisites/):

```powershell
winget install --id Microsoft.VisualStudio.2022.BuildTools --exact --source winget --override "--wait --passive --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
winget install --id Rustlang.Rustup --exact --source winget
```

Mở PowerShell mới và chạy `rustup default stable-msvc`. Node/npm và `.venv` theo SETUP chỉ cần trên máy build; cài locked npm dependencies bằng `npm.cmd ci --prefix apps/windows`. Preflight exit2 nghĩa còn thiếu dependency.

### Nghe Bài ca mới thật trên máy hiện tại

Trong workspace đã có đủ 983 audio/manifest và bản LOCAL đã build, mở **`Mo-AudioTP.cmd`** ở root. Launcher kiểm tra SHA-256 EXE, mở backend chỉ đọc và EXE; app tự kết nối, không nhập mã. Giữ ba nhóm485 Hướng dẫn/485 Nhạc đệm/13 Ngẫm nghĩ và assetId thật. Các mục cầu nguyện chưa có nguồn vẫn khóa. Không mở bản TEST để nghe Bài ca mới.

Lệnh tương đương:

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 scripts/start-windows-local.py
```

`--check` chỉ xác minh artifact/hash, không mở app hoặc kết nối mạng. Launcher từ chối cổng bị chương trình khác chiếm, không dừng backend đã có, chặn mở trùng và dừng backend do nó tạo khi EXE đóng. Log chỉ ghi route/status native, không token/query/header.

Bản LOCAL cần Node/Python/workspace/media cho **launcher/backend trên máy này**; EXE dùng WebView2. Chưa phải bản online độc lập workspace hoặc phát từ R2. Nếu mở trực tiếp EXE hay shortcut installer LOCAL, backend phải đang chạy. Ưu tiên `Mo-AudioTP.cmd` để mở đầy đủ.

Build lại khi có private projections hợp lệ:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build-windows.py --build --installer --local-library --api-base http://127.0.0.1:8872
```

Artifact `release/windows/LOCAL-0.2.0-<timestamp>/`, identifier `org.audiotp.local`; không chép M4A vào EXE/installer, không đổi 983 asset gốc. Backend chỉ cho Tauri origins chính xác khi opt-in `--desktop`, bind127.0.0.1; mặc định browser preview giữ giới hạn cũ. `--local-library` và `--test-fixtures` loại trừ nhau; production vẫn yêu cầu HTTPS.

### Thử native với âm tự tạo — dành cho kiểm thử riêng

Không cần private catalogs cho bản TEST. PowerShell thứ nhất, trong root repo:

```powershell
node apps/windows/native-mock.mjs --port 8870
```

PowerShell thứ hai:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build-windows.py --build --debug --test-fixtures --api-base http://127.0.0.1:8870
& '.\apps\windows\src-tauri\target\debug\AudioTP.exe'
```

Trong app: Cài đặt → Kết nối thư viện → mã công khai `public-self-authored-native-test-code` → Kết nối. Tất cả tên bài có TEST, chỉ4 track/3 WAV tự tạo12 giây, không phải nhạc WATV. Session không lưu khi đóng app và mất khi restart mock. Tắt mock bằng Ctrl+C sau thử.

Build release/installer **TEST** bằng command đã chạy thành công:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build-windows.py --build --installer --test-fixtures --api-base http://127.0.0.1:8870
```

Artifact trong `release/windows/TEST-0.2.0-<timestamp>/`. Identifier riêng `org.audiotp.acceptance`, không dùng như bản thư viện thật. Backend TEST cần Node/repo; EXE chỉ cần WebView2 để mở. `--build --debug` không endpoint cho phép kiểm tra native catalog-only nếu private projection đã chuẩn bị; không phát nhạc/kết nối. `--prepare` thay `--build` chỉ stage/config, không compiler/network.

### Production — chỉ sau review và live acceptance

Sau khi có private projections được phép, HTTPS Worker thật đã deploy và nghiệm thu Phase01, dùng:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build-windows.py --build --api-base (Read-Host 'HTTPS URL Worker đã deploy') --installer
```

Builder stage allowlist **không có WAV/media local**, validate metadata, cấu hình API/CSP chính xác origin, test rồi build. Config tracked không bị builder sửa; dùng override riêng. Có binary PE mới/được scan mới tạo release folder với EXE/installer, guide, SHA256SUMS và build-report. Cargo dùng lockfile. `npm run build`/`npm run installer` cũng đi qua builder và nhận `--api-base`; không dùng raw `npm run tauri build` để phân phối.

Portable EXE cần WebView2; NSIS currentUser có bootstrapper khi thiếu runtime. Đã thử build, startup WebView2, cài/gỡ TEST và portable ngoài workspace với PATH tối thiểu. **Chưa nghiệm thu native playback/UI, máy sạch, bootstrap máy thiếu runtime, Authenticode hoặc live E2E**. Không gọi TEST artifact là production beta. CLI2.12.2 và Cargo.lock đã pin.

[Hướng dẫn người dùng cuối](../../docs/windows-user-guide.vi.md) · [Khảo sát WATV](../../docs/watv-player-ui-analysis.md) · [Báo cáo hiện hành](../../docs/autonomous-implementation-report.md)
