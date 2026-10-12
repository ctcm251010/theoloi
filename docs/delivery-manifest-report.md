# B8 — Delivery manifest

B8 status: **PASS**. Chỉ tạo manifest và công cụ kiểm tra offline. Chưa thực hiện B9.

| Chỉ tiêu | Kết quả |
|---|---:|
| Catalog assets | 983 |
| Delivery assets | 983 |
| Guide | 485 |
| Instrumental | 485 |
| Meditations | 13 |
| Total bytes | 2.506.137.889 |
| Total size readable | 2,506 GB / 2,334 GiB |
| Unique SHA-256 | 983 |
| Unique object keys | 983 |
| Missing assets | 0 |
| Unexpected state/media assets | 0 |
| Duplicate IDs / final paths / object keys | 0 / 0 / 0 |
| Hash mismatches / invalid files | 0 / 0 |
| Validator | PASS, exit 0 |

- Delivery manifest: `delivery/manifest.vi.json` — UTF-8, 696.660 bytes.
- Manifest SHA-256: `b54965fd3c612439ba2ef503bd502abbab11fadcd6b1e16857c2ef0403051a4c`.
- Catalog SHA-256: `e449b3a25ed49c6879bf06c72219863857632491f4a2ca424c2bc692e45ca8d4` — giữ nguyên.
- Revision: `sha256:09594059b6a06e389ee15b3eaa530ed2567c1a32cd258442fe3e3aa5e3baef44`.
- Generated at: `2026-10-10T18:41:43.747378+00:00` (11/10/2026 theo giờ Việt Nam).

## Kiểm tra thực tế

SQLite `quick_check = ok`. Tất cả 983 record đều `completed`, có probe và decode verification thành công. Đọc SQLite bằng `mode=ro`; không gọi hàm đăng ký/retry/update của downloader.

Builder và validator giữ cùng OS lock `state/download-media.lock` với downloader để tránh chạy đồng thời. Mỗi lần chạy đều đọc lại toàn bộ 983 final file, kiểm tra size và SHA-256 thực tế với state, đối chiếu fingerprint/source/profile/identity với catalog, rồi so metadata đo được trong state với JSON bằng chứng FFprobe B7. Kiểm tra cả tập file trong media root để phát hiện file thừa và partial; từ chối symlink/junction. Nếu không thể đọc đủ một thư mục, audit fail thay vì bỏ qua.

B8 sử dụng bằng chứng probe/decode B7 đã có, gắn với bytes vừa được hash lại; **không chạy lại FFmpeg/FFprobe, không remux/transcode, không tải audio**. Media, catalog, source và transfer state được bảo toàn. Không có trường retry/error/status/progress hay URL HLS trong delivery manifest.

## Model đã chốt

`assets` là map theo `assetId`; mỗi entry có `logicalId`, `kind`, `audioId`, `variant`, `localPath`, `objectKey`, `bytes`, `sha256`, `durationSeconds`, `codec`, `sampleRate`, `channels`, `container`. Song có thêm `section` và `number`. Meditation dùng `kind=meditation`, `variant=silent`, logical identity riêng `watv:vi:silent:<audioId>`, không có section/number và không thuộc variants của song.

`localPath` dùng dấu `/`, tương đối từ **project root**. B9 có thể resolve bằng `projectRoot / localPath`. State B6/B7 hiện vẫn lưu absolute paths; khi chuyển cả workspace sang máy/thư mục khác, cần xử lý state riêng trước khi chạy lại kiểm tra B8. Manifest và object key không chứa absolute path.

Object key giữ nguyên thiết kế được yêu cầu:

```text
audio/v1/watv/vi/newsong/main/<number:04d>/<guide|instrumental>/<audioId>/<sha256>.m4a
audio/v1/watv/vi/newsong/appendix/<number:04d>/<guide|instrumental>/<audioId>/<sha256>.m4a
audio/v1/watv/vi/meditations/<audioId>/<sha256>.m4a
```

SHA trong key được tính trực tiếp từ file và phải khớp SHA B7. File đổi bytes sẽ có key mới khi state được verify lại. Không dùng index để nhận dạng bài. Main và appendix giữ namespace riêng, kể cả khi cùng number.

`revision` là SHA-256 của JSON canonical: bỏ `revision` và `generatedAt`, sort toàn bộ keys, UTF-8, `ensure_ascii=False`, `separators=(",", ":")`, không NaN/Infinity. Bao gồm catalog SHA và toàn bộ asset metadata. Build lại cùng nội dung giữ revision/object keys; `generatedAt` thay đổi nên hash toàn file manifest có thể thay đổi. `outputProfile` ghi profile AAC stream copy/M4A/faststart của B6/B7; các field codec/sample rate/channels trong asset là giá trị thực đo.

Schema Draft 2020-12 từ chối field lạ ở mọi cấp và phân biệt song/meditation. Validator bổ sung count chính xác 983/485/485/13, đối chiếu từng field với catalog/state/file, uniqueness và content revision. Profile/catalog B3 đang được pin có chủ đích: khi WATV thêm bài cần review catalog và baseline/counts; B8 không tự chấp nhận phiên bản chưa review.

## Representative records

Đã kiểm tra đủ 5 record sau với catalog, state, bytes và SHA thực tế:

| Content | Variant | Asset ID | Bytes | Measured seconds | Sample rate |
|---|---|---|---:|---:|---:|
| main:1 | guide | watv:vi:guide:4177 | 2.027.172 | 125.016236 | 44100 |
| main:1 | instrumental | watv:vi:instrumental:17407 | 2.030.903 | 125.248435 | 44100 |
| appendix:1 | guide | watv:vi:guide:25495 | 2.904.864 | 120.064 | 48000 |
| appendix:1 | instrumental | watv:vi:instrumental:25464 | 1.931.264 | 119.373787 | 44100 |
| meditation 19965 | silent | watv:vi:silent:19965 | 694.429 | 42.794376 | 44100 |

Ví dụ key thực tế main:1 guide:

```text
audio/v1/watv/vi/newsong/main/0001/guide/4177/ff9c2ad0d53e908a1f156561f15c16f00894b8b59f072324ee5aa53151d63393.m4a
```

Không có artifact `main:34`. Các số main không tồn tại trong catalog: 34, 242, 300, 306, 367; validator không lấp số thiếu. Có 480 main songs và 5 appendix songs, mỗi song có guide + instrumental.

## Phân bố và warnings

| Metadata đo thực tế | Phân bố |
|---|---|
| Codec / container | AAC / M4A: 983 |
| Sample rate | 44100 Hz: 977; 48000 Hz: 6 |
| Channels | Stereo, 2 channels: 983 |
| Duration range | 40.263401–337.873560 giây |

Warnings: **12 assets** có duration đo được lệch metadata catalog trên 2 giây. Đây là warning B7, không phải lỗi hash/decode. Chênh lệch dưới đây = measured output − catalog duration, đơn vị giây. Catalog không bị sửa; delivery dùng measured duration.

| Asset ID | Delta seconds |
|---|---:|
| watv:vi:guide:16644 | -2.023673 |
| watv:vi:guide:4105 | -3.084354 |
| watv:vi:guide:16617 | -3.133696 |
| watv:vi:guide:16615 | +2.124898 |
| watv:vi:guide:4446 | -2.607256 |
| watv:vi:guide:4055 | -3.378503 |
| watv:vi:instrumental:17741 | -19.426122 |
| watv:vi:instrumental:17749 | -19.123084 |
| watv:vi:guide:4117 | -3.155465 |
| watv:vi:guide:4110 | -2.229660 |
| watv:vi:guide:4008 | -2.237460 |
| watv:vi:instrumental:17858 | +10.714921 |

## Commands và kiểm thử

Đã chạy builder và validator trên toàn bộ dữ liệu thật, exit 0:

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe scripts/build-delivery.py
.\.venv\Scripts\python.exe scripts/validate-delivery.py
```

Builder chỉ atomic replace manifest sau khi toàn bộ audit/schema/semantic checks thành công; không xuất manifest thiếu bài. `--output` chỉ nhận file `.json` trong `projectRoot/delivery`, từ chối trùng input hoặc qua symlink/junction, để bảo toàn catalog/source/state/media. Validator không tạo/sửa manifest, exit nonzero khi sai. Không cần FFmpeg hay dependency mới; dùng `.venv` hiện có và `requirements.txt` đã pin jsonschema.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Kết quả cuối: 43 tests, 42 PASS, 1 SKIP. Test tạo Windows file symlink bị skip do tài khoản không có quyền tạo symlink; hai test Windows directory junction chạy thật và PASS. Các test khác kiểm tra hash sai cùng size, thiếu/thừa file/state, duplicate, non-completed, malformed proof, sai profile/identity, count thiếu, namespace, metadata bị sửa, path tmp/absolute/traversal, field transfer/HLS, revision, database read-only, lock contention và atomic write thất bại. Tests dùng file giả nhỏ trong thư mục tạm, không thao tác media thật.

Review độc lập tìm thấy hai vấn đề trong công cụ: lỗi scan thư mục bị bỏ qua và output path có thể ghi nhầm lên input. Đã tái hiện cả hai bằng tests RED, sửa trong một lượt rồi chạy lại suite GREEN và validator toàn bộ 983 file. Không còn finding cần sửa hoặc minor bị hoãn. Bản build cuối giữ nguyên content revision/object keys; hash manifest đổi vì `generatedAt` mới.

## Files created

```text
delivery/manifest.vi.json
schemas/delivery.schema.json
scripts/delivery_lib.py
scripts/build-delivery.py
scripts/validate-delivery.py
tests/test_delivery.py
docs/delivery-manifest-report.md
docs/superpowers/plans/2026-10-11-delivery-b8.md
```

Ready for B9 Cloudflare R2: **YES** — dữ liệu B8 đã sẵn sàng; chưa upload hay cấu hình Cloudflare. Dừng tại B8 để người dùng review.
