# AudioTP 1.0.1 — nghiệm thu kỹ thuật

Ngày 13/10/2026, Asia/Bangkok. Task tích hợp/phát hành: DONE. Nghiệm thu nâng cấp native sang phiên bản sau/máy Windows khác: READY FOR REVIEW, không đồng nghĩa toàn bộ Closed Beta hoàn tất.

## Chức năng

- Nghe nhanh → “Cầu nguyện chúng con mong muốn” phát đúng asset riêng `watv:vi:prayer:our-wish`, 69.427664s, AAC stereo. Người dùng xác nhận đúng nội dung/quyền phục vụ nhóm AudioTP. Một prayer object upload/GET SHA-256 verified; không tải lại nguồn.
- Catalog cũ giữ 983 tracks (485/485/13); supplementary catalog qua `/v1/quick-audio`, ticket có revision riêng, chung player/HTTP Range. Không thay 983 catalog/manifest/media/state. Bài cầu nguyện không mang số bài và chưa thuộc Yêu thích/Gần đây; mục thống thanh tiếp tục unavailable.
- Updater Tauri2.13.3: kiểm tra sau đăng nhập và mỗi sáu giờ khi visible; nút trong Cài đặt; chỉ tải/cài khi người dùng bấm. Installer private R2, bearer RAM, exact HTTPS origin/path, không redirect, Minisign và signed-version chống replay, logout vô hiệu pending check/install. Lỗi hiển thị với nút Thử lại.
- Bản1.0.0 cần cài1.0.1 thủ công một lần; không thể bổ sung updater vào EXE cũ từ xa. GitHub/bucket không đổi visibility; không credential/token R2 trong client.

## Bằng chứng

| Phạm vi | Kết quả |
|---|---|
| Python toàn bộ | 227 tests:223 PASS,4 SKIP do quyền symlink Windows |
| Frontend | 67 PASS |
| Worker/service/workerd/private local | 35 PASS; TypeScript PASS; deploy dry-run PASS |
| Rust | 16 PASS,1 helper ignored được parent test chạy subprocess hai lần PASS |
| Chữ ký updater | Fixture tự tạo: đúng chữ ký và Bearer download PASS; sửa bytes, sai version, legacy thiếu version bị từ chối |
| Browser local thật | Prayer hiển thị1:09/playing, pause/seek/chuyển tab; tìm kiếm ẩn Nghe nhanh; silent shortcut mở13tracks/bài đầu nguồn |
| Cloudflare live | 12 checks PASS: login/catalog983, supplementary1, prayer ticket/HEAD/Range/full SHA, update newer/current, installer full SHA, denied unauth |
| Integrity gốc | 983 media/2,506,137,889bytes SHA/size khớp;18 metadata/state hashes không đổi |
| User native | Người dùng xác nhận “cầu nguyện chúng con mong muốn ổn r nha” sau khi thử EXE1.0.1 |
| Clone sạch source | Frontend67 PASS; Worker32 PASS/3 private integrations SKIP; typecheck PASS; prayer/publisher/packaging43 PASS/2 symlink SKIP |
| Git/Release | PR#3 MERGED, tagv1.0.1 trỏ bace536;5 asset upload +2 source archives, cả5 SHA GitHub khớp local; secret/index scan sạch |

Evidence local ignored: `tmp/regression-1.0.1-{python,frontend,worker,rust}.log`, `tmp/build-1.0.1.log`, `tmp/deploy-1.0.1.log`, `logs/repository-audit/v1.0.1-{integrity,live-smoke}.json`. Live verification tải khoảng2.97MB qua API để kiểm tra, không lưu bản sao media. Không phải full R2 content audit.

Worker `audiotp-media-api` giữ auth epoch3/secrets/serving; deployment version `b8c06131-69d4-4a95-bfdb-69819350e2e1`. R2 chỉ thêm một prayer audio và một signed installer, không overwrite originals. Không đổi gói dịch vụ. Một check update không truy cập R2; tải installer dùng HEAD+GET khi người dùng bấm. API giữ no-store và rate limits hiện có, không loop retry nền. Chi phí/request phụ thuộc lượng nghe/cập nhật thực tế, không khẳng định miễn phí vô hạn.

## Artifact

Folder `release/windows/1.0.1-20261013T080719956929Z/`:

| File | Bytes | SHA-256 |
|---|---:|---|
| AudioTP.exe | 4713984 | 4f009d3b60e428b76dab5bdb7452c8ea3d0c5ea50f91893eb808d8130f549a1e |
| AudioTP_1.0.1_x64-setup.exe | 1846286 | 80eda93a00a2490f3e11b467cef7bb4e4559bde50655fb641f73a83ddcb6a2e3 |
| AudioTP_1.0.1_x64-setup.exe.sig | 436 | 67cbe07498deac094584228581b06b0cd6a4a31cd79f07e5276e6a0c6db65211 |

Public updater key `config/audiotp-updater.pub` có thể commit. Private signing key giữ local, không đọc/in/commit; người quản lý cần sao lưu an toàn để ký các bản sau. Đây không phải Authenticode, Windows vẫn có thể cảnh báo nhà phát hành chưa xác định. Backend không cung cấp file chưa ký.

## Review và giới hạn

Review đã phát hiện và sửa: lỗi đóng S3 client thoát sanitizer; HEAD prayer thiếu kiểm tra Content-Type; banner lỗi cập nhật biến mất vào dialog đóng; LOCAL/TEST hiện nhầm nút cập nhật; preview thiếu module remember-access. Regression hiện PASS. Release compiler phát hiện serde_json chỉ ở dev-dependencies; đã chuyển vào dependencies và build NSIS PASS.

EXE đã mở ngoài workspace với PATH chỉ System32; người dùng sau đó xác nhận phát bài cầu nguyện ổn. Lần thử đầu người dùng báo bấm được nhưng chưa phát; sau đó xác nhận phát được trước khi có thay đổi code khác. Không tái hiện được và chưa xác định nguyên nhân lần đầu, không nhận là một bug đã tìm/sửa root cause. CUA không cung cấp native app control trong phiên này. Nút kiểm tra cập nhật native, nâng cấp thực tế1.0.1→phiên bản sau và cài/gỡ trên máy khác chưa được người dùng xác nhận. Không tuyên bố toàn Phase01/02/03 DONE hoặc tự chuyển phase.

Full Python discover trong clone không private inputs đã chạy và FAIL:222 tests,36 FileNotFoundError và1 assertion do thiếu snapshot/catalog/manifest gốc,5 SKIP;180 PASS. Đây là giới hạn private-input được SETUP.md ghi sẵn, không phải full clone PASS. Các module mới chạy riêng và Worker source/typecheck đều PASS như bảng trên; không copy private datasets hoặc tạo dữ liệu giả để che lỗi. Log `tmp/clone-1.0.1-python.log` giữ chi tiết từng test.

## GitHub đã phát hành

[Release1.0.1](https://github.com/ctcm251010/theoloi/releases/tag/v1.0.1), [PR#3](https://github.com/ctcm251010/theoloi/pull/3). Source `ac4537ce8a4228f367923863327c985f0961f324` merge thành `bace53634612ccc5c94ec69f25efd0b31499aecc`, tree giống source đã build/test; tag không di chuyển. Docs ledger theo sau không đổi runtime. Assets gồm setup/portable/.sig/HUONG-DAN/SHA256SUMS, không media/credential. Evidence `logs/repository-audit/v1.0.1-published-assets.json`, ảnh `tmp/release-1.0.1-assets.png`. Private repository giữ nguyên; người dùng phổ thông nhận setup từ quản lý, các bản sau tải qua API xác thực không cần GitHub account.

## Vận hành bản tiếp theo

Build production bằng `scripts/build-windows.py --build --installer --api-base <origin hiện tại> --updater-public-key config/audiotp-updater.pub`, với `TAURI_SIGNING_PRIVATE_KEY` trỏ file khóa local được quản lý bảo mật. Không commit env/khóa.

Chạy `scripts/publish-windows-update.py --release-dir <release-folder>` để dry-run. Sau review dùng cùng lệnh thêm `--apply`: create-only PUT một installer và GET/hash, rồi xuất ignored `delivery/windows-update.json`/`workers/media-api/generated/updates.json`. Deploy Worker bằng quy trình hiện có với `--strict --keep-vars --var SERVING_ENABLED:true`, giữ đúng account. Không đưa command giả cho binary chưa build. Nếu object/version xung đột, dừng và chọn version mới; không overwrite release đã phát hành.

Nếu cần rollback Worker, phiên bản trước task là `264b2ce0-9e8f-4095-935d-02d5afeb449c`; rollback sẽ tạm mất supplementary/updater nhưng catalog983 vẫn là baseline. Không tự rollback/xóa object. Native updater không tự downgrade.
