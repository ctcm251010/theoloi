# Phase02 — ONLINE Beta và Nhớ đăng nhập

Ngày: 13/10/2026, Asia/Bangkok. **READY FOR REVIEW**, không đánh dấu DONE trước nghiệm thu nghe thật/native/máy đích. Người dùng đã duyệt deploy API private trong account `ctcm251010`, thao tác bằng member `nguyenducbang.uit`, và chọn tính năng Nhớ đăng nhập.

## Cập nhật mã chung ngắn — 13/10/2026

Theo yêu cầu rõ ràng của người dùng cho nhóm nội bộ, validation API/UI/DPAPI/helper hỗ trợ mã4–256 ký tự. Mã thật không nằm trong source, EXE hoặc tài liệu. Mã ngắn dễ đoán; giới hạn10 lần/phút/IP/location không chống đoán phân tán. Không thay quyền bucket,983 object hoặc credential R2.

Đã cập nhật riêng `GROUP_CODE_SHA256` bằng input ẩn và stdin, giữ nguyên `SIGNING_KEY`. Sau cập nhật hash, deploy epoch3 thu hồi cả phiên/vé cấp trước khi đổi mã; source serving vẫn false, live bật bằng override đã duyệt. Version ID giữ tại `logs/repository-audit/short-code-final-live-deploy.txt`. Không rollback về epoch cũ.

Live smoke nhỏ PASS: mã mới login200, catalog200 đủ485guide/485instrumental/13silent, health200, không auth401, mã sai401. Không tải audio hoặc audit SHA nội dung R2. Test offline: frontend60 PASS, Worker25 PASS/typecheck/dry-run PASS, Python193 total190 PASS/3 symlink SKIP, Rust6 PASS và helper subprocess được parent chạy hai lần. Test RED trước GREEN ở UI/API/DPAPI/helper; independent review không có Important/Critical.

Integrity đọc983 media/2,506,137,889 bytes:0 size/hash mismatch;18 metadata/state:0 thay đổi. Bản app cũ không nhập được mã4 ký tự, cần đóng và mở/cài artifact mới dưới đây, nhập mã được cấp rồi chọn Nhớ đăng nhập. Native playback/restart trên chính artifact mới và máy đích vẫn chờ người dùng nghiệm thu; Phase02 tiếp tục READY FOR REVIEW.

## API đã triển khai

- `https://audiotp-media-api.ctcm251010.workers.dev`; binding `MEDIA` tới bucket hiện có `audiotp-media`. Bucket vẫn private, không public r2.dev hoặc custom domain. Không upload/sửa/xóa object.
- OAuth CLI đã xác minh đúng member và account. Member đã Active; nguyên nhân ban đầu là OAuth Wrangler chỉ cho account khác, không cần mời lại hoặc tăng quyền.
- Người dùng tự cấu hình hai secret mới qua helper input ẩn. Agent chỉ kiểm tra tên secret, không đọc mã/hash/signing key hoặc credential R2. Không chạy helper lại vì nó rotate signing key.
- Deploy đầu giữ serving tắt, người dùng mở health thấy `serving_disabled`; sau đó bật phục vụ authenticated bằng override `SERVING_ENABLED:true`. Source `wrangler.jsonc` vẫn false để default deploy fail closed. Version journal giữ local tại `logs/repository-audit/phase02-live-deployment.json`.
- Account Workers **Free / Current plan** đã quan sát; không upgrade subscription. Chi phí R2 và giới hạn Workers vẫn theo [operations](phase01-operations.md), không cam kết miễn phí toàn account.
- Curl chuẩn xác minh5 request: health200, catalog không auth401, login sai401, origin lạ403, native preflight204. Health ghi `storage:not-probed`: chưa chứng minh playback R2.
- Python urllib bị edge1010; Browser Use mở/reload tự động bị ERR_BLOCKED_BY_CLIENT. Curl chuẩn hoạt động, không đổi bảo vệ trình duyệt hoặc Cloudflare để vượt chặn. Người dùng mở thủ công đã quan sát được health.

## Nhớ đăng nhập Windows

Người dùng dán mã nhóm một lần, chọn **Nhớ đăng nhập trên máy này** và kết nối. Sau khi login/catalog thành công, mã được lưu bằng DPAPI current-user, ràng buộc đúng HTTPS API origin bằng entropy. Không lưu plaintext/localStorage/sessionStorage; session và vé nghe giữ RAM. App tự kết nối khi mở lại hoặc khi phiên hết hạn, không tự phát nhạc. Mã bị từ chối401 khi khôi phục thì xóa mã nhớ và yêu cầu nhập lại, không retry vô hạn.

Chỉ main window với bundled origin được gọi ba native command save/read/forget; không plugin shell/fs/network hoặc đường dẫn tùy ý từ JS. Không nhúng R2 credential. File ciphertext trong app local data, chỉ mở lại trên đúng tài khoản Windows và origin. DPAPI không bảo vệ trước malware chạy bằng cùng tài khoản Windows. Group code vẫn là quyền nhóm, không hỗ trợ thu hồi từng người.

Logout/bỏ chọn xóa mã đã nhớ; queue và generation ngăn callback cũ khôi phục sau logout. OS file lock bảo vệ nhiều process; staging sau crash được phục hồi dưới lock. File lock trống được giữ, không chứa mã. Rust build yêu cầu>=1.89 cho native file locking; máy người nghe chỉ cần WebView2, không cần Rust/Node/Python.

## Artifact ONLINE

Artifact cuối có first-run prompt và hỗ trợ mã ngắn: `release/windows/0.2.0-20261013T042837062795Z/`. Các artifact trước `0.2.0-20261013T040214371062Z` và `0.2.0-20261013T034723844708Z` giữ nguyên để đối chiếu; artifact đầu đã được người dùng thử online/remember restart.

| File | Bytes | SHA-256 |
|---|---:|---|
| `AudioTP.exe` | 3,188,736 | `2f78bc7feae8449aa020cb9a762536b47576b42752a5ac52cf3c788eafeca9b5` |
| `AudioTP_0.2.0_x64-setup.exe` | 1,161,320 | `3d255ce67531c8ddc3a51c33c080b80755d9dc5e8d07d4b177c47818fc6eadff` |

Identifier `org.audiotp.desktop`, pinned API HTTPS thực. Stage983 tracks485/485/13,0 test IDs,0 M4A/WAV; app/api/remember/index/styles khớp source test. Source tauri config không bị builder sửa để tạo endpoint; override stage riêng. Release chưa ký.

Đã chạy portable từ TEMP với PATH chỉ System32; process Responding và titleAudioTP. Đây là startup check trên máy phát triển, chưa thay nghiệm thu native Play/seek, IPC UI, nhớ đăng nhập sau restart hoặc máy sạch. Cửa sổ được giữ cho người dùng nhập mã và thử trực tiếp.

## Kiểm thử và giới hạn

Người dùng đã trực tiếp thử artifact đầu và phản hồi “ổn nha, tự kết nối lại dc”. Đây là nghiệm thu user-run cho hoạt động online và nhớ đăng nhập sau restart; không phải automated remote SHA/Range audit hoặc máy Windows sạch. Theo feedback tiếp theo, đã bổ sung auto mở form kết nối khi bản ONLINE chưa đăng nhập, giữ thư viện trực tiếp nếu restore thành công; frontend tăng59 PASS. Artifact mới ở lần build sau chứa sửa UX này; artifact đầu được giữ để đối chiếu.

- Python191 total:188 PASS/3 symlink SKIP; frontend59 PASS; Worker24 PASS/typecheck; Rust5 PASS,1 subprocess helper ignored trong run chính nhưng được parent chạy hai lần và PASS.
- Test native DPAPI thật với mã tự tạo: ciphertext không lộ plaintext, origin khác/ciphertext hỏng bị từ chối, overwrite, crash recovery, logout và khóa hai process. Không dùng mã người dùng trong tests.
- Independent review phát hiện staging bị kẹt sau crash; đã tái hiện RED, sửa bằng OS lock/recovery và re-review không còn Critical/Important.
- 983 media/2,506,137,889 bytes SHA/size giữ nguyên; catalog/manifest hash khớp mốc cũ.18 metadata/state kiểm tra riêng với baseline. Không download/upload thêm hoặc chạy lại B10.
- User đã xác nhận hoạt động ONLINE và auto reconnect sau restart. Pending: formal HEAD/Range/R2 metadata, thao tác riêng pause/seek/variant/queue/logout chưa có biên bản chi tiết, first-connect prompt của artifact cuối, cài/gỡ installer ONLINE và máy đích sạch. Các kết quả TEST/LOCAL trước không thay thế những mục này.
- Source/secret scan/Git cập nhật trong final handoff. Giữ `.env.example` người dùng đang sửa ngoài commit công việc này; không đọc/in nội dung sửa đó.

Source runtime `f324ed9` đã push, clone frontend59 PASS, Worker21 PASS/3 private SKIP/typecheck PASS. Khi chạy Windows Python integration trong clone, test catalog cũ lỗi do thiếu private JSON; đã sửa phân loại bằng explicit SkipTest (`b5663ae`), không thêm/fake dữ liệu. Workspace5 catalog integration vẫn PASS; clone Windows Python46 total/43 PASS/3 SKIP, helper account6 PASS. Runtime artifact không thay đổi bởi commit test-only này. Gitleaks staged/history không leak, exact-index không có media/credential/private operational paths; remote SHA đã kiểm tra. Docs ledger theo sau không đổi runtime.

## Bàn giao và bước tiếp theo

Người dùng thử đúng ONLINE artifact: Cài đặt → Kết nối thư viện → dán mã → chọn Nhớ đăng nhập → Kết nối. Phát bài1, pause/seek, đóng/mở lại và xác nhận tự kết nối; đăng xuất rồi mở lại phải yêu cầu mã. Không gửi mã hoặc URL vé nghe khi báo lỗi.

Sau nghiệm thu máy này, gửi installer và mã truy cập qua hai kênh riêng cho nhóm thử được duyệt; máy đích cần Internet/WebView2, không cần kho media local. Hoàn tất Phase01 live R2 và Phase02 native/installer/máy sạch trước Closed Beta. Không merge PR Phase01, public bucket hoặc bắt đầu Phase03 tự động.
