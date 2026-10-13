# AudioTP private media API 0.2

Worker đã deploy theo phê duyệt vào account đích; health/auth/CORS live PASS và người dùng báo ONLINE hoạt động/tự kết nối lại. Kiểm tra authenticated Range/R2 đầy đủ còn pending, không coi health là storage probe. R2 bucket vẫn private. Chỉ `MEDIA.head/get` được dùng; không LIST/PUT/DELETE/COPY. Server allowlist giữ nguyên assetId/objectKey; client không gửi/nhận object key. [ONLINE report](../../docs/phase02-online-beta.md).

## Routes và xác thực

- `GET/HEAD /v1/health`: readiness không đọc R2; 503 khi serving chưa bật/cấu hình thiếu. `storage: not-probed` không chứng minh bucket đang truy cập được.
- `POST /v1/auth/login`, JSON `{ "code": "mã nhóm do người quản lý cấp" }`: trả phiên HMAC, mặc định tối đa12 giờ. Mã đầu vào được SHA-256 và so bằng `timingSafeEqual`; session/ticket giữ RAM. Windows client có tùy chọn nhớ group code bằng DPAPI current-user/origin, không plaintext/localStorage; logout xóa mã nhớ.
- `GET/HEAD /v1/catalog`: Bearer session, metadata 983 asset; không có R2 key, HLS source hoặc đường local.
- `GET/HEAD /v1/songs/<encoded logicalId>`: metadata các variant của cùng bài; silent giữ ID riêng.
- `POST /v1/play-tickets`, Bearer + JSON `{ "assetId": "..." }`: vé gắn một asset, revision, session và epoch. TTL = duration + 600 giây, trong khoảng 300–3600 giây và không quá phiên.
- `GET/HEAD /v1/media/<encoded assetId>?ticket=...`: thẻ HTML audio dùng vé trong URL, không cần Bearer header/cookie. Vé không chứa object key và không cấp quyền ghi.

Full 200; single/suffix/open range 206; Range sai hoặc không thỏa 416; phiên/vé sai/hết hạn 401; nguồn serving chưa được bật, CORS hoặc scope sai 403; asset/route không có 404; metadata sai/đổi trong lúc đọc 409; giới hạn 429; backend/cấu hình thiếu 503. HEAD media bỏ qua Range và không gọi GET. If-None-Match/ETag hỗ trợ 304; If-Range khớp ETag mới trả range, validator khác trả full. Không hỗ trợ multipart range. Không tự lấy bytes để tính remote SHA toàn file.

R2 HEAD/GET được đối chiếu size, metadata `sha256`/`asset-id`, Content-Type và ETag; GET dùng conditional ETag để chặn thay object giữa hai request. Metadata SHA khớp **không phải** hash nội dung remote độc lập. [R2 Workers API](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/)

## Quyền và giới hạn

Mặc định `SERVING_ENABLED=false`: chưa cấp quyền phục vụ production. Secrets `GROUP_CODE_SHA256` và `SIGNING_KEY` chỉ ở Worker. Không dùng uploader access key; R2 binding phía server. `AUTH_EPOCH` hoặc đổi signing key thu hồi toàn bộ phiên/vé. Mô hình hiện tại là **một mã nhóm**, chưa có quản lý thành viên/thu hồi từng cá nhân; đổi mã kèm signing key để thu hồi nhóm cũ.

Origin allowlist chính xác cho Tauri; không wildcard, không third-party cookie. Vé phát là bearer URL trong hạn sử dụng, nên không đưa vào log/ảnh/report. Worker observability mặc định tắt để không ghi URL có vé; code không log request, body hoặc env. Rate binding: login 10/phút/IP, request khác 180/phút/IP, có Retry-After. Đây là giới hạn theo Cloudflare location, **không phải quota toàn cầu**; kiểm tra namespace ID không trùng binding khác trong account trước deploy. [Rate limiting binding](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/)

Mọi response trả `private, no-store` và CDN no-store; không dùng Cache API. App chỉ reuse tối đa 16 ticket còn hạn trong RAM, không có disk cache audio hoặc bulk prefetch. Một player buffer theo cơ chế browser/WebView2. Cache metadata xác minh của adapter local giới hạn 16 entry, không lưu bytes audio. Caching audio LRU lâu dài chưa được triển khai/bật.

## Test offline/local — đã chạy

Clone source không cần private JSON để typecheck/test: `npm.cmd run typecheck` và `npm.cmd test` trong package này. Test workerd tổng hợp seed bytes tự tạo trong R2 mô phỏng cô lập; hai integration production SKIP rõ lý do khi thiếu manifest/bundle. Không tạo generated production JSON và không thay audio thật. Bundle production vẫn cần inputs hợp lệ như dưới đây.

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 scripts/prepare-worker.py
cd workers\media-api
npm.cmd ci --ignore-scripts
$env:WRANGLER_SEND_METRICS = 'false'
$env:WRANGLER_LOG_PATH = 'D:\Workspace\AudioTP\tmp\wrangler-logs'
npm.cmd run typecheck
npm.cmd run check
npm.cmd test
```

`check` thực tế là `wrangler deploy --dry-run`; không deploy. Test runtime cần bundle từ `check`. Test mock dùng payload tổng hợp; HTTP integration đọc đúng ba M4A local đại diện và so full SHA; test workerd dùng **R2 mô phỏng cô lập**, seed một M4A local, không ghi bucket thật. Không chạy toàn bộ 983 download/hash hoặc truy cập `.secrets/r2.env`.

Wrangler 4.149.0, Workers types 5.20261011.1, TypeScript 7.0.2 được khóa trong package-lock. Miniflare 5.20261006.1-alpha đi cùng toolchain và được pin riêng cho test; dùng converter V4 được public export bởi phiên bản này. Runtime test không phải production deployment.

## Nghe đúng audio hiện có trên máy

```powershell
cd D:\Workspace\AudioTP
node workers/media-api/local-preview.mjs
```

Hoặc command Python cũ `apps/windows/serve.py` nay gọi adapter này. Mở `http://127.0.0.1:8766/`. Adapter chạy cùng handler Worker nhưng R2 binding được thay bằng bộ đọc file **read-only**, lấy đường từ manifest đã pin, kiểm tra size/full SHA khi file được chọn. Không copy 983 file vào app. Local bootstrap chỉ tồn tại ở adapter loopback, bị chặn Host/cross-site, không có route đó trên Worker production. Khóa local ngẫu nhiên mỗi lần khởi động; client local có thể bootstrap lại một lần sau restart. Không nhúng mã nhóm production vào adapter/frontend.

Nếu cổng bận: `node workers/media-api/local-preview.mjs --port 8767`. Adapter không phục vụ source, manifest, credential, directory listing hoặc WAV demo; các URL ngoài danh sách web/public API bị từ chối. Đây là bản nghe cá nhân trên máy có media, **không thay thế EXE online cho bạn bè**.

## Deploy — CHỈ người dùng thực hiện sau review

Quy trình đầy đủ, giới hạn auth/cache/chi phí, bootstrap secret và rollback nằm tại [Phase 01 operations](../../docs/phase01-operations.md). Chưa được chạy live trong Codex. Có báo cáo B10 user-run PASS ngày 11/10/2026 (983 metadata khớp); đây không phải audit mới hay SHA nội dung remote.

Trước hết chạy B10 nếu chưa có báo cáo, xem kết quả/đối chiếu quyền phục vụ nhóm. B10 vẫn là audit metadata, không full SHA remote:

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 scripts/verify-r2.py --workers 2
```

Sau khi đồng ý triển khai Worker, tự chạy trong PowerShell:

```powershell
cd D:\Workspace\AudioTP\workers\media-api
npm.cmd exec -- wrangler login
```

Đăng nhập Cloudflare bằng browser của chính bạn, không gửi token qua chat. **Cấu hình required secrets trước lần deploy đầu tiên**; deploy sẽ bị từ chối nếu thiếu secrets.

Mã nhóm hiện hỗ trợ 4–256 ký tự, so khớp chính xác (không trim), không ký tự điều khiển. Người quản lý đã chọn mã ngắn cho nhóm nội bộ; rate limiting vẫn chỉ theo IP/location, không bảo đảm chống đoán phân tán. Không nhúng mã/hash thật vào source, EXE hoặc ví dụ. Cập nhật chỉ mã bằng `--code-only` giữ nguyên signing key; đổi `AUTH_EPOCH` sang giá trị mới để thu hồi phiên/vé cũ.

Tạo hai secret auth riêng bằng script interactive đã có (không dùng hoặc thay R2 credentials):

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 scripts/configure-worker-secrets.py --apply --account-id $env:CLOUDFLARE_ACCOUNT_ID
```

Script hỏi mã nhóm 4–256 ký tự hai lần với input ẩn, chỉ gửi hash mã và signing key ngẫu nhiên qua stdin của Wrangler, không in/lưu các giá trị. Không có `--code-only` sẽ đổi signing key; có `--code-only` chỉ đổi hash mã và giữ phiên hiện tại tới khi hết hạn hoặc tăng epoch. Dry-run là mặc định. [Worker secrets](https://developers.cloudflare.com/workers/configuration/secrets/)

Nếu Worker chưa tồn tại, Wrangler secret put có thể tạo draft Worker tối thiểu; việc này cũng cần quyền deploy đã duyệt. Sau khi secrets tồn tại, chạy `npm.cmd run deploy` trong workers/media-api với serving vẫn false, ghi đúng URL/version trả về. Secret put cho Worker đã tồn tại có thể deploy thay đổi ngay; không chạy lại helper chỉ để kiểm tra.

Review `wrangler.jsonc`: bucket đúng `audiotp-media`, namespace rate limit không trùng, origin đúng, quyền phục vụ đúng phạm vi. Sau khi đã xác nhận, tự đổi **`SERVING_ENABLED` thành `"true"`**, rồi:

```powershell
cd D:\Workspace\AudioTP\workers\media-api
npm.cmd run deploy
```

Không public bucket hoặc thêm R2 access key vào app. Sau deploy, thử API thật và EXE thật với quyền hợp lệ; kiểm tra cả 401/403, seek, expired ticket, logout và Range trước khi chia sẻ nhóm. Đổi `AUTH_EPOCH` rồi redeploy nếu cần thu hồi tất cả mà không thay key. Chưa có lệnh deploy nào được chạy trong phiên chuẩn bị này.
