# Phase 01 — Vận hành API private và đề nghị deploy

Ngày review: 12/10/2026. **Chưa được phê duyệt/chưa chạy deploy hoặc live E2E.** Các lệnh live bên dưới là bàn giao cho người quản lý sau khi duyệt, không phải công việc Codex đã thực hiện.

**Cập nhật 13/10/2026:** người dùng đã duyệt triển khai Worker/API private và bản Windows online trong account `ctcm251010`, thao tác bằng member `nguyenducbang.uit`. Bản review ở trên là lịch sử trước phê duyệt; chưa có bằng chứng deploy/live PASS. Bucket và member Active đã đối chiếu qua dashboard; OAuth Wrangler cũ chưa thấy account đích, đang chờ người dùng Authorize riêng account này. Xem [checklist live](superpowers/plans/2026-10-13-phase02-live-online.md). Không cần mời lại hoặc tăng quyền khi policy hiện có đã bao gồm quản trị.

**Kết quả sau phê duyệt:** OAuth và user-run secrets đã hoàn tất; Worker đã deploy, source serving false được giữ nguyên, live bật bằng `--var SERVING_ENABLED:true`. Endpoint thực `https://audiotp-media-api.ctcm251010.workers.dev`. Health200, no-auth401, wrong-code401, foreign-origin403, preflight204; authenticated R2/native acceptance còn pending. Không chạy lại helper secrets để kiểm tra vì sẽ rotate key. Mã user chọn Nhớ đăng nhập chỉ được native Windows DPAPI lưu mã hóa theo user/origin; session/ticket giữ RAM. Xem [nghiệm thu ONLINE](phase02-online-beta.md).

Để redeploy live đúng cấu hình đã duyệt: set `$env:CLOUDFLARE_ACCOUNT_ID` từ `config/r2.json` đã đối chiếu, tại `workers/media-api` chạy `node node_modules/wrangler/bin/wrangler.js deploy --strict --var SERVING_ENABLED:true`. Deploy không override sẽ đưa serving về false. Emergency stop: source false + override epoch mới chưa dùng; không rollback về epoch cũ hoặc rotate secret chỉ để xem trạng thái. Version IDs giữ trong journal local, không đoán URL/version hoặc mở public bucket.

## Cấu hình đem review

| Thành phần | Hiện tại / giới hạn |
|---|---|
| Worker | `audiotp-media-api`, Wrangler 4.149.0 đã khóa |
| Binding | `MEDIA` → `audiotp-media`; production code chỉ `head/get` |
| Đối tượng | Allowlist 983 ID/key chính xác từ manifest đã pin; không LIST hoặc nhận arbitrary key |
| Khóa phục vụ | `SERVING_ENABLED=false`; không đổi trong Phase 01 |
| Auth | Hai secret Worker riêng `SIGNING_KEY`, `GROUP_CODE_SHA256`; không dùng R2 uploader credential |
| Session / vé | Session tối đa12h trong RAM; vé một asset/revision/epoch, duration+600s, tối đa1h và không quá session |
| Origin | Tauri HTTP/HTTPS/tauri localhost chính xác theo wrangler.jsonc; phải nghiệm thu origin WebView2 thật ở Phase02 |
| Rate limit | Login10/phút/IP; request khác180/phút/IP; Retry-After60s |
| Logging | Observability tắt; code chỉ có diagnostic cố định `{event,code}`, không URL/IP/body/token/env/key |
| Quyền truy cập | Bucket giữ private; không thêm public domain/r2.dev; quyền phân phối và nhóm nhận cần duyệt riêng |

R2 binding có capability ghi ở platform, mặc dù handler chỉ expose đọc. Đây là bảo vệ bằng code/route, không phải IAM read-only cho binding; thay đổi source/deploy phải được review. Uploader token read/write cũ không xuất hiện trong API/client. Group code là mô hình nhóm nhỏ, không có thu hồi từng người hoặc chống sao chép nội dung sau khi được cấp quyền. CORS không thay authentication. Người có vé có thể dùng vé tới hết hạn; logout client chỉ xóa RAM/dừng player, muốn thu hồi toàn bộ phải đổi epoch/signing key phía server.

## Cache, request và chi phí

Mọi response có `private, no-store`, `CDN-Cache-Control: no-store`, `Cloudflare-CDN-Cache-Control: no-store`. Không dùng Cache API hoặc public cache key; không bật Cache Everything trên route này. Conditional requests vẫn kiểm tra vé trước R2. Vé được tái dùng trong RAM (tối đa16 bài, còn hạn trên30s); cùng asset đang xin vé được coalesce. Không disk cache audio, bulk prefetch hoặc retry nền vô hạn. Browser/WebView2 vẫn có buffer đang phát; số GET/Range thực tế tùy engine và thao tác tua.

| Request | R2 operations tối đa trong một lần handler |
|---|---:|
| Login / catalog / song / ticket / health / OPTIONS; auth/origin/rate bị từ chối | 0 |
| HEAD media, 304, 416, metadata sai hoặc object thiếu tại HEAD | 1 HEAD |
| GET full hoặc Range hợp lệ | 1 HEAD + 1 conditional GET |

Không cache HEAD để giữ kiểm tra metadata và ETag mỗi request. GET chuyển thẳng stream; cancellation truyền tới nguồn. Lỗi đọc stream sau khi đã gửi headers không thể đổi thành JSON503; player hiện error/buffering timeout và retry bằng thao tác người dùng. Không tự tải lại toàn file để hash; SHA metadata chỉ là assertion đã ghi khi upload, không phải hash remote độc lập. [R2 API](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/)

Đặt `G` là GET media hợp lệ, `H` là HEAD, `N` là GET kết thúc tại HEAD (304/416/mismatch). R2 ClassB tối đa `2G + H + N`; Worker requests gồm tất cả API/media/OPTIONS/lỗi, kể cả các request không tới R2. Ví dụ giả định100 người ×20 lượt/ngày ×30 ngày =60.000 lượt, 4 GET/lượt, 1 ticket/lượt, mỗi người login/catalog1 lần/ngày: **306.000 Worker requests +480.000 ClassB/tháng**, chưa tính OPTIONS/retry/HEAD/health. Đây là mô hình, không phải traffic/CPU đã đo live.

Theo giá Standard được tra ngày review: storage `$0.015/GB-month`, ClassB `$0.36/triệu`, egress R2 miễn phí; free tier10GB-month/10triệu ClassB áp dụng tổng account. Kho hiện2.506.137.889 bytes (~2,51GB thập phân), nhưng không biết tổng usage account nên không cam kết miễn phí. Không chuyển sang Infrequent Access. [R2 pricing](https://developers.cloudflare.com/r2/pricing/)

Workers Free:100.000 request/ngày, CPU10ms/invocation; Standard Paid có base `$5/tháng`,10triệu request và30triệu CPU-ms/tháng, phần thêm `$0.30/triệu request` và`$0.02/triệu CPU-ms`. Ví dụ trên dưới mức request Free nếu phân bố đều, **chưa chứng minh CPU phù hợp hoặc account đang dùng plan nào**. R2 request tính riêng; không coi stream là static assets miễn phí. Kiểm tra giá/plan/billing account trước duyệt. [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/)

Rate binding theo location, eventually consistent, không phải global quota/hard spending cap. Request bị từ chối vẫn có thể tốn Worker requests. Chưa có global byte budget. Trước production: chọn plan rõ ràng, review namespace IDs chưa trùng; bật usage/billing alerts do người quản lý; nếu Paid cân nhắc `limits.cpu_ms` khoảng50ms sau đo live, không đổi subscription tự động. Theo dõi request/day, ClassB, CPU p95,429/503 và số seek mỗi lượt. Không log signed URL; nếu bật dashboard/tail/observability cần redaction request URL trước, app diagnostic cố định không tự redaction platform invocation logs. [Rate limiter](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/), [CPU limits](https://developers.cloudflare.com/workers/platform/limits/)

## Kiểm tra local / clone

Sau npm ci theo SETUP, không cần catalog riêng để typecheck/test nguồn:

```powershell
cd D:\Workspace\AudioTP
npm.cmd run typecheck --prefix workers/media-api
npm.cmd run test:source --prefix workers/media-api
npm.cmd test --prefix apps/windows
```

`npm.cmd test --prefix workers/media-api` chạy thêm adapter synthetic; hai integration cần private manifest/media/bundle sẽ SKIP có lý do nếu thiếu inputs. Runtime source dùng workerd/R2 **mô phỏng cô lập**, opaque bytes tự tạo, không phải audio fixture để phát trong app. Production JSON không có trong Git; declarations mô tả hợp đồng, runtime kiểm tra đúng field/identity/size/hash/path. Không tắt checkJs hoặc dùng `any`. `npm run check` vẫn fail khi thiếu JSON, đúng thiết kế.

Workspace vận hành đã có authorized inputs: chạy prepare-worker/prepare-windows theo README nếu cần dựng lại projections, rồi `npm.cmd run check --prefix workers/media-api` (dry-run) trước full Worker tests. Không nâng baseline/counts để làm pass. Clone đã cài từ lockfile chạy workerd thành công dù npm từng cảnh báo allowScripts; không đổi global npm policy.

## Deploy user-run — chỉ sau phê duyệt riêng

Điều kiện: duyệt source/config/cost/rights, đúng account, bucket vẫn private, B10 còn phù hợp, không có upload đồng thời. Báo cáo B10 hiện có PASS983/983 ngày11/10, không cần Codex chạy audit mới; nếu có thay đổi R2 sau đó, người quản lý tự chạy `scripts/verify-r2.py --workers 2` theo r2-verification.md.

```powershell
cd D:\Workspace\AudioTP
.\.venv\Scripts\python.exe -X utf8 scripts/prepare-worker.py
npm.cmd run typecheck --prefix workers/media-api
npm.cmd run check --prefix workers/media-api
cd workers\media-api
npm.cmd exec -- wrangler login
```

**Bootstrap secrets trước deploy đầu:** `secrets.required` làm deploy fail nếu chưa có secret. Helper dùng `--apply` yêu cầu terminal tương tác; nhập group code4–256 ký tự với input ẩn. Nó gửi hash/key qua stdin, không đọc R2 credential. `--code-only` giữ signing key, chỉ đổi hash mã; tăng epoch mới nếu cần thu hồi phiên cũ. Mã ngắn chỉ phù hợp lựa chọn nhóm nội bộ đã được chấp nhận, không chống đoán phân tán. Wrangler có thể tạo draft Worker khi chưa tồn tại; mọi mutation live cần phạm vi phê duyệt phù hợp.

```powershell
cd D:\Workspace\AudioTP
$r2Config = Get-Content -Raw -Encoding UTF8 config/r2.json | ConvertFrom-Json
$env:CLOUDFLARE_ACCOUNT_ID = $r2Config.accountId
.\.venv\Scripts\python.exe -X utf8 scripts/configure-worker-secrets.py --apply --account-id $env:CLOUDFLARE_ACCOUNT_ID
cd workers\media-api
npm.cmd run deploy
```

Deploy này vẫn `SERVING_ENABLED=false`. Lưu Version ID và URL HTTPS thực Wrangler trả; không đoán URL. Với Worker đã tồn tại, lưu version/config trước khi rotate secret; `secret put` có thể deploy version ngay. Không chạy helper lại để kiểm tra vì nó rotate signing key. [Secrets](https://developers.cloudflare.com/workers/configuration/secrets/), [Required secrets/config](https://developers.cloudflare.com/workers/wrangler/configuration/)

Sau kiểm tra khóa phục vụ và được duyệt bật: người quản lý sửa riêng `SERVING_ENABLED` thành `"true"`, xem diff, chạy lại `npm.cmd run deploy` tại workers/media-api. Không xóa required secrets, mở public bucket hoặc thêm credential vào connection.json. Không build exe trong bước này. URL API là thông tin cấu hình public, còn code nhóm nhập lúc chạy, không đóng gói.

## Live acceptance / rollback

Chưa chạy bất cứ mục live nào. Sau deploy hợp lệ cần:

1. `GET/HEAD /v1/health` ready200, không probe bucket; disabled/missing config503. Health không chứng minh R2 tồn tại/quyền đọc.
2. Catalog không Bearer401; login sai401; đúng code mở catalog485/485/13. Origin lạ403;429 có Retry-After. Không lưu raw auth/network dumps.
3. Ba đại diện guide4177/instrumental17407/silent19977: đúng asset header, HEAD size/type, GET Range206 và Content-Range; suffix/open/If-Range,304,416; thiếu ticket401. Chỉ đọc vài range được phép, không full download983.
4. Client/EXE trên máy không có media local: nghe, tua/pause/resume, đổi variant/tab, queue, expired ticket/session, logout khi đang connect, mất mạng/retry. Browser mock không thay Windows/WebView2 thực.
5. Ghi browser/OS/version, UTC thời điểm, status/counts và ID không kèm ticket/code; user nghe xác nhận nội dung. Sau đủ bằng chứng mới đánh dấu Phase01 DONE.

Emergency stop: đặt `SERVING_ENABLED=false`, tăng `AUTH_EPOCH` tới giá trị mới chưa dùng rồi redeploy. Nếu không deploy được, người quản lý chặn route/Worker trong dashboard theo quyền đã duyệt. Không xóa/ghi object R2 hoặc upload lại. In-flight stream đã được chấp nhận có thể còn chạy; kill switch áp dụng request kế tiếp, không phải DRM.

Rollback code: lưu version tốt trước mỗi deploy; người quản lý dùng `wrangler rollback` theo hướng dẫn chính thức, xác nhận đúng version. Rollback có thể mang cấu hình/secret cũ, nên phải kiểm tra lại serving/origin/epoch và không vô tình phục hồi vé đã thu hồi; ưu tiên redeploy source tốt với epoch mới và serving tắt. Sau đó smoke auth/Range trước bật lại. Không tự đưa rollback command có Version ID giả. [Rollbacks](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/rollbacks/)
