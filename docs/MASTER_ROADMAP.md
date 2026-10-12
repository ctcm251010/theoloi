# THEOLOI — MASTER DEVELOPMENT ROADMAP & AUTONOMOUS WORKFLOW

## 0. THÔNG TIN DỰ ÁN

**Project:** THEOLOI

**Local workspace hiện tại:**

`D:\Workspace\AudioTP`

**GitHub repository:**

https://github.com/ctcm251010/theoloi.git

**Định hướng:** Xây dựng hệ sinh thái ứng dụng dành cho người theo Kinh Thánh, phát triển lâu dài trên Windows, Android, iOS và có thể cả Web.

**Sản phẩm đầu tiên:** AudioTP — ứng dụng nghe Bài ca mới và các nội dung âm thanh liên quan.

THEOLOI là tên hệ sinh thái và monorepo.

AudioTP là ứng dụng/module đầu tiên, không phải tên đại diện cho mọi sản phẩm tương lai.

---

# I. NHIỆM VỤ TỔNG QUÁT

Tôi muốn bạn trở thành coding agent phụ trách triển khai và quản lý tiến độ kỹ thuật của dự án THEOLOI.

Bạn cần:

1. Hiểu toàn bộ cấu trúc và trạng thái dự án.
2. Duy trì roadmap dài hạn.
3. Tự phân tích và chia nhỏ công việc của từng giai đoạn.
4. Tự triển khai các công việc trong phạm vi được phép.
5. Tự kiểm thử và sửa lỗi.
6. Tự review trước khi hoàn thành.
7. Cập nhật tài liệu và Git.
8. Khi hoàn thành một giai đoạn, tự đề xuất bước tiếp theo dựa trên roadmap.
9. Khi tôi xác nhận tiếp tục, tự bắt đầu giai đoạn kế tiếp mà không yêu cầu tôi viết lại prompt.

**QUAN TRỌNG: Không dừng sau từng task nhỏ. Hãy hoàn thành trọn vẹn một giai đoạn trước khi báo cáo tổng kết.**

Tuy nhiên, không được tự động thực hiện một giai đoạn mới sau khi đã báo cáo hoàn thành giai đoạn trước, trừ khi tôi đã cho phép.

---

# II. QUY TRÌNH KHỞI ĐỘNG

Mỗi khi bắt đầu một phiên làm việc:

1. Đọc AGENTS.md.
2. Đọc SETUP.md nếu có.
3. Đọc README.md.
4. Đọc roadmap và task đang hoạt động.
5. Kiểm tra Git status và branch hiện tại.
6. Xác định giai đoạn hiện hành.
7. Đọc báo cáo nghiệm thu giai đoạn trước.
8. Kiểm tra các blocker chưa giải quyết.
9. Xác định công việc tiếp theo dựa trên roadmap.
10. Tiếp tục triển khai mà không yêu cầu tôi giải thích lại toàn bộ dự án.

Không tự giả định trạng thái từ báo cáo cũ nếu source code thực tế đã thay đổi.

Source code, test output và commit thực tế phải là bằng chứng ưu tiên.

---

# III. HỆ THỐNG QUẢN LÝ ROADMAP

Sử dụng hệ thống quản lý task/roadmap đã tồn tại nếu có.

Nếu chưa có, tạo:

`docs/roadmap/ROADMAP.md`

`docs/roadmap/CURRENT_PHASE.md`

`docs/roadmap/CHANGELOG.md`

`docs/roadmap/BACKLOG.md`

`docs/roadmap/DECISIONS.md`

Với mỗi giai đoạn, tạo tài liệu riêng khi cần:

`docs/roadmap/phases/phase-00.md`

`docs/roadmap/phases/phase-01.md`

...

Không tạo file trùng lặp nếu dự án đã có hệ thống tương đương.

## Mỗi giai đoạn cần có

- ID và tên.
- Mục tiêu.
- Phạm vi.
- Danh sách công việc.
- Dependency.
- Rủi ro.
- Tiêu chí nghiệm thu.
- Test bắt buộc.
- Trạng thái.
- Những gì chưa xác minh.
- Git commit hoặc PR liên quan.
- Đề xuất bước tiếp theo.

## Trạng thái chuẩn

- NOT STARTED
- IN PROGRESS
- BLOCKED
- READY FOR REVIEW
- DONE

Chỉ đánh dấu DONE khi đạt đủ tiêu chí nghiệm thu và có bằng chứng.

Phân biệt rõ:

- Unit tests PASS.
- Integration tests PASS.
- Browser tests PASS.
- Windows runtime PASS.
- Live Cloudflare E2E PASS.
- User acceptance PASS.

Không dùng kết quả mock để khẳng định hệ thống production đã hoạt động.

---

# IV. ROADMAP CHÍNH THỨC

## PHASE 00 — REPOSITORY FOUNDATION

### Mục tiêu

Hoàn thiện monorepo THEOLOI trên GitHub và xác minh có thể phát triển dự án từ một bản clone sạch.

### Công việc

- Kiểm tra kết quả refactor trước đó.
- Xác minh Git remote và branch.
- Xác minh commit đã push thành công lên GitHub.
- Audit .gitignore và tracked files.
- Kiểm tra không commit media local, secret, credential hoặc dữ liệu không được phép phân phối.
- Kiểm tra cấu trúc apps, workers, catalog, delivery, schemas, tests và scripts.
- Chuẩn hóa README và tài liệu setup.
- Kiểm tra lockfiles, dependency và build scripts.
- Thử clone repository vào một thư mục riêng biệt.
- Cài dependency từ tài liệu.
- Chạy các bộ test khả thi.
- Xác minh các ứng dụng không phụ thuộc đường dẫn tuyệt đối của workspace cũ.

Nếu chưa refactor/push xong, hoàn tất các việc an toàn còn thiếu trước.

Không tự ý xóa, di chuyển hoặc sửa dữ liệu audio gốc.

### Tiêu chí nghiệm thu

- Repo GitHub hoạt động.
- Không phát hiện secret trong commit được push.
- Không có media lớn hoặc dữ liệu bị hạn chế phân phối vô tình được commit.
- Có tài liệu setup đủ rõ.
- Clean clone có thể chạy được các bài kiểm thử phù hợp.
- Các test không bị hỏng do refactor.

### Sau khi hoàn thành

Tự đề xuất:

**PHASE 01 — Cloudflare R2 & Worker API**

Giải thích lý do đây là giai đoạn ưu tiên tiếp theo.

---

## PHASE 01 — CLOUDFLARE R2 & ONLINE AUDIO

### Mục tiêu

Chuyển AudioTP từ ứng dụng nghe audio local thành ứng dụng có khả năng phát audio trực tuyến qua Cloudflare R2 private.

### Thông tin hiện có

Bucket dự kiến:

`audiotp-media`

Dữ liệu trước đây:

- 485 audio Hướng dẫn.
- 485 audio Nhạc đệm.
- 13 audio Nhạc ngẫm nghĩ.
- Tổng 983 M4A assets.

Worker API đã từng được triển khai và kiểm thử local nhưng chưa xác minh deployment production.

Phải kiểm tra source và kết quả mới nhất, không mặc định trạng thái này vẫn còn chính xác.

### Công việc

**1. Audit R2**

- Xác minh bucket và cấu hình binding.
- Kiểm tra B10 và kết quả xác minh object nếu có.
- Kiểm tra mapping assetId → objectKey.
- Xác minh tính toàn vẹn metadata.
- Không tải lại toàn bộ media khi chưa cần.
- Không tự upload, xóa hoặc ghi đè R2 objects.

**2. Worker API**

- Hoàn thiện API catalog.
- API truy cập nội dung.
- API streaming audio.
- Hỗ trợ HTTP Range và seek.
- Xử lý authentication.
- Thiết kế vé phát audio ngắn hạn hoặc phương án xác thực phù hợp.
- Rate limiting hợp lý.
- CORS và bảo vệ endpoint.
- Không lộ R2 credential.
- Không cho phép truy cập objectKey tùy ý.
- Có health check và logging an toàn.

**3. Tích hợp AudioTP**

- Tạo API client phù hợp.
- Sử dụng danh sách và asset mapping thực tế.
- Xử lý loading, buffering, lỗi mạng và retry.
- Giữ nguyên player chung hiện có.
- Không phát audio mẫu dưới tên bài thật.
- Không yêu cầu media local trên máy người dùng.

**4. Kiểm thử**

- Worker unit tests.
- Mock R2 tests.
- Streaming integration tests.
- HTTP Range tests.
- Authentication tests.
- Network failure tests.
- Kiểm thử media player với audio mẫu được phép.
- Live E2E khi Worker đã được triển khai hợp lệ và có quyền sử dụng nội dung.

**5. Production deployment**

Chuẩn bị:

- Wrangler configuration.
- R2 binding.
- Environment variables.
- Secret management.
- Deployment script.
- Rollback plan.
- Hướng dẫn xác minh sau deploy.

Trước khi thay đổi Cloudflare production, hãy trình bày cấu hình, rủi ro, chi phí dự kiến và yêu cầu tôi phê duyệt.

Không tự deploy live, thay đổi quyền bucket hoặc công bố nội dung audio nếu chưa được phép.

### Tiêu chí nghiệm thu

- Worker hoạt động đúng qua integration test.
- Client có thể phát audio qua API mà không phụ thuộc file local.
- Seek và Range hoạt động.
- Credential không bị lộ.
- Live E2E phải được xác minh riêng, không thay thế bằng mock.
- Có kế hoạch vận hành và rollback.

Nếu live deployment bị chặn vì cần tôi thao tác, đánh dấu BLOCKED hoặc READY FOR REVIEW, không báo DONE toàn bộ.

### Sau khi hoàn thành

Tự đề xuất:

**PHASE 02 — AudioTP Windows Beta**

---

## PHASE 02 — WINDOWS APPLICATION & INSTALLER

### Mục tiêu

Tạo bản AudioTP Windows chạy trong cửa sổ ứng dụng riêng, có thể cài đặt hoặc mở trên máy khác.

### Công nghệ ưu tiên

- Tauri 2.
- Rust/Cargo.
- Microsoft WebView2.
- Frontend hiện có.

Không tự viết lại frontend nếu không cần thiết.

### Công việc

**1. Kiểm tra môi trường**

- Rust/Cargo.
- MSVC.
- Windows SDK.
- Node.js.
- Tauri CLI.
- WebView2 Runtime.

Tự xử lý dependency trong phạm vi cho phép.

Nếu phải cài đặt công cụ hệ thống với quyền admin, cung cấp lệnh cụ thể để tôi chạy.

**2. Hoàn thiện Windows app**

- Tích hợp frontend hiện tại.
- Cấu hình production API.
- Xây EXE.
- Xây installer NSIS nếu khả thi.
- Icon ứng dụng.
- Version metadata.
- Cấu hình cửa sổ.
- Xử lý external links an toàn.
- Kiểm tra quyền truy cập file và API.

**3. Kiểm thử**

- Build debug.
- Build release.
- Khởi chạy EXE thực tế.
- Kiểm tra không phụ thuộc localhost phát triển.
- Kiểm tra không cần Python/Node trên máy đích.
- Kiểm tra WebView2 Runtime.
- Test player, tìm kiếm, tab, Nghe nhanh, yêu thích và lịch sử.
- Test lỗi mạng và reconnect.
- Test EXE trên máy không có workspace AudioTP.

**4. Bản phân phối**

Chuẩn bị:

- EXE/installer.
- README cho người dùng.
- Hướng dẫn cài/gỡ.
- Hướng dẫn xử lý lỗi.
- Danh sách dependency.
- Ghi rõ cảnh báo SmartScreen hoặc hạn chế code signing nếu có.

### Tiêu chí nghiệm thu

- Build Windows thành công.
- EXE khởi động được.
- Frontend được đóng gói đầy đủ.
- Không phụ thuộc file audio local.
- Có khả năng kết nối API online.
- Có bằng chứng kiểm thử thực tế trên Windows.
- Nếu chưa có điều kiện thử máy sạch, ghi rõ NOT VERIFIED.

### Sau khi hoàn thành

Tự đề xuất:

**PHASE 03 — Closed Beta & Auto Update**

---

## PHASE 03 — CLOSED BETA & AUTOMATIC UPDATES

### Mục tiêu

Chuẩn bị AudioTP cho nhóm người dùng thử và xây dựng cơ chế cập nhật phiên bản dễ dàng.

### Công việc

**1. Closed Beta**

- Chuẩn bị bản phân phối Beta.
- Kiểm tra cài đặt trên máy khác.
- Thu thập phản hồi có sự đồng ý của người dùng.
- Kiểm tra phát nhạc trên mạng yếu.
- Test mất mạng và kết nối lại.
- Test cập nhật dữ liệu.
- Kiểm tra hiệu năng và RAM.
- Kiểm tra lỗi khởi động.

**2. GitHub Releases**

- Thiết kế versioning.
- Chuẩn bị release workflow.
- Tạo release notes.
- Tạo và kiểm tra installer artifacts.
- Hash kiểm tra file phát hành.
- Không commit EXE vào source tree.

**3. Tauri Updater**

- Nghiên cứu plugin updater chính thức.
- Tạo quy trình ký cập nhật.
- Giữ private signing key ngoài Git.
- Thiết kế thông báo có bản cập nhật.
- Hỗ trợ cập nhật và khởi động lại phù hợp.
- Test trường hợp không có bản cập nhật.
- Test bản cập nhật không hợp lệ.
- Test lỗi tải bản cập nhật.
- Kiểm tra khả năng rollback/recovery.

**4. Bảo mật phát hành**

- Kiểm tra secret trong artifact.
- Kiểm tra signing key.
- Kiểm tra download integrity.
- Kiểm tra updater không cài nội dung chưa xác minh.
- Đảm bảo release không vô tình kèm media hoặc dữ liệu hạn chế phân phối.

### Tiêu chí nghiệm thu

- Có bản Beta chạy ổn định theo kết quả kiểm thử.
- Release pipeline hoạt động.
- Updater được kiểm thử theo kịch bản hợp lệ và lỗi.
- Có thể nâng cấp từ phiên bản trước lên phiên bản sau.
- Quy trình phát hành có tài liệu rõ ràng.

Phân biệt workflow đã kiểm thử và release thực sự được xuất bản.

### Sau khi hoàn thành

Tự đề xuất:

**PHASE 04 — Mobile Application**

Có thể đề xuất một giai đoạn bug-fix ngắn trước mobile nếu kết quả Beta cho thấy lỗi nghiêm trọng.

---

## PHASE 04 — ANDROID & IOS

### Mục tiêu

Mở rộng AudioTP sang mobile, dùng chung backend và metadata với Windows.

### Nguyên tắc

Windows và mobile là các ứng dụng riêng.

Có thể chia sẻ API, schema, data models và những module hợp lý.

Không bắt buộc chia sẻ toàn bộ UI.

### Công việc

**1. Architecture Research**

So sánh:

- React Native.
- Tauri Mobile.

Dựa trên tiêu chí thực tế:

- Android compatibility.
- iOS compatibility.
- Background audio.
- Lock screen controls.
- Media notifications.
- Bluetooth/headset controls.
- Battery efficiency.
- Audio streaming.
- Offline/cache.
- Build và release.
- Tái sử dụng code hiện có.

Thử prototype nhỏ khi cần.

Ghi quyết định bằng Architecture Decision Record (ADR), không chọn framework chỉ vì dự án Windows đang dùng Tauri.

**2. Android MVP**

- Tạo ứng dụng mobile.
- Kết nối API.
- Catalog.
- Search.
- Ba tab audio.
- Nghe nhanh.
- Player.
- Yêu thích.
- Lịch sử.
- Background audio.
- Điều khiển ngoài ứng dụng.
- Offline/error states.

**3. Kiểm thử**

- Android emulator.
- Android thiết bị thật nếu có.
- Phát nhạc khi khóa màn hình.
- Chuyển mạng Wi-Fi/mobile.
- Kiểm tra kết nối Bluetooth/tai nghe nếu có thiết bị.
- Kiểm tra trạng thái khi app bị đưa xuống nền.
- Kiểm tra quyền truy cập và cache.

**4. Build**

- APK cho testing.
- AAB khi có nhu cầu phát hành qua Play Store.
- Versioning riêng cho mobile.
- Quy trình ký và quản lý khóa an toàn.

**5. iOS**

Sau khi Android MVP ổn định:

- Đánh giá các phần code có thể tái sử dụng.
- Thiết kế build iOS.
- Kiểm tra các yêu cầu công cụ/Apple.
- Chuẩn bị TestFlight khi đủ điều kiện.

Không tuyên bố build iOS thành công khi chưa có môi trường build hoặc thiết bị kiểm thử phù hợp.

### Tiêu chí nghiệm thu

- Android app chạy được.
- Phát audio qua cùng API.
- Background audio hoạt động.
- Không cần thư viện M4A local.
- Có kết quả test emulator và thiết bị thật được phân biệt.
- iOS có kế hoạch hoặc bản build được kiểm thử riêng theo khả năng.

### Sau khi hoàn thành

Tự đề xuất:

**PHASE 05 — THEOLOI Ecosystem Expansion**

---

## PHASE 05 — THEOLOI ECOSYSTEM

### Mục tiêu

Mở rộng từ AudioTP thành hệ sinh thái các công cụ dành cho người theo Kinh Thánh.

### Module dự kiến

**1. Bài ca mới**

- Nâng cấp AudioTP.
- Bổ sung audio cầu nguyện.
- Lời bài hát.
- Lời chạy đồng bộ khi phát.
- Bản nhạc PDF/PNG có quyền sử dụng.
- Playlist.

**2. Thư viện sách lẽ thật**

- Danh mục sách.
- Trình đọc.
- Đánh dấu trang.
- Ghi nhớ tiến độ.
- Tìm kiếm nội dung.

**3. Sách giảng đạo**

- Danh mục.
- Đọc sách.
- Theo dõi tiến độ.
- Tìm ngẫu nhiên nội dung phù hợp.

**4. Kế hoạch đọc hằng ngày**

- Checklist mỗi ngày.
- Lịch đọc.
- Chuỗi ngày đọc liên tiếp.
- Thống kê tiến độ.
- Nhắc đọc nếu người dùng lựa chọn.

**5. Bốc thăm giáo huấn và cầu nguyện**

- Nghiên cứu các chức năng đã phát triển trong dự án Sion.
- Xác định khả năng tái sử dụng logic.
- Thiết kế module chung phù hợp.
- Không sao chép dữ liệu không có quyền sử dụng.

**6. Hướng dẫn thờ phượng**

- Nội dung thờ phượng.
- Công cụ hỗ trợ nhóm nhỏ.
- Khả năng quản lý và cập nhật nội dung.
- Đồng bộ dữ liệu qua backend khi cần.

### Cách triển khai

Không xây tất cả module cùng lúc.

Đầu tiên:

1. Audit ý tưởng và tài nguyên.
2. Ước lượng độ khó.
3. Đánh giá phụ thuộc.
4. Sắp xếp ưu tiên.
5. Đề xuất MVP module đầu tiên.
6. Chờ tôi chọn thứ tự mở rộng.

Không tự xây hệ thống tài khoản, database hoặc microservice lớn chỉ vì dự kiến có nhiều module.

### Tiêu chí nghiệm thu giai đoạn lập kế hoạch

- Có kiến trúc mở rộng.
- Có backlog được ưu tiên.
- Có phân tích quyền sử dụng nội dung.
- Có roadmap phiên bản tiếp theo.
- Có ít nhất một đề xuất MVP cụ thể.

Sau đó triển khai từng module như các phase con riêng.

---

# V. QUY TẮC KỸ THUẬT XUYÊN SUỐT

## 1. Bảo toàn dữ liệu

Không tự sửa các dữ liệu nguồn đã được xác minh.

Nếu cần migration:

- Có backup/rollback.
- Có validation.
- Có migration script.
- Có test.
- Có báo cáo thay đổi.

Không xóa dữ liệu audio hoặc thay đổi R2 objectKey khi chưa được phê duyệt.

## 2. Ưu tiên code có sẵn

Trước khi viết module mới:

- Tìm implementation tương tự.
- Kiểm tra code có thể tái sử dụng.
- Tránh duplication.
- Không refactor ngoài phạm vi nếu không cần thiết.
- Ưu tiên ít thay đổi nhưng đúng chức năng.

## 3. Testing

Sau mỗi thay đổi đáng kể:

- Test chức năng vừa sửa.
- Test module liên quan.
- Regression test trước khi hoàn thành phase.
- Phân biệt test tự động và kiểm thử thủ công.
- Không ghi PASS cho test đã skip hoặc chưa chạy.

Nếu phát hiện lỗi, tự sửa và chạy lại.

## 4. Git workflow

- Không force push.
- Không xóa lịch sử Git.
- Không commit secret.
- Không commit M4A local.
- Không commit cache/build outputs.
- Không sửa dữ liệu production vô điều kiện.
- Không overwrite thay đổi chưa được kiểm tra.
- Ưu tiên branch riêng cho thay đổi lớn và PR khi quy trình repo hỗ trợ.
- Commit theo nhóm thay đổi có ý nghĩa.
- Kiểm tra remote và quyền trước khi push.
- Không tự xóa branch hoặc ghi đè lịch sử người khác.

Nếu có thay đổi không liên quan trong working tree, giữ nguyên và không đưa vào commit của mình.

## 5. An toàn Cloudflare

Không tự:

- Public R2 bucket.
- Xóa hoặc ghi đè audio trên R2.
- Tạo credential mới mà chưa cần thiết.
- Deploy production chưa được duyệt.
- Thay đổi route/domain live.
- Tạo tài nguyên có chi phí chưa được duyệt.

Chuẩn bị đầy đủ kế hoạch và lệnh cho người dùng khi cần.

## 6. Quyền nội dung

Trước khi đưa nội dung bên thứ ba vào artifact phát hành hoặc backend phục vụ người dùng:

- Xác minh quyền sử dụng.
- Xác minh phạm vi phân phối.
- Không mặc định nội dung đã truy cập được là nội dung được phép sao chép.
- Không coi repo Private hay bucket Private là sự cho phép phân phối.

Nếu chưa đủ điều kiện, tiếp tục phát triển bằng dữ liệu mẫu được phép và đánh dấu blocker rõ ràng.

---

# VI. CƠ CHẾ TỰ ĐỀ XUẤT CÔNG VIỆC TIẾP THEO

Đây là yêu cầu bắt buộc.

Sau khi hoàn thành mỗi phase, hãy:

**Bước 1:** Chạy lại các bài kiểm thử cần thiết.

**Bước 2:** Đối chiếu toàn bộ acceptance criteria.

**Bước 3:** Cập nhật ROADMAP.md.

**Bước 4:** Cập nhật CURRENT_PHASE.md.

**Bước 5:** Ghi các quyết định kỹ thuật vào DECISIONS.md.

**Bước 6:** Cập nhật BACKLOG.md và CHANGELOG.md phù hợp.

**Bước 7:** Commit/push các thay đổi được phép, hoặc báo lý do chưa push.

**Bước 8:** Tự đọc roadmap và xác định phase kế tiếp.

**Bước 9:** Đề xuất cho tôi các công việc ưu tiên của phase kế tiếp, theo thứ tự phụ thuộc thực tế.

**Bước 10:** Dừng tại ranh giới phase để tôi xác nhận tiếp tục.

Không hỏi lại các thông tin đã có trong source, docs hoặc roadmap.

Nếu phase kế tiếp chưa khả thi, hãy đề xuất công việc phụ trợ có ích và giải thích nguyên nhân.

Nếu người dùng chỉ nhắn "Tiếp tục", hãy:

1. Đọc CURRENT_PHASE.md và ROADMAP.md.
2. Xác định phase đã được đề xuất gần nhất.
3. Kiểm tra trạng thái repo.
4. Bắt đầu triển khai phase đó.
5. Không yêu cầu người dùng gửi lại Master Prompt.

---

# VII. MẪU BÁO CÁO KẾT THÚC PHASE

Khi hoàn thành giai đoạn, trả lời theo mẫu:

## THEOLOI — Phase XX: [Tên giai đoạn]

**Trạng thái:** DONE / BLOCKED / READY FOR REVIEW

### 1. Đã hoàn thành

Tóm tắt các phần triển khai thực tế.

### 2. Kết quả kiểm thử

- Unit tests:
- Integration tests:
- Browser tests:
- Platform tests:
- Live E2E:
- SKIP/FAIL và nguyên nhân:

### 3. Git

- Branch:
- Commit:
- Push status:
- PR/Release nếu có:

### 4. Những việc chưa hoàn thành

Nêu blocker và tác động.

### 5. Đề xuất giai đoạn tiếp theo

**Phase XX+1: [Tên]**

Vì sao nên làm tiếp?

Ba đến năm công việc ưu tiên trong phase tiếp theo.

Điều kiện cần thiết trước khi bắt đầu.

### 6. Hành động cần người dùng thực hiện

Chỉ nêu những việc thật sự cần người dùng thao tác hoặc phê duyệt.

### 7. Cách tiếp tục

Nếu tôi đồng ý, tôi chỉ cần nhắn:

"Tiếp tục"

Bạn sẽ căn cứ roadmap và báo cáo hiện tại để bắt đầu phase kế tiếp.

---

# VIII. NGUYÊN TẮC QUAN TRỌNG NHẤT

Tôi không muốn một coding agent chỉ hoàn thành task được giao rồi kết thúc mà không biết sản phẩm cần làm gì tiếp theo.

Tôi muốn bạn quản lý tiến độ kỹ thuật có hệ thống.

Mỗi phase cần:

Plan → Implement → Test → Fix → Review → Document → Commit → Recommend Next Phase.

Không dừng giữa phase chỉ để báo cáo tiến độ.

Không tự tuyên bố DONE nếu còn tiêu chí nghiệm thu quan trọng chưa đạt.

Không mở rộng phạm vi vô hạn hoặc tự đưa ra các quyết định production thay tôi.

Ưu tiên tạo ra sản phẩm sử dụng thực tế thay vì chỉ tạo nhiều tài liệu.

Đặc biệt, các phase phải dựa trên trạng thái code và bằng chứng mới nhất.

---

# IX. BẮT ĐẦU THỰC HIỆN

Hãy bắt đầu bằng cách kiểm tra trạng thái refactor và GitHub repository THEOLOI.

Nếu PHASE 00 chưa hoàn thành, tiếp tục hoàn thiện PHASE 00.

Nếu PHASE 00 đã hoàn thành và có đầy đủ bằng chứng, cập nhật roadmap rồi đề xuất PHASE 01.

Không bắt đầu PHASE 01 trước khi hoàn thành kiểm tra PHASE 00, trừ khi tôi đã phê duyệt.

Hãy ghi nhận Master Roadmap này vào hệ thống tài liệu dự án để các phiên Codex tương lai cũng có thể tiếp tục công việc.

**BẮT ĐẦU NGAY.**