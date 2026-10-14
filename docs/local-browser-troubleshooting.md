# Browser Use localhost — sửa nguyên nhân /14-10-2026

**DONE cho preview AudioTP hiện tại.** Chrome profile Bang; tự tạo tab mới và phát audio thành công, không cần người dùng mở trang hộ. Không đổi Chrome, extension, sandbox, credential hoặc Cloudflare live.

## Nguyên nhân và bằng chứng

`workers/media-api/local-preview.mjs` từ chối mọi `Sec-Fetch-Site: cross-site`. Browser Use mở trang mới mang `cross-site`, `Sec-Fetch-Mode: navigate`, `Sec-Fetch-Dest: document`; nhập địa chỉ thủ công khác ngữ cảnh nên không bị từ chối. Log HTTP tạm chứng minh request tới server với Host hợp lệ và nhận403. Chrome hiện `ERR_BLOCKED_BY_CLIENT`; chỉ nhìn trang lỗi đã dẫn đến khoanh vùng thiếu chính xác trước đây.

Trước sửa: tab748687836 bị lỗi; wrapper ghi GET `/`, hostAllowed=true, cross-site/navigate/document, status403. Sau sửa: tab mới748687842 với cùng headers nhận200, module tiếp theo same-origin và player chạy. Wrapper chỉ ghi route cố định/status/Fetch Metadata, không header xác thực, query, body, cookie hoặc token. Evidence ignored: `tmp/local-browser-diagnostic.headers.stdout.log`, `tmp/local-browser-diagnostic.fixed.stdout.log`.

## Bản sửa

Cho phép điều hướng top-level GET/HEAD tới đúng `/` hoặc `/index.html`. Cross-site fetch/subresource/iframe/POST và API/media vẫn403; Host chỉ loopback đúng port, native origins vẫn opt-in như trước. HTML thêm `X-Frame-Options: DENY` và CSP `frame-ancestors 'none'`; không mở CORS rộng. Phù hợp [Fetch Metadata resource isolation](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Fetch_metadata): phân biệt điều hướng trang với truy cập tài nguyên từ website khác.

Không cần thay Allow access to file URLs (chỉ liên quan upload file), tắt antivirus/extension, public tunnel hoặc mở server ra LAN. Không cần build lại EXE hoặc deploy Worker vì lỗi nằm trong adapter local.

## Kiểm chứng

- Regression raw HTTP tái hiện đúng headers trình duyệt: RED403→GREEN200. Node fetch tự đổi Sec-Fetch-Mode thành cors nên test dùng node:http để bảo toàn request. Kiểm tra API/media/module/iframe/cors/no-cors/POST/bad Host vẫn bị chặn; HEAD, HTML và frame protection đúng.
- Worker suite37 PASS, frontend69 PASS, Worker typecheck PASS.
- Python Windows subset66 tổng:64 PASS,2 SKIP (symlink Windows),0 FAIL. Không gọi đây là full Python regression.
- Browser Use tự tạo tab mới bằng createBrowserTab và tabs.new/goto; sau bỏ wrapper/restart CLI bình thường và reset runtime vẫn tự mở/phát được. Guide1 duration125.016236s/currentTime tăng/error=null; instrumental1 duration125.248435s; Nghe nhanh silent đầu duration50.085442s,13 hàng; our-wish69.427664s; unison311.518912s, currentTime9.574968/error=null. Một audio element.
- Pause/tua tới10s/resume/chuyển tab vẫn phát đúng context; Nhạc đệm485 hàng; tìm472 ẩn Nghe nhanh, xóa hiện lại; console warn/error rỗng. Screenshot ignored `tmp/local-browser-fixed.png`.
- Đây là browser playback trên file local, không phải nghiệm thu native EXE/máy sạch/live R2 hoặc nghe xác nhận nội dung bằng tai. Source không sửa catalog, manifest, state, media; không đọc credential.

## Quy trình tự test lần sau

```powershell
cd D:\Workspace\AudioTP
node workers/media-api/local-preview.mjs --port 8772
```

Kiểm tra server sống, Browser Use tự tạo tab `http://127.0.0.1:8772/`, chờ bootstrap hoàn tất rồi bấm Play. Nếu dùng server cũ còn giữ code trong RAM, restart đúng helper do phiên đó tạo; không kill mọi Node/Chrome. Nếu lỗi tái xuất hiện, đối chiếu HTTP status/Fetch Metadata trước khi quy cho quyền Chrome. Lỗi browser policy chặn protocol hoặc quyền truy cập là trường hợp riêng, không tìm cách lách.
