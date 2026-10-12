# AudioTP — Catalog bản nhạc và xử lý file local trên Windows

Ngày bàn giao: 12/10/2026. Các công cụ này chỉ xử lý metadata và file local được phép sử dụng. Không có HTTP downloader, đăng nhập, lấy cookie, tải BookVN hoặc uploader R2.

## 1. Môi trường

Trong PowerShell:

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 -m pip install -r requirements-sheets.txt
```

Project hiện có `.venv` Python 3.13; đã cài và kiểm thử pypdf 6.20.0, PyMuPDF 1.28.2. Không cần activate environment, FFmpeg hoặc credential cho các lệnh bên dưới. `requirements-sheets.txt` bổ sung dependency PDF; `requirements.txt` của audio giữ nguyên. Việc cài dependency cần mạng; xử lý dữ liệu không cần mạng.

## 2. Catalog BookVN và mapping audio

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\sheets.py build --dry-run
.\.venv\Scripts\python.exe -X utf8 scripts\sheets.py build
.\.venv\Scripts\python.exe -X utf8 scripts\sheets.py validate
```

`build` chỉ đọc snapshot metadata đã khảo sát và catalog audio local, không truy cập BookVN. Nó tạo lại ba file: `catalog/sheet-sources.vi.json`, `delivery/sheet-mapping.vi.json`, `docs/sheet-mapping-report.md`. `--dry-run` không ghi file. `validate` đối chiếu cả snapshot gốc, schema và catalog audio; trả `PASS` hoặc `FAIL`, exit code 0 hoặc 1.

Catalog hiện có 542 nguồn: 480 main, 5 appx, 57 numbered-appendix. Mapping có 489 record candidate, 1 conflict (main 464), 52 unmatched; **0 liên kết đã xác minh**. Năm cặp title phụ lục trùng vẫn là 10 record riêng. Xem toàn bộ các dòng trong [báo cáo mapping](sheet-mapping-report.md).

Catalog BookVN là dữ liệu quan sát có thể tái tạo, không phải bản ghi phê duyệt. Không sửa candidate thành verified hoặc đổi quyền trực tiếp rồi mong `sheets.py validate` chấp nhận: validator nguồn sẽ phát hiện khác snapshot. Đã có [công cụ review định danh/overlay riêng](mapping-review.md); quyền sử dụng vẫn cần nguồn bằng chứng và quy trình riêng, không được cấp bởi approve mapping. Nguồn local độc lập có thể khai báo liên kết đã review, kèm `verificationEvidence`; không suy ra verified từ confidence.

## 3. Kiểm tra manifest BookVN hiện tại

```powershell
.\run-sheet-files.bat verify
.\run-sheet-files.bat status
```

Hiện `verify` PASS với **0 assets**, vì cả 542 nguồn đều chưa có file được nhập hợp lệ. `availability` ghi `no-file`; PASS ở đây xác nhận cấu trúc và tính toàn vẹn của manifest hiện có, không xác nhận đã có 542 PDF. `status` sẽ là 0 job nếu chưa tạo state xử lý local. Đây là verifier file local, không phải B10/R2.

## 4. Demo tự tạo, không dùng nội dung BookVN

Generator tạo PDF vector 2 trang và 2 PNG hình học, cùng catalog/plan riêng. Mỗi lần tạo dùng một thư mục trống; nếu đã có file thì từ chối ghi đè. Demo `sample-01` đã được Codex tạo và chạy thử. Muốn tự tạo mới, dùng `sample-02`:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\make-sheet-demo.py --directory tmp/sheets-demo/sample-02

$demoRoot = 'tmp/sheets-demo/sample-02'
$demoCatalog = "$demoRoot/catalog/sheet-demo.json"
$demoPlan = "$demoRoot/catalog/sheet-file-plan.demo.json"

# Chỉ kiểm tra, không tạo state/media/manifest.
.\run-sheet-files.bat process --root $demoRoot --catalog $demoCatalog --plan $demoPlan --dry-run

# Xử lý ba job nhỏ: PDF gốc, PDF từ ảnh, ảnh nhiều trang.
.\run-sheet-files.bat process --root $demoRoot --catalog $demoCatalog --plan $demoPlan

# Resume: cùng lệnh, skip output hoàn tất còn hợp lệ.
.\run-sheet-files.bat process --root $demoRoot --catalog $demoCatalog --plan $demoPlan

.\run-sheet-files.bat status --root $demoRoot
.\run-sheet-files.bat verify --root $demoRoot --catalog $demoCatalog

# Chỉ thử lại job đang failed trong plan.
.\run-sheet-files.bat process --root $demoRoot --catalog $demoCatalog --plan $demoPlan --retry-failed
```

Kỳ vọng sau xử lý: 3 completed, 0 failed, 0 remaining; lần resume tiếp theo 3 skipped, 0 processed. Manifest có 3 assets và 4 file output. `--root` đặt vùng state/media/manifest riêng; `--catalog` và `--plan` là đường dẫn tính từ thư mục PowerShell hiện tại, không tự nối vào `--root`. Các đường dẫn `inputs` bên trong plan tính từ `--root`, dùng `/`.

## 5. Nhập tài liệu local được phép sử dụng

Chuẩn bị catalog riêng theo `schemas/sheet-catalog.schema.json` và mẫu `tmp/sheets-demo/sample-01/catalog/sheet-demo.json`. Mỗi nguồn có ID ổn định, tên đúng tài liệu, provider/locale, số riêng, edition nếu đã biết và bằng chứng quyền thực tế. Không dùng ID/tuyên bố self-authored của demo cho tài liệu của người khác. Với nguồn local: `sourcePostId`, `sourcePageUrl`, `originalPdf` có thể null; file thực tế nằm trong manifest. Giữ `audioCatalogSha256` khớp catalog audio hiện tại.

`usageRights.status` phải `confirmed`, `evidence` không rỗng và `permissions.store=true`. Chuyển ảnh thành PDF cần thêm `convert=true`. Quyền dùng cá nhân không tự cấp quyền `serve`/`upload`: hai cờ này được lưu riêng, có thể giữ false. Công cụ chỉ kiểm tra tuyên bố/bằng chứng trong metadata; không thay chủ sở hữu xác nhận quyền.

Đặt file đầu vào dưới `source/local-sheets/`, rồi tạo `catalog/sheet-file-plan.local.json`, ví dụ:

```json
{
  "schemaVersion": 1,
  "jobs": [
    {
      "sheetId": "local:vi:my-authorized-score:1",
      "edition": "edition-2026",
      "kind": "original-pdf",
      "inputs": ["source/local-sheets/my-score/original.pdf"]
    },
    {
      "sheetId": "local:vi:my-authorized-score:1",
      "edition": "edition-2026",
      "kind": "image-derived-pdf",
      "inputs": [
        "source/local-sheets/my-score/page-1.png",
        "source/local-sheets/my-score/page-2.png"
      ]
    }
  ]
}
```

ID này phải tồn tại trong catalog riêng. `original-pdf` nhận đúng một PDF; `image-pages` giữ từng PNG/JPEG nguyên bytes; `image-derived-pdf` ghép ảnh theo đúng thứ tự inputs. Hai job cùng sheet/edition/kind bị từ chối. Muốn lưu một ấn bản khác, dùng edition khác; không đổi nghĩa của ID nguồn để ghi đè tài liệu cũ.

Các lệnh batch local dưới đây chỉ dùng **sau khi bạn đã tạo catalog/plan hợp lệ và có file được phép**. Chúng không tải file từ web:

```powershell
$localCatalog = 'catalog/sheet-local.vi.json'
$localPlan = 'catalog/sheet-file-plan.local.json'
$localState = 'state/sheet-local.sqlite'
$localManifest = 'delivery/sheet-local-manifest.vi.json'

# Preflight/dry-run trước khi chạy nhiều file.
.\run-sheet-files.bat process --catalog $localCatalog --plan $localPlan --state $localState --manifest $localManifest --dry-run

# Full/resume: người dùng tự chạy ngoài Codex khi batch lớn.
.\run-sheet-files.bat process --catalog $localCatalog --plan $localPlan --state $localState --manifest $localManifest

.\run-sheet-files.bat status --state $localState
.\run-sheet-files.bat verify --catalog $localCatalog --manifest $localManifest

# Retry riêng failed, giữ nguyên catalog/plan/state/manifest của batch đó.
.\run-sheet-files.bat process --catalog $localCatalog --plan $localPlan --state $localState --manifest $localManifest --retry-failed
```

Không có lệnh download BookVN hoặc upload sheet R2 trong phiên bản này. Không dùng catalog restricted của BookVN để chạy batch file.

## 6. Resume, FAIL và cách hiểu kết quả

- `process`: exit 0 khi các job trong plan không failed; exit 1 khi preflight lỗi hoặc có job failed; exit 130 khi Ctrl+C. Dòng `[n/total]` cho biết completed/skipped/failed. `counts` của process chỉ tính plan hiện tại; `status` tính toàn bộ state.
- `dry-run`: `would-process`, `would-skip`, `would-fail`, `not-selected`; kiểm tra nguồn, quyền, state và output nếu resume; không ghi. `--retry-failed` không chọn job pending/completed hoặc chưa có state.
- `status`: chỉ đọc SQLite; không kiểm tra lại bytes file. Exit 1 nếu state có failed. State có application ID/schema version riêng; DB lạ, JSON artifact sai hoặc DB hỏng bị từ chối, không reset.
- `verify`: chỉ đọc manifest/catalog/output; PASS sau kiểm tra mọi file output, SHA-256, bytes, loại file, số trang, thứ tự, key, quyền, liên kết và hash pin. Báo `duplicateHashes` để thấy cùng bytes ở nhiều nơi; không tự gộp/xóa ấn bản. Không cần file inputs còn tồn tại để verify bản lưu; source hash là provenance đã ghi lúc xử lý, không phải chữ ký từ nhà cung cấp.
- Resume yêu cầu **cả inputs còn hợp lệ** và output đúng fingerprint/hash/format. File output hỏng sẽ được tái tạo từ inputs hợp lệ. Thiếu inputs thì job failed; thêm lại file đúng rồi retry. File hợp lệ cũ vẫn được giữ; nếu lần cập nhật thất bại, manifest vẫn tham chiếu phiên bản tốt cuối cùng nếu quyền/catalog còn phù hợp. State failed phản ánh lần xử lý mới nhất, không có nghĩa bản lưu cũ đã bị xóa.
- PDF giả HTML, PDF thiếu EOF, encrypted/repaired hoặc không render được, ảnh sai định dạng đều FAIL. Không giải mã PDF. Giới hạn hiện tại: 256 MiB/file, 500 trang/PDF, 100 triệu pixel/ảnh.
- Nếu manifest populated nhưng state thiếu/không khớp, công cụ từ chối thay thế. Khôi phục **cặp manifest + SQLite** từ backup; không xóa/reset DB để “sửa” lỗi. Nếu cố ý tạo bộ xử lý khác, dùng state và manifest riêng. Catalog/rights thay đổi phải review rồi chạy lại với đủ nguồn đầu vào để cập nhật fingerprint.
- Nếu quyền chưa xác nhận, dừng nhập file đó và cung cấp bằng chứng phù hợp; không đổi cờ để vượt kiểm tra. Nếu mapping conflict/unmatched, review tên/ấn bản/nội dung trước khi dùng cho frontend/bot.

Có thể đóng Codex khi lệnh chạy trong PowerShell ngoài Codex. Không chạy hai process cùng `--root`; khóa OS tự giải phóng khi process kết thúc. Manifest được ghi atomic; state SQLite commit sau từng job. Backup catalog, plan, SQLite, manifest và media cùng nhau; các file content-addressed cũ không tự bị xóa.

## 7. Kiểm thử offline

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_sheets.py -v
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_sheet_files.py -v
```

Các fixture PDF/ảnh đều tự tạo; không tải media hoặc dùng credential. Xem [báo cáo triển khai](sheet-implementation-report.md) cho kết quả kiểm tra và phần chưa xác minh.
