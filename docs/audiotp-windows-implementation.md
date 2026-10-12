# AudioTP — Windows MVP và hai mục phát nhanh

**Cập nhật hiện hành 0.2 — 12/10/2026:** đã bỏ WAV demo khỏi luồng nghe, triển khai Worker/API và phát M4A thật qua local integration. Xem [báo cáo P0–P4 và lệnh hiện tại](autonomous-implementation-report.md), [backend](../workers/media-api/README.md). EXE/live R2 E2E vẫn BLOCKED vì thiếu toolchain/deployment. Phần bên dưới là lịch sử **0.1**, không mô tả source hiện tại.

Ngày 12/10/2026, Windows, Chrome extension profile Bang. Tiếp tục baseline hiện có; không truy cập credential, chạy B10 live, upload/download audio, đổi bucket hoặc lấy tài liệu BookVN.

## Kết quả

Đã triển khai source MVP trong `apps/windows`: giao diện ES modules, một HTMLAudioElement, projection metadata client, server preview loopback và shell Tauri 2. Browser thử được với âm mẫu tự tạo, **chưa có EXE build thành công hoặc nghe R2 production**.

Giữ đúng Hướng dẫn **485**, Nhạc đệm **485**, Nhạc ngẫm nghĩ **13**. Số bài lấy từ identifier đã kiểm tra, không lấy index; silent có namespace riêng. Projection đối chiếu đầy đủ asset/logicalId/variant/kind/section/number và duration đo từ manifest; không phát hành source HLS, object key, đường local hoặc state.

Phát nhanh có hai nút đúng tên yêu cầu. Catalog chính khóa cả hai; nguồn/rights review tách nhau. Khi fixture có nguồn được xác minh và quyền được duyệt, nút có loading/Play/Pause/retry và tên riêng, dùng chung player với ba tab. Không có nhiều audio element phát chồng. Queue được chụp tại lúc chọn bài; chuyển tab không tự thay queue hoặc nguồn. Player xử lý resolver/play timeout, lựa chọn cũ về muộn, lỗi media, retry, seek, volume, mute, next/previous, loop/shuffle/continuous. Yêu thích/lịch sử/theme lưu metadata; chưa có app-managed media caching/download.

## WATV và tình trạng asset

Nguồn/bằng chứng đầy đủ: [watv-player-ui-analysis.md](watv-player-ui-analysis.md).

| Nội dung | Bằng chứng | Tình trạng |
|---|---|---|
| 983 audio | B9 local state: 983 uploaded, 983 verified, 0 failed/remaining | Không gọi R2 xác minh lại; B10 vẫn user-run |
| Ghim Nhạc ngẫm nghĩ | Hai lần trong cùng phiên yêu cầu đúng URL silent ID 19976, Thánh Thay! Thánh Thay!, UI 00:56 | Asset nằm sẵn trong 13 silent; chưa chốt alias cố định qua phiên/ngày |
| Ghim Cầu nguyện… | Bấm UI yêu cầu `WATV_PRAYER/pray/our_wish`; UI 01:08; kết thúc/reset trong lượt quan sát | Ngoài manifest; chưa nhập nguồn/quyền mới |
| pray_01–pray_13 | Literal URL trong script nhúng; không quan sát request của hai mục ghim | Chưa rõ dùng ở UI nào; không tự ghép hoặc nhập |

00:56/01:08 là duration nhãn UI, không phải duration media đo độc lập. Không khẳng định đã nghe và nhận diện nội dung recording hoặc có chuỗi nhiều file. Không đưa raw URL vào app.

## Kiểm thử và bằng chứng

| Kiểm tra thực chạy | Kết quả |
|---|---|
| Python toàn dự án, unittest discover | **159 tổng: 157 PASS / 0 FAIL / 2 SKIP**, 110,972 giây |
| Hai SKIP | Hai test symlink không đủ quyền tạo trên Windows; junction traversal test vẫn PASS |
| Node Windows MVP | **24 PASS / 0 FAIL / 0 SKIP**, gồm Unicode/khoảng trắng, namespace, source/rights, storage, phím tắt, player race/timeout/error và quick states |
| Chrome với metadata 983 | Đúng 485/485/13; tìm 100/PL 1/không dấu+nhiều khoảng trắng; số thiếu 34 trả 0; tab-change giữ nguồn khi đang phát; guide→instrumental→silent thay nguồn chung; pause/seek/mute, volume control, next/previous, favourite/history, theme, catalog-only stop |
| Chrome với copy độc lập chỉ chứa fixture | Hai quick controls enabled trên nguồn mẫu tự tạo; Play/Pause/loading/error/retry; đổi tab giữ quick đang phát; chọn bài silent thay quick; một audio element |
| Lỗi thực trong browser | Cố ý bỏ WAV instrumental **chỉ ở copy tmp**: error, paused, nút retry hiện; phục hồi fixture và retry phát lại thành công |
| Responsive | Thực đo rộng **1732×917** và hẹp **623×818 CSS px**, không tràn ngang; viewport yêu cầu 700×900 không bằng kích thước DOM thực, báo theo DOM; đã reset |
| Tauri config | Khớp JSON schema CLI cài local; không có IPC command/plugin hoặc capabilities được cấp |
| Native build | **BLOCKED/FAIL prerequisite**: `cargo metadata` program not found; chưa compile Rust |
| EXE, NSIS installer, WebView2/Windows máy sạch, native size/RAM | **SKIP — chưa có toolchain/binary**, không lấy Chrome thay cho kết quả native |
| Live R2/API, B10, PRAYER import, Cloudflare deploy | **NOT RUN** theo phạm vi |

Môi trường thực đo: Python 3.13.15, Node 24.18.0, npm 12.2.0, Tauri CLI 2.12.2. Thư mục web **1.516.092 bytes, khoảng 1,52 MB**, gồm metadata và 3 WAV mẫu; đây **không phải dung lượng EXE/installer**. Chrome kiểm thử thêm Space pause, ArrowRight seek đúng 5 giây, M mute, N/P chuyển đúng bài 2/bài 1; nhập `n` trong ô tìm kiếm không chuyển bài.

[Python log](../apps/windows/evidence/python-tests.txt), [Node log](../apps/windows/evidence/node-tests.txt), [build blocker](../apps/windows/evidence/native-build.txt), [DOM smoke evidence](../apps/windows/evidence/browser-smoke.json), [verification](../apps/windows/evidence/verification.json). Browser JSON là quan sát các bước, có cả trạng thái loading trung gian; các bước sau mới xác nhận thành công/error. Fixture tạm sinh qua PowerShell có title bị thay dấu thành `?` do encoding pipe, không ảnh hưởng metadata UTF-8 chính thức; không dùng screenshot fixture đó để đánh giá typography tiếng Việt.

![AudioTP browser MVP](../apps/windows/evidence/app-wide.jpg)

[Giao diện sáng](../apps/windows/evidence/app-wide-light.jpg), [giao diện hẹp](../apps/windows/evidence/app-narrow.jpg). Đây là screenshot của app tự tạo, không phải tài liệu BookVN. Ảnh hẹp cuộn tới danh mục khi thao tác player; banner demo nằm phía trên. Snapshot wide cuối hiển thị banner và hai nút khóa. Ảnh `app-initial.jpg` từ giai đoạn trước không phải giao diện cuối và không dùng làm bằng chứng.

## File và cấu trúc triển khai

- `scripts/windows_catalog.py`, `scripts/prepare-windows.py`, `tests/test_windows_catalog.py`: projection, generator, kiểm thử catalog.
- `apps/windows/web/`: HTML/CSS/modules, catalog client, quick-play JSON, favicon và 3 WAV tự tạo; không có bản nhạc thật.
- `apps/windows/tests/`: Node unit tests.
- `apps/windows/serve.py`, `tests/test_windows_preview.py`: server chỉ GET/HEAD, Range/If-Range/conditional/ETag, MIME, Host check, chống traversal/symlink/junction, không list directory.
- `apps/windows/src-tauri/`: Rust shell, build/config, icons tự tạo; `package.json`/lockfile khóa CLI 2.12.2.
- `.gitignore`: thêm node_modules, Rust target và npm cache; không đổi quy tắc dữ liệu cũ.
- `docs/watv-player-ui-analysis.md`, báo cáo này, `docs/windows-app-architecture.md`, `apps/windows/README.md`, plan và `apps/windows/evidence/`: bằng chứng/hướng dẫn/bàn giao; architecture cũ được thêm liên kết tới trạng thái MVP.

Kiểm tra hash trước/sau của source snapshot, audio catalog/manifest, sheet catalog, R2 config; kết quả chi tiết ở verification JSON. Không thay audio, media đã hoàn tất, upload/download state, review decisions hoặc credential. Server chỉ phục vụ web root; Rust shell không chứa network/secret code; CSP chỉ cho tài nguyên local. Preview server không phải authenticated backend và không được public ra Internet.

## Giới hạn và bước tiếp

1. **Build Windows:** người dùng cài Rust MSVC, C++ Build Tools, WebView2 theo hướng dẫn chính thức; build bằng các npm scripts đã có trong [README](../apps/windows/README.md). Chốt Cargo.lock, chạy EXE/installer, đo dung lượng/RAM/startup và kiểm tra máy sạch trước khi gọi release.
2. **Private audio API:** review cơ chế đăng nhập, scope cá nhân/phân phối và manifest revision; sau đó mới triển khai endpoint/ticket/read-only Range streaming, CSP allowlist và resolver live. Chưa triển khai endpoint giả hoặc credential nhúng trong app.
3. **Quick sources:** review quy tắc chọn ghim đầu; review `our_wish` và quyền đúng phạm vi trước nhập subset; không tự thêm 14 PRAYER vào baseline 983. Chưa có importer PRAYER nên không đưa lệnh download/upload chưa tồn tại.
4. **PDF:** tiếp tục sheet catalog/review overlay hiện tại. Không tự tải hoặc chuyển PNG BookVN. Viewer chỉ tích hợp sau khi có nguồn được phép và mapping đã review.
5. **Production:** signed installer/updater, auth token vault, cache giới hạn/xóa cache, access revoke/offline policy, keyboard/assistive tech và WebView2 errors cần phase riêng. UI metadata local không đồng nghĩa quyền phục vụ audio production.

Mọi command hiện có để preview/test/build được ghi tại README; không chạy job lớn hoặc cloud mutation trong bước này.
