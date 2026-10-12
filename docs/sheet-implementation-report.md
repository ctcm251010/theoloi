# AudioTP — Bàn giao catalog bản nhạc và pipeline local

Ngày: 12/10/2026. Phạm vi hoàn thành: metadata BookVN đã quan sát, matching audio có review, file local được phép và demo tự tạo. Không tải BookVN, không chạy FFmpeg/B10 hoặc upload R2, không đọc credential.

## Dữ liệu và mapping

| Chỉ số | Kết quả |
|---|---:|
| Trang bài trong snapshot quan sát | 542 |
| Main / appx / numbered-appendix | 480 / 5 / 57 |
| Main vắng trong dải 1–485 | 34, 242, 300, 306, 367 |
| Trang đã quan sát nội dung DOM | 7 (9 ảnh nền) |
| Chưa quan sát nội dung | 535 |
| Candidate / conflict / unmatched | 489 / 1 / 52 |
| Liên kết ứng viên, gồm conflict | 490 |
| Liên kết đã xác minh | 0 |
| Cặp title trùng giữa appx và numbered-appendix | 5 |
| File BookVN đã nhập / tải | 0 / 0 |

Đã tận dụng snapshot metadata giữ từ khảo sát Chrome, không mở lại hàng trăm trang. Đây là phạm vi đã quan sát, không khẳng định toàn bộ kho website. Snapshot chỉ chứa post/title/URL và quan sát cấu trúc, không có HTML tài khoản/cookie/token hoặc bytes ảnh.

Khóa nguồn `bookvn:vi:post:<postId>` không phụ thuộc array index. Main dùng số từ slug và số hiển thị cùng title NFC/khoảng trắng/casefold. Phụ lục chỉ matching title trong nhóm audio appendix, không fallback cùng số. Bài main 464 có “ĐiCon” trong title BookVN, khác “Đi Con” của audio: giữ nguyên dữ liệu và đưa vào conflict. Không tự sửa typo để xác nhận tác phẩm. Năm cặp phụ lục vẫn giữ source ID/ấn bản riêng; chưa chứng minh nội dung giống nhau.

Không có audio song nào thiếu hoàn toàn ứng viên, nhưng bài 464 chỉ có ứng viên confidence thấp do conflict; không gọi đó là đã khớp. 52 numbered-appendix chưa có ứng viên audio. Nhạc ngẫm nghĩ không được ghép vào bản nhạc Bài ca mới.

Xem [báo cáo toàn bộ mapping](sheet-mapping-report.md), [catalog](../catalog/sheet-sources.vi.json) và [mapping JSON](../delivery/sheet-mapping.vi.json).

## Kiến trúc và công cụ đã triển khai

- Snapshot bất biến → builder/validator/schema riêng → catalog nguồn và mapping/report tái tạo được. Observed/not-observed tách rõ; originalPdf null là chưa tìm thấy, không phải chứng minh không tồn tại.
- Catalog chính không chứa attempts/download/upload state. Metadata quyền có evidence và các cờ store/convert/serve/upload độc lập. BookVN mặc định restricted, mọi quyền false.
- Plan offline khai báo sheetId/edition/kind/inputs. Pipeline kiểm tra quyền trước khi ghi; chỉ nhận vùng input local dành riêng, chặn traversal/junction/Windows alias và đường dẫn audio/credential.
- PDF gốc và ảnh gốc giữ nguyên bytes. PDF tạo từ ảnh giữ raster và thứ tự trang, gắn kind phái sinh; kiểm tra bằng pypdf strict + PyMuPDF render, SHA-256/bytes/pageCount/dimensions.
- SQLite riêng có application ID/version, integrity/shape checks và khóa OS; commit từng job. Dry-run không ghi. Resume chỉ skip khi input fingerprint và file output hợp lệ; retry riêng failed.
- Manifest có availability cho nguồn chưa có file, file provenance, rights, audio links, hash pin/revision và object key dự kiến. Giữ ấn bản cũ khi chạy plan mới; giữ bản hợp lệ cuối cùng khi cập nhật thất bại. Không ghi đè manifest populated bằng state mới/thiếu. Verifier local báo PASS/FAIL và hash trùng, không tự xóa/gộp.
- Demo tự tạo: original PDF 2 trang, 2 PNG, ba loại job; catalog/state/media/manifest riêng dưới `tmp/sheets-demo/sample-01`. Đã render và xem PDF phái sinh: bố cục rõ, không cắt chữ; kiểm thử pixel/thứ tự ảnh bằng dữ liệu fixture.

## Folder và key dự kiến cho R2

```text
source/snapshots/bookvn-vi-2026-10-12.sheets.json
source/local-sheets/                    # Người dùng cung cấp file có quyền, bỏ qua Git
catalog/sheet-sources.vi.json
schemas/sheet-catalog.schema.json
schemas/sheet-plan.schema.json
schemas/sheet-manifest.schema.json
delivery/sheet-mapping.vi.json
delivery/sheet-manifest.vi.json          # 542 no-file, 0 assets hiện tại
state/sheet-transfers.sqlite            # Chỉ tạo khi xử lý thật, chưa tạo cho BookVN
media/sheets/v1/<provider>/vi/<source>/<edition>/<kind>/<sha256>.<ext>
tmp/sheets/                             # Staging riêng
tmp/sheets-demo/sample-01/               # Demo tự tạo, không phải production
scripts/sheet_*.py
scripts/sheets.py
scripts/sheet-files.py
scripts/make-sheet-demo.py
run-sheet-files.bat
requirements-sheets.txt
```

Object key dự kiến bỏ tiền tố `media/`: `sheets/v1/<provider>/vi/<source>/<edition>/<kind>/<sha256>.<ext>`. Với BookVN, source là `post-<id>`; với local là SHA-256 của source ID theo serializer catalog. Hash giúp nhận biết cùng bytes; sheet/edition/kind vẫn tách riêng. Nhiều trang ảnh là danh sách thứ tự trong manifest, kể cả khi hai trang có cùng hash. Không upload hoặc cấu hình R2; prefix này chỉ là dữ liệu chuẩn bị, uploader sheet chưa triển khai.

## Kiểm chứng

Kết quả cuối: `unittest discover -s tests -v` chạy **103 test: 102 PASS, 1 SKIP**, 58,175 giây, exit 0. Test skip là test symlink cũ trong `test_delivery`: tài khoản Windows không có quyền tạo file symlink. Test Windows junction mới của sheet chạy PASS; không sửa ACL hoặc xin quyền hệ thống để chạy lại test cũ. **44 test mới (14 catalog + 30 file local) đều PASS.** Log: `tmp/sheet-full-tests.log`; riêng file local: `tmp/sheet-files-final-green.log`. Các log RED lưu lỗi trước triển khai, log GREEN lưu kiểm thử sau sửa; không phải log tải tài liệu thật.

Review độc lập read-only hoàn tất sau vòng sửa, không còn finding Critical/Important/Minor. Các regression đã sửa: manifest giữ ấn bản cũ khi chạy subset plan; giữ output tốt cuối cùng khi cập nhật failed; từ chối manifest populated với state mới/thiếu; từ chối artifact JSON/state sai trước khi ghi. Reviewer cũng đối chiếu hash pin/revision, 542 availability, quyền restricted và 0 asset BookVN. Quyền pháp lý, định danh tác phẩm/ấn bản và hành vi production/remote vẫn dành cho review thực tế, không được coi là đã chứng minh bằng unit test.

Validator catalog đối chiếu snapshot PASS; verifier manifest BookVN PASS với 0 assets/0 files; demo verify PASS với 3 assets/4 files/4 hash khác nhau. CLI/BAT status, dry-run, resume và retry-failed đã chạy với demo nhỏ; retry-failed không chọn job nào khi không có lỗi. Hash audio catalog/manifest và snapshot bên dưới khớp baseline sau kiểm thử.

Demo CLI đã chạy: dry-run 3 would-process; process 3 completed; resume 3 skipped/0 processed; status 3 completed/0 failed; verify PASS. Batch local lớn và thao tác R2 dành cho người dùng, chưa chạy.

Hash audio baseline để đối chiếu cuối:

```text
catalog/catalog.vi.json
e449b3a25ed49c6879bf06c72219863857632491f4a2ca424c2bc692e45ca8d4
delivery/manifest.vi.json
b54965fd3c612439ba2ef503bd502abbab11fadcd6b1e16857c2ef0403051a4c
source/snapshots/bookvn-vi-2026-10-12.sheets.json
6d1eb5e44446fa67e3d2d04989c84ad34be8474916375e7d4accb1a7dd725307
```

## File mới hoặc thay đổi

Mới: snapshot BookVN; catalog sheet; mapping JSON/report; manifest sheet; ba schema sheet; `scripts/sheet_catalog.py`, `sheet_paths.py`, `sheet_media.py`, `sheet_pipeline.py`, `sheets.py`, `sheet-files.py`, `make-sheet-demo.py`; hai test module `test_sheets.py`, `test_sheet_files.py`; `requirements-sheets.txt`; `run-sheet-files.bat`; hai tài liệu bàn giao này; spec/plan dưới `docs/superpowers/`.

Sửa: `.gitignore` để loại file local/state/staging/demo; `bookvn-pdf-analysis.md` chỉ thêm liên kết bàn giao. `.venv` có hai dependency PDF bổ sung. Log, render và fixture chỉ ở tmp. Không sửa source audio, catalog audio, manifest audio, script audio, cấu hình R2 hoặc credential.

## Chưa xác minh và bước tiếp theo

1. **BookVN PDF gốc/nguồn tải được phép còn thiếu.** Chưa tải/chuyển ảnh BookVN; nội dung cá nhân không tự thay đổi cờ restricted từ thông báo website. Khi có nguồn hoặc giấy phép cụ thể, review phạm vi rồi thiết kế importer/downloader phù hợp.
2. Cần review bài 464, 52 phụ lục chưa matching và 5 cặp phụ lục khác namespace/ấn bản. Mọi liên kết catalog nguồn hiện chỉ candidate. Cập nhật bước sau: đã có [CLI/UI review định danh riêng](mapping-review.md), store/export vẫn 0 verified cho đến khi người dùng review; chưa có công cụ phê duyệt quyền sử dụng. Không tự chọn candidate làm liên kết đã xác minh cho frontend/bot.
3. Chưa biết nội dung 535 trang chưa mở, tổng trang/asset thật, PDF có ở nơi khác, auth/header/URL expiry/rate limit. Không suy đoán URL tài liệu.
4. Chưa có frontend/API/bot phục vụ bản nhạc, sheet uploader R2 hoặc verifier remote. Manifest/key/rights là giao diện chuẩn bị cho bước đó; cần quyền serve/upload phù hợp trước khi phát hành.
5. Pipeline chỉ quản lý file local được phép, không phục hồi mất toàn bộ state từ media, không xóa file orphan/cũ, không tự sửa mapping và không chứng minh nguồn gốc từ hash tự tính. Backup bộ catalog/plan/state/manifest/media; verifier kiểm tra tính toàn vẹn local, không phải chữ ký nhà cung cấp.

Lệnh thực tế và cách xử lý FAIL: [Windows guide](sheets-windows.md).
