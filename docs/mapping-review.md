# AudioTP — Review định danh bản nhạc ↔ audio

Review overlay độc lập, không sửa snapshot/catalog gốc, không review hoặc cấp quyền tải/phân phối. Store hiện rỗng, **0 quyết định / 0 verified**. Catalog giữ 542 nguồn, 489 candidate, 1 conflict, 52 unmatched. Không tự approve theo confidence hoặc cùng số phụ lục.

## File và schema

- `reviews/sheet-mapping-decisions.vi.json`: lịch sử quyết định có sequence, reviewer, UTC timestamp, evidence/provenance, source/audio identity hash, catalog pins và event hash chain. Revision bao phủ toàn store.
- `schemas/sheet-review.schema.json`: root store; `$defs/batch` cho batch; `$defs/export` cho export. JSON Schema Draft 2020-12, không nhận field quyền sử dụng trong decision.
- `reviews/sheet-review-queue.vi.json`, `reviews/sheet-review.html`: view/proposal tái tạo được; không phải decision store.
- `delivery/sheet-verified-mapping.vi.json`: chỉ các approve hiện còn hiệu lực và không stale; usageRights được sao nguyên từ catalog. Export **không phải** danh sách được phép phục vụ file.

Store JSON được ghi atomic dưới OS lock; lỗi ở bất kỳ dòng batch nào không lưu phần đầu. Đây là dấu vết nhất quán local, không phải chữ ký số chứng minh người review. Người có quyền sửa toàn bộ file vẫn có thể tạo lại hash chain. Backup store cùng catalog/revision; không reset hoặc sửa event cũ. Các lệnh dùng `.venv` sẵn có, không cần dependency mới. Test JS UI dùng Node.js của môi trường phát triển; người dùng UI/CLI không cần Node.

## Bắt đầu trên Windows

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 scripts\review-mapping.py status
.\.venv\Scripts\python.exe -X utf8 scripts\review-mapping.py queue
.\.venv\Scripts\python.exe -X utf8 scripts\review-mapping.py html
```

Mở `D:\Workspace\AudioTP\reviews\sheet-review.html` bằng Chrome/Edge qua File Explorer. Trang offline, không cần server, không tự tải ảnh/âm thanh/tài liệu. Nút nguồn chỉ mở trang khi bạn chủ động click; giữ các giới hạn quyền truy cập/tải của website. Bộ lọc mặc định là **main 464 và 10 mục thuộc năm cặp phụ lục trùng title**; chuyển “Toàn bộ nguồn” để xem 542 mục. Mỗi trang tối đa 25 mục.

1. Điền tên người thực sự review và provenance/tham chiếu bằng chứng.
2. Đối chiếu source ID, nhóm:số, title, ấn bản và audio song ID chính xác. Main464 không tự điền audio ID vì title conflict. Năm cặp phụ lục không được gộp ấn bản chỉ vì cùng title.
3. Chọn approve/reject/defer, ghi evidence cho **từng** mục và đánh dấu đã kiểm tra. Chỉ defer được để audio ID trống. Nếu chưa đủ bằng chứng, defer và ghi rõ thiếu gì.
4. “Xuất batch” tạo đề xuất JSON tối đa 50 quyết định. Đóng/reload trang làm mất phần chọn chưa xuất. Chưa có quyết định nào được lưu chỉ bằng thao tác trên trang.
5. Chép file đề xuất tải từ browser thành `reviews/sheet-review-batch.json`; giữ nguyên catalog pins và baseRevision.

Trang HTML đã được kiểm thử parser/escaping và chạy constructor batch thực bằng Node.js. **Chưa kiểm tra render/thao tác bằng Browser Use:** công cụ chặn protocol `file:` theo browser security policy; không dùng máy chủ hoặc bề mặt khác để né chặn. Người dùng tự mở file local để review giao diện. Đây là giới hạn kiểm chứng giao diện, không phải lỗi quyền truy cập BookVN.

## Dry-run và áp dụng batch có kiểm soát

```powershell
# Không ghi decision store.
.\.venv\Scripts\python.exe -X utf8 scripts\review-mapping.py batch --input reviews/sheet-review-batch.json

# CHỈ khi bạn đã kiểm tra cả batch. N phải đúng số quyết định trong file.
$reviewCount = (Get-Content reviews/sheet-review-batch.json -Raw | ConvertFrom-Json).decisions.Count
.\.venv\Scripts\python.exe -X utf8 scripts\review-mapping.py batch --input reviews/sheet-review-batch.json --apply --confirm-count $reviewCount

.\.venv\Scripts\python.exe -X utf8 scripts\review-mapping.py status
.\.venv\Scripts\python.exe -X utf8 scripts\review-mapping.py export
.\.venv\Scripts\python.exe -X utf8 scripts\review-mapping.py html
```

Lệnh apply là hành động của người dùng, không được gọi tự động từ UI hoặc Codex cho catalog thật. `reviewed:true`, reviewer/evidence/provenance bắt buộc; một batch chỉ có một quyết định cho mỗi cặp source/audio, không quá 50. `--confirm-count` sai thì FAIL, store giữ nguyên. Batch stale revision hoặc catalog pins thì phải tạo lại view và review lại, không sửa pin chỉ để ép qua kiểm tra.

## Review một mục bằng CLI

Ví dụ dưới đây chỉ **defer** bài 464, không tuyên bố hai bản là cùng tác phẩm. Mặc định dry-run:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\review-mapping.py decide --sheet bookvn:vi:post:77217 --decision defer --reviewer 'TEN_NGUOI_REVIEW' --evidence 'Cần đối chiếu title ĐiCon với Đi Con và xác minh nội dung/ấn bản.' --provenance 'BIEN_BAN_HOAC_NGUON_KIEM_TRA' --reviewed
```

Source ID trên được đối chiếu với catalog hiện tại; CLI từ chối ID không tồn tại. Sau khi chính bạn review, thêm `--apply` để lưu defer. Để approve/reject một cặp, dùng `--song <exact-song-id>` và `--decision approve` hoặc `reject`, evidence đúng việc đã kiểm tra. Không có command bulk-approve tự động. Không dùng placeholder làm bằng chứng cho quyết định thật.

Approve xác nhận **cùng tác phẩm**, không xác nhận hai bản in/ảnh có cùng bytes hoặc cùng ấn bản. Mỗi source có tối đa một audio song đang approve; guide/instrumental nằm trong variants của song, không phải hai mapping độc lập. Muốn đổi song, reject cặp cũ rõ ràng rồi approve cặp mới, **kể cả khi đã defer cặp cũ**; có thể làm trong một batch theo thứ tự, hai cặp khác nhau. Nhiều source/ấn bản có thể cùng link tới một song; vẫn giữ tất cả source ID.

Reject/defer về sau trên cùng cặp sẽ ngừng export approve cũ nhưng lịch sử vẫn còn. Defer không có song chỉ ghi việc chưa quyết định ở cấp nguồn, không tự thu hồi một approve khác có song; muốn đình chỉ approve đó phải defer/reject đúng cặp source/song.

## Stale, FAIL và API tương lai

- Thay đổi định danh source/title/edition/nội dung quan sát hoặc dữ liệu audio của một approve làm export FAIL: re-review cặp đó với bằng chứng mới. Thay đổi quyền không tự thành approve/revoke định danh; export luôn sao quyền hiện tại.
- Store sai schema/hash/chain/timestamp/ID hoặc batch thiếu evidence/không reviewed đều FAIL. Không ghi nửa batch. Khôi phục backup khi store hỏng, không xóa/reset để bỏ lịch sử.
- Export có `reviewRevision`, catalog/audio SHA và `decisionEventHash` để hệ thống API kiểm tra pin. Export là snapshot tại thời điểm chạy, phải tạo lại sau review; API cần từ chối export cũ/khác catalog.
- Quyền `restricted` vẫn giữ nguyên kể cả mapping verified. Frontend/API phải kiểm tra quyền serve/upload riêng, không dựa riêng vào status verified. Chưa triển khai rights decision store, Worker hay app.
- `init` chỉ dùng khi chưa có store; từ chối ghi đè store hiện hữu. `--root`/`--store` cho phép môi trường thử riêng, output giới hạn `reviews/sheet-*` hoặc `delivery/sheet-*`, chặn hard-link/symlink/junction và trùng input.
- Exit 0: validation/dry-run/apply/export thành công; exit 1: FAIL và thông báo; exit 2: sai CLI. `status` cũng FAIL nếu còn approved identity stale; dùng `queue`/HTML để xem cặp và review lại.

## Kiểm thử offline

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_sheet_review.py -v
```

Mọi approve trong test chỉ dùng catalog fixture ở thư mục tạm. Catalog/store thật vẫn 0 verified cho đến khi người dùng tự review/apply.
