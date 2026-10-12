# THEOLOI

Hệ sinh thái ứng dụng dành cho người theo Kinh Thánh. **AudioTP** là module đầu tiên: thư viện audio và kiến trúc bản nhạc, với Windows đang phát triển bằng **Tauri 2 / WebView2**, frontend JavaScript và backend **Cloudflare Worker / private R2**. Android/iOS được bổ sung sau; chưa chọn mobile stack.

## Trạng thái thực tế

Source Windows 0.2/Worker đã có; AudioTP phát M4A thật qua adapter local chỉ đọc. Thư viện vận hành có 485 guide, 485 instrumental, 13 silent. Người dùng báo B9 upload/verify 983 object; bước này không audit R2 live. Worker chưa có bằng chứng deploy live; chưa có EXE/installer đã build và kiểm thử.

Audio, snapshot website, catalog/manifest vận hành, review decisions, credential và SQLite **không nằm trong GitHub**. Chúng vẫn giữ trên máy hoặc R2 theo cấu hình vận hành. Clone mới chỉ có source; full tests/playback cần bộ dữ liệu đã cấp quyền từ người quản lý. Không tải bù website hoặc fake audio.

## Các module

| Đường dẫn | Mục đích |
|---|---|
| `apps/windows` | UI, player, API client, Tauri shell và tests |
| `workers/media-api` | Xác thực/vé phát, streaming R2 và local adapter |
| `scripts`, `tests` | Python pipeline/validators/review/offline tests |
| `schemas` | JSON schemas catalog/delivery/sheet/review |
| `benchmarks/score-viewer` | PDF/raster/vector prototype dùng bản nhạc tự tạo, vendor có license |
| `docs` | Kiến trúc, vận hành, báo cáo, roadmap/tasks |

Không tạo package mobile/web/shared rỗng. [Cấu trúc](docs/repository-structure.md) · [Audit](docs/repository-audit.md) · [Setup](SETUP.md) · [Master roadmap](docs/MASTER_ROADMAP.md) · [Roadmap](docs/ROADMAP.md) · [Phase hiện tại](docs/CURRENT_PHASE.md).

Quy trình: hoàn thành trọn phase được giao, kiểm thử/review/cập nhật Git, đề xuất bước tiếp theo rồi dừng. Không tự triển khai toàn bộ master roadmap khi người dùng chỉ giao một phase.

## Setup Windows

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-sheets.txt
.\.venv\Scripts\python.exe -m pip install -r benchmarks/score-viewer/requirements.txt
npm.cmd ci --prefix apps/windows
npm.cmd ci --prefix workers/media-api
```

Trong workspace đã có local inputs theo SETUP:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/prepare-windows.py
.\.venv\Scripts\python.exe -X utf8 scripts/prepare-worker.py
node workers/media-api/local-preview.mjs
```

Mở **http://127.0.0.1:8766/**; nếu helper đã chạy chỉ mở/reload. Đây là phát file local, chưa phải R2 live. [Hướng dẫn AudioTP](apps/windows/README.md).

## Kiểm thử

Clone chỉ có source: dùng nhóm fixture/mock trong [SETUP — Kiểm thử source-only](SETUP.md#kiểm-thử-source-only). Các lệnh full regression dưới đây cần private inputs/projections được chuẩn bị như SETUP; Worker typecheck/dry-run không chạy được khi thiếu generated JSON. Không thay JSON production bằng fixture để làm chúng pass.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
npm.cmd test --prefix apps/windows
npm.cmd run check --prefix workers/media-api
npm.cmd test --prefix workers/media-api
npm.cmd run typecheck --prefix workers/media-api
```

Worker check là dry-run local, không deploy. Full regression cần local datasets/generated projection, benchmark dependencies và fixture được chuẩn bị; thiếu file không phải PASS. Không nhúng R2 credential vào frontend/EXE hoặc public bucket tự động. `.env.example` là template tài liệu, không được ứng dụng tự load.
