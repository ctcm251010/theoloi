# AudioTP — Catalog bản nhạc và file local

## Mục tiêu và phạm vi đã được giao

Người dùng yêu cầu tự triển khai toàn bộ phần khả thi: catalog/schema, matching có review, xử lý PDF/ảnh được phép bằng file tự tạo, CLI offline, validation và tài liệu Windows. Mục đích hiện tại là sử dụng cá nhân; audio, state audio, manifest audio, R2 và credential giữ nguyên. Không tải/chụp/chuyển ảnh BookVN. Không chạy bulk hoặc upload.

## Lựa chọn kiến trúc

Chọn catalog nguồn riêng + manifest file riêng + SQLite xử lý riêng. Gắn trực tiếp sheet vào catalog audio sẽ sửa dữ liệu đã pin; dùng số bài làm khóa chung sẽ ghép sai phụ lục. Không dùng hai phương án đó. Snapshot metadata đã giữ trong browser được xuất ra JSON an toàn, không truy cập lại 542 trang bài.

## Catalog và matching

- Snapshot gồm 542 post/title/URL, 6 trang danh mục và 7 quan sát DOM, không chứa HTML tài khoản hoặc ảnh.
- Source ID theo provider/locale/post ID; giữ main, appx và numbered-appendix độc lập, số hiển thị tách số từ slug.
- Title gốc giữ nguyên; NFC + khoảng trắng + casefold cho matching, không bỏ dấu tiếng Việt.
- Bài chính so số và title; lệch số/title là conflict/review. Phụ lục chỉ xét title trong audio appendix, tuyệt đối không fallback cùng số.
- Mỗi ứng viên có confidence, evidence và verificationStatus needs-review. Không tự tuyên bố verified. Trùng title không gộp record.
- Rights BookVN restricted; nội dung 535 bài chưa mở là not-observed; PDF chưa thấy không đồng nghĩa không tồn tại.
- Catalog generic cho nguồn được phép sau này; schema + validation ngữ nghĩa đối chiếu nguồn/audio, đường dẫn, quyền và ID.

## File và manifest

CLI chỉ đọc file local do người dùng cung cấp, không có HTTP downloader. Plan có jobs: sheetId, edition, format (original-pdf/image-derived-pdf/image-pages), inputs theo thứ tự. Quyền store phải confirmed; convert cần quyền convert; manifest ghi quyền serve/upload riêng, không suy ra quyền phát lại từ quyền lưu cá nhân. Mọi quyền phải có evidence.

PDF gốc giữ nguyên bytes. PDF từ ảnh dùng PyMuPDF convert_to_pdf/insert_pdf, giữ thứ tự và kích thước raster, không tự gọi đó là PDF gốc. Dùng pypdf strict và render PyMuPDF để kiểm tra định dạng, trang, corruption; encrypted PDF bị từ chối, không thử giải mã. SHA-256/bytes/dimensions và provenance được lưu trong manifest. Source files không thay đổi.

Output content-addressed dưới media/sheets/v1; key tương ứng sheets/v1 để chuẩn bị R2. State SQLite riêng dưới state/sheet-transfers.sqlite, có lock; dry-run không ghi state/media. Resume skip chỉ sau kiểm tra input fingerprint và output hash/format. Failed retry chọn riêng; tiến độ/exit code rõ. Manifest chỉ chứa output hoàn tất, availability giữ bản nhạc chưa có file. Không gọi R2.

## Kiểm thử và tiêu chí đạt

TDD: reversed metadata, NFC/whitespace, phụ lục cùng số khác bài, title trùng/ambiguous, title-number conflict, null/malformed/duplicate IDs, snapshot tampering, rights escalation, local path traversal/junction, thiếu file, HTML giả PDF, encrypted/truncated PDF, hash mismatch, hai trang ảnh đúng thứ tự, byte-preserving original PDF, resume/failed retry/dry-run, state lock và CLI exit code.

Các fixture hoàn toàn tự tạo, không phải bản nhạc BookVN. Kiểm thử render và pixel/dimensions cho PDF tạo từ ảnh. Chạy test offline hiện có; không chạy verifier B10 hoặc gọi dịch vụ. Ghi hashes audio/manifest trước và sau.

## Phân chia trách nhiệm

Codex triển khai và chạy unit/integration test cùng demo nhỏ tự tạo. Người dùng tự chạy batch local về sau, tải từ nguồn được phép và upload R2. Không có nguồn tải được phép nên không triển khai downloader BookVN.
