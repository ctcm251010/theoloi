# AudioTP1.0.3 — thống thanh và Mật khẩu chung

14/10/2026, Asia/Bangkok. Source/build/live READY FOR REVIEW; GitHub và native user acceptance đang hoàn tất.

Người dùng cung cấp `cau-nguyen-thong-thanh.m4a` và duyệt bốn bước kiểm tra/đăng ký/upload/tích hợp/test/phát hành. Bổ sung yêu cầu đổi nhãn trường kết nối thành **Mật khẩu chung**, giữ giá trị xác thực hiện có, không điền sẵn hoặc commit mật khẩu.

## Phạm vi và kiểm chứng

- Source local giữ nguyên tên/bytes; bản quản lý nội bộ `media/prayer/watv/vi/unison-prayer/unison-prayer.m4a` là copy byte-identical. AAC44100Hz/stereo,5,038,802bytes,311.518912s, SHA256 `317ae73c27cc963181d71e11cdbb522924c329e31f0ffcb3bc15354a5579070e`; FFprobe và full FFmpeg decode PASS, không re-encode. Metadata/proof ignored, không có URL nguồn suy đoán.
- Asset riêng `watv:vi:prayer:unison-prayer`, cùng namespace supplementary vớiour-wish. Strict ID/title/duration/path mapping; không dùng số bài hoặc arrayindex. Nút `quick:unison-prayer` phát qua player chung, không dùng âm thay thế. 983 catalog/tracks vẫn giữ485/485/13.
- Uploader đòi `--asset` khi có nhiều bản thu, create-only và HEAD Content-Type/metadata+GET SHA; recovery chỉ sửa selected row. Review phát hiện global recover có thể sửa unselected uploaded/uploading rows; regression RED→GREEN đã sửa, không đổi shared uploader hoặc original983state.
- Frontend69 PASS, Worker36 PASS/typecheck, Python229 tổng225 PASS/4 symlink SKIP sau reviewfix; Rust16 PASS/1helper ignored được gọi subprocess hai lầnPASS. EXE/NSIS release1.0.3 build/signature PASS. Browser local phát thống thanh5:11, pause/seek/chuyển tab, hai prayer không lẫn nhau; tìm kiếm vẫn ẩn Nghe nhanh. Backend synthetic/mock và native user acceptance phân biệt riêng.
- R2: thống thanh mới đã upload và full GET/hash verified. Không overwrite our-wish hoặc983. 983media/2,506,137,889bytes và18 metadata/state hashes kiểm tra lại không đổi.

## Phiên bản và cập nhật

1.0.2 đã build/upload installer private để chuẩn bị, chưa tạo tag/Release hoặc deploy metadata. Yêu cầu nhãn Mật khẩu chung đến sau khi artifact đã có; chọn1.0.3 để giữ installer version immutable, không overwrite/xóa1.0.2. Bản phát hành cuối gộp cả hai yêu cầu. Người dùng1.0.1 nhận update qua API xác thực;1.0.0 phải cài thủ công một lần. Chỉ tải/cài khi người dùng bấm; giữ public key/signing key/auth epoch/DPAPI hiện tại, không yêu cầu nhập lại mật khẩu do đợt source này.

## Lỗi Browser Use mở localhost — khoanh vùng

Lệnh tạo tab vào `http://127.0.0.1:8772/` nhận `net::ERR_BLOCKED_BY_CLIENT`. CùngURL người dùng mở thủ công được; claim/DOM/click/audio/reload bằng Browser Use thành công. HTTPS GitHub bằng lệnh mở tab cũng thành công. Backend localhost phục vụ bình thường và file audio được player phát. Vì vậy chưa có bằng chứng server thiếu port/quyền media; vấn đề nằm ở đường mở/điều hướng tab mới của công cụ hoặc Chrome client. Không đủ chứng cứ quy cho extension cụ thể, firewall, CORS hay sandbox. Không vô hiệu hóa sandbox/protection/extension, không xuất cookie/token hoặc inspect công cụ nội bộ. Tiếp tục dùng tab người dùng mở; root cause còn UNKNOWN.

## Artifact/live

Folder `release/windows/1.0.3-20261014T104321669422Z/`: portableEXE4713984bytes SHA43a8a390419621e05456e6883ec5f108db3828750ff98bd8ba349c95abd8a37e;setup1846914bytes SHA6f34b407ee98bd4ba1a65c31ea7ae32efdb026f7b1cf031c11376416d24074c9;updater.sig436bytes SHA481529652eec0e5540a35b83f44f26ee648692dedef9019dd3715ca218fa8bc9. Installer đãprivateR2/create-only/fullGET SHAverified. Worker deployment `4b3c5c16-04b8-4faa-a30c-a0d24ec59b66`, giữepoch3/secrets/serving/bucketprivate.12livechecksPASS:catalog983,2supplementary,unisonHEAD/Range/fullSHA,update1.0.1→1.0.3/current204/authdenied/installerSHA. Khoảng6.89MB verification, không lưu bản sao audio. Evidence `logs/repository-audit/v1.0.3-live-smoke.json`, `v1.0.2-integrity.json`; `tmp/build-1.0.3.log`, `tmp/deploy-1.0.3.log`.

## Còn cần nghiệm thu

GitHub assets/hash và user native nâng cấp1.0.1→1.0.3/phát thống thanh. Không đánh dấu native/máy sạch PASS từ browser/mock. Giữ toànPhase03/ClosedBeta ngoài task này.
