# B10 — Verification do người dùng chạy

**Cập nhật 12/10/2026:** đã bổ sung kiểm thử offline theo yêu cầu mới, không chạy live B10. Xem phần preflight cuối tài liệu. Các mô tả “chưa test” bên dưới là lịch sử chuẩn bị ngày 11/10, không phải trạng thái bộ test hiện tại.

## Phạm vi và thiết kế

Chuẩn bị ngày 2026-10-11. **Chưa chạy B10, chưa có kết luận PASS/FAIL về R2 trong bước chuẩn bị này.** Người dùng báo bulk B9 đã hoàn tất. Kiểm tra local chỉ đọc xác nhận manifest có 983 asset, SHA-256 vẫn là `b54965fd3c612439ba2ef503bd502abbab11fadcd6b1e16857c2ef0403051a4c`; state có 983 verified và 5 dòng có bằng chứng GET trước đây. Các số này không thay thế audit remote.

Công cụ hiện có không đáp ứng audit độc lập: `upload-r2.py` có thể PUT và ghi state; `validate-delivery.py` chỉ audit local. Script riêng `scripts/verify-r2.py` tái sử dụng loader manifest đã pin, config, credential loader và client B9; không tái sử dụng logic upload hoặc trạng thái verified để quyết định PASS.

Kế hoạch thực hiện đã giới hạn trong yêu cầu B10:

1. Đọc mã uploader/validator, cấu trúc manifest và SQLite bằng mode=ro.
2. Thêm một script riêng: LIST toàn bộ bucket có phân trang, so tập key, HEAD từng asset với 2 workers mặc định.
3. Chỉ kiểm tra cú pháp và rà soát mã tĩnh khi chuẩn bị; **không chạy script, không chạy test B10, không gọi R2** theo yêu cầu người dùng. Không có kết quả runtime/test được tuyên bố ở bước này.
4. Bàn giao command/report/FAIL guidance rồi dừng. Không đổi credential, bucket, state, catalog hoặc manifest.

Kiểm tra chuẩn bị đã thực hiện: parse AST/cú pháp script và rà soát tĩnh các thao tác API, không import/thực thi script; không thấy lời gọi GET/PUT/DELETE/COPY hoặc logic ghi upload state. Manifest/catalog giữ nguyên SHA-256 baseline. Script chưa được kiểm thử runtime theo giới hạn người dùng đặt ra.

## Quyền đọc và hash

Script chỉ cho phép SDK operations `ListObjectsV2` và `HeadObject`, chặn operation khác trước khi tạo request. **Credential hiện hữu vẫn là Object Read & Write**, không bị thay đổi; đây là giới hạn thao tác trong script, không phải chuyển credential thành quyền read-only ở Cloudflare. Script không gọi GET, PUT, COPY, DELETE hoặc thay metadata/public access. Chỉ tạo báo cáo local mới dưới `logs/r2-verification/` (đã nằm trong rule ignore `logs/`). Không mở/ghi SQLite upload/download.

SHA-256 trong custom metadata được đối chiếu chính xác với manifest đã review/pin, cùng `asset-id` và kích thước. Metadata do uploader ghi, không phải checksum SHA-256 do B10 tự tính từ remote bytes. Vì vậy báo cáo luôn ghi `contentSha256Verified: false` và `hashVerification: metadata-match-only`. ETag chỉ dùng phát hiện khác biệt LIST ↔ HEAD, không được diễn giải là SHA-256.

Không có fallback tự download để hash. Nếu cần xác minh nội dung độc lập sau khi xem kết quả, phải thông báo và thống nhất phạm vi trước một bước riêng; script này không có cờ tải nội dung.

## Chạy bằng PowerShell

Dùng `.venv` B9 hiện có; không cần activate hoặc cài dependency mới.

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 scripts/verify-r2.py --workers 2
$LASTEXITCODE
```

Chạy sau khi uploader kết thúc; tránh thay đổi object trong lúc audit. Script LIST **toàn bucket**, không giới hạn prefix, nên phát hiện cả object thừa nằm ngoài `audio/v1/watv/vi/`. Khi phân trang LIST thất bại/duplicate key/token lặp, kết quả FAIL, `inventoryComplete: false`; actual/missing không được kết luận từ một inventory chưa đầy đủ. Những object thiếu hoặc lỗi HEAD không được tự sửa.

HEAD kiểm tra đúng key, Content-Length, `sha256`, `asset-id`, Content-Type `audio/mp4`, size và opaque ETag nhất quán với LIST. Mỗi request được thử tối đa 3 lần khi lỗi transient, lỗi permanent không retry. Mặc định 2 worker (cho phép 1–4); HEAD tiến độ in mỗi 100 object. Ctrl+C dừng nhận việc mới và chờ tối đa các request đang chạy theo timeout; báo cáo partial là FAIL/exit 130, không được coi là audit hoàn tất. Đóng cưỡng bức terminal có thể chưa kịp ghi report; chạy lại cùng command để audit mới, không có dữ liệu R2 cần khôi phục.

Mỗi lần chạy tạo một thư mục timestamp UTC + mã ngẫu nhiên mới, giữ báo cáo cũ. Đây là kết quả trong khoảng thời gian LIST/HEAD, không phải snapshot transaction toàn bucket; thay đổi đồng thời có thể gây FAIL hoặc cần chạy lại sau khi hết thay đổi.

## Xem và hiểu báo cáo

Console in tiến độ, PASS/FAIL, số đếm và đường dẫn `Report: ...\report.json`. Mở đúng file console chỉ ra. Có thể xem báo cáo mới nhất:

```powershell
cd D:\Workspace\AudioTP
$b10Report = Get-ChildItem -LiteralPath .\logs\r2-verification -Recurse -Filter report.json -File | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
if ($null -ne $b10Report) { Get-Content -LiteralPath $b10Report.FullName -Raw }
```

PASS yêu cầu `inventoryComplete: true`, `expected = actual = checked = matched = 983`, tất cả `missing`, `extra`, `mismatched`, `headErrors`, `errors` bằng 0. `checked` là số asset đã xử lý HEAD (gồm lỗi); `matched` là số khớp toàn bộ kiểm tra. `mismatched` là số HEAD thành công nhưng khác size/metadata/type/LIST; `headErrors` gồm missing 404 và lỗi quyền/network. Các số lỗi có thể chồng lấp, không cộng để suy ra tổng asset.

- Exit `0`: PASS về inventory/key/size/metadata; không phải full-content SHA audit.
- Exit `1`: FAIL, có sai lệch/lỗi hoặc không ghi được báo cáo. Lỗi trước khi khởi tạo báo cáo có thể chỉ in FAIL trên console.
- Exit `130`: người dùng ngắt; audit chưa hoàn thành.
- Exit `2`: command/flag không hợp lệ, chưa audit.

JSON có `missingKeys`, `extraKeys`, `objects[].issues`, `objects[].checks` và `errors` để phân biệt vấn đề; không lưu arbitrary remote metadata hoặc raw exception/credential. Nếu credential xuất hiện trong tên object bất thường, giá trị được che trong report.

## Nếu FAIL

1. `remote_http_403`: kiểm tra đang dùng đúng account/bucket và token còn hiệu lực/quyền LIST/HEAD. Không kết luận object thiếu từ 403, không tự đổi credential.
2. `network_connection`, HTTP 408/429/5xx hoặc `interrupted`: giữ báo cáo, ổn định mạng/chờ uploader kết thúc rồi chạy lại cùng command. Retry có giới hạn; không có mutation.
3. `missingKeys`/`missing_head`: đối chiếu các key trong report với manifest. Giữ nguyên state và báo cáo để review phương án khôi phục; **không tự chạy uploader** vì việc sửa R2 nằm ngoài B10 này.
4. `extraKeys`: review mục đích từng key; không tự xóa.
5. `size`, `list_size`, `metadata_sha256`, `metadata_asset_id`, `content_type`, `list_head_etag` hoặc `listed`: đối chiếu report/manifest và xem có tác vụ đang thay object hay không. Không sửa metadata/ghi đè. SHA metadata không khớp thì FAIL; chỉ xét GET/hash sau khi thông báo phạm vi riêng.
6. `unreviewed_delivery_manifest`, `invalid_target_config`, lỗi secret file: kiểm tra đúng project và input đã review. Không tự sửa manifest pin hoặc đưa secret vào chat.
7. `invalid_or_changing_inventory`/`invalid_inventory_pagination`: inventory chưa đáng tin hoặc bucket thay đổi khi đọc; không coi số thiếu/thừa là kết luận đầy đủ. Giữ report rồi audit lại khi bucket ổn định.

Gửi summary và các issue/key cần review; không gửi `.secrets/r2.env`, access key hoặc secret key.

## File được thêm

- `scripts/verify-r2.py`
- `docs/r2-verification.md`

## Preflight offline — 12/10/2026

Theo yêu cầu mới, đã thêm `tests/test_verify_r2.py` và chạy mock tests; **chưa chạy live B10 và chưa có verdict mới về R2**. Test dùng client S3 giả, credential chuỗi synthetic, config/report/state trong thư mục tạm; real `.secrets/r2.env` không được mở. Test SDK dùng boto3 service model + Stubber và chặn transport, không gửi request.

Đã kiểm tra LIST hai trang/token continuation, toàn bucket không Prefix/Delimiter, token thiếu/lặp, key trùng, response/size sai kiểu; HEAD size/sha256/asset-id/content-type/LIST-HEAD ETag; missing/extra/404, 403 không bị hiểu thành missing, retry 429/500/503 có giới hạn, interrupted/partial FAIL. Test mock main kiểm tra exit 0/1, report JSON, redaction, không đọc secret thật hoặc sửa upload state. SDK guard thử mọi S3 operation trong service model: chỉ ListObjectsV2/HeadObject được qua, tất cả GET/PUT/DELETE/COPY/multipart/bucket operations bị chặn trước transport.

Các lỗi phát hiện và sửa: từ chối duplicate expected asset IDs/keys trước LIST; malformed HEAD metadata thành FAIL row thay vì exception làm gián đoạn audit; lỗi đóng client vẫn được lưu vào report FAIL. Responses LIST sai kiểu có mã lỗi tĩnh riêng. Không đổi CLI, manifest pin, credential loader hoặc uploader. Không thêm tải nội dung hay ghi state.

Review độc lập phát hiện thêm ETag LIST/HEAD sai kiểu nhưng bằng nhau có thể PASS. Đã tái hiện bằng integer/list/dict/bool/blank ETag và sửa yêu cầu cả hai là string không rỗng; lỗi LIST `invalid_inventory_etag` là FAIL inventory chưa hoàn tất. ETag vẫn chỉ là opaque change detector, không phải hash SHA-256.

Mock suite riêng hiện 12 test PASS; log `tmp/review-b10-final-green.log`. Kết quả toàn project và review độc lập ghi trong `docs/audit-mapping-handoff.md`. Command B10 ở trên là **người dùng tự chạy**, không được chạy như một phần test offline. Dependency dùng `.venv` B9, không cài mới.

Tài liệu đã đối chiếu qua Context7: [boto3 paginators](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/paginators.html), [boto3 events](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/events.html), [Cloudflare R2 S3 API](https://developers.cloudflare.com/r2/api/s3/api/).
