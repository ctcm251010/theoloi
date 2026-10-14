# AudioTP 1.1.0 — Hướng dẫn sử dụng

**Bản ONLINE1.1.0:** API hỗ trợ tải offline đã được triển khai và kiểm tra với một bài thật. Người quản lý đã thử chức năng offline cơ bản. Bộ cài không chứa thư viện audio hoặc mật khẩu; tải bài cần kết nối thư viện. Xem ghi chú nghiệm thu máy khác trong báo cáo phát hành.

Lần đầu mở bản ONLINE, phần **Kết nối thư viện** tự hiện để bạn dán mã và chọn Nhớ đăng nhập. Nếu đã nhớ mã và tự kết nối thành công, app vào thư viện trực tiếp. Bạn luôn có thể mở lại phần kết nối trong Cài đặt.

Bản ONLINE mới hỗ trợ mã chung ngắn từ 4 ký tự theo lựa chọn của người quản lý. Mã không có sẵn trong app: nhập mã được cấp một lần rồi chọn Nhớ đăng nhập. Khi quản lý đổi mã, hãy dùng bản app mới; mã cũ đã lưu sẽ bị từ chối và app yêu cầu nhập lại. Không coi mã ngắn là bảo vệ mạnh hoặc chia sẻ mã ra ngoài nhóm nội bộ.

**Bản ONLINE:** dùng API HTTPS đã cấu hình và thư viện R2 private; máy người nghe không cần workspace, Node, Python hoặc media local. Bản LOCAL cũ mở bằng `Mo-AudioTP.cmd` chỉ dùng trên máy phát triển; bản TEST chỉ có âm tự tạo. Chọn đúng installer ONLINE do người quản lý bàn giao.

Nhận bản cài từ người quản lý thư viện. Kết nối Internet, cài và mở AudioTP. Nếu máy thiếu Microsoft Edge WebView2, bộ cài có thể đề nghị cài runtime này; cần Internet. Bản EXE portable cũng cần WebView2 trên máy.

Mở **Cài đặt → Kết nối thư viện → Mật khẩu chung**, nhập mật khẩu người quản lý cấp rồi bấm **Kết nối**. Trên máy cá nhân, chọn **Nhớ đăng nhập trên máy này** để Windows mã hóa và lưu theo tài khoản đang dùng/địa chỉ API; lần mở sau tự đăng nhập, không tự phát nhạc. Mật khẩu không điền sẵn trong bộ cài và không phải mật khẩu Cloudflare. Không gửi mật khẩu trong ảnh chụp hoặc báo lỗi.

Chọn **Đăng xuất** hoặc bỏ chọn Nhớ đăng nhập để xóa mã đã nhớ. Đăng xuất dừng player và xóa phiên trong RAM; không thu hồi các thiết bị khác. Trên máy dùng chung, để Nhớ đăng nhập tắt. Trình duyệt preview không có tùy chọn lưu này; không lưu credential vào localStorage. DPAPI không bảo vệ trước phần mềm độc hại đang chạy bằng chính tài khoản Windows của bạn.

Tìm bằng số hoặc tên không dấu; dùng `PL 1` để tìm phụ lục. Hướng dẫn và Nhạc đệm là hai bản của cùng bài; Nhạc ngẫm nghĩ là nhóm riêng. Chuyển tab không tự đổi bài đang phát, hãy chọn bài muốn nghe.

Thanh dưới có phát/dừng, tua và bài trước/sau; desktop có âm lượng. Nút **…** mở ngẫu nhiên, lặp và phát liên tục. Space phát/dừng, ←/→ tua 5 giây, N/P đổi bài, M bật/tắt tiếng khi không nhập văn bản. Điều hướng trên mở Yêu thích/Gần đây; Cài đặt đổi sáng/tối; Bộ lọc chọn chủ đề/phụ lục.

**Nghe nhanh** nằm dưới ba tab. Nhạc ngẫm nghĩ mở danh sách riêng và phát “Tâm Linh Tha Thiết Cầu Nguyện”, bài đầu trong nguồn hiện có. “Cầu nguyện chúng con mong muốn” phát bản thu riêng khoảng 1:09. “Nhạc không lời cầu nguyện thống thanh” phát bản thu riêng khoảng 5:11, từ bản1.0.3. Bấm lại để tạm dừng/phát tiếp; tất cả dùng chung player. Bài cầu nguyện không thuộc ba tab đánh số, chưa lưu vào Yêu thích/Gần đây. Nhập từ khóa sẽ ẩn Nghe nhanh; xóa từ khóa sẽ hiện lại. Thu gọn thủ công được nhớ, chỉ mở lại khi bạn bấm Mở rộng.

Nếu mất mạng, chờ kết nối lại và bấm **Thử phát lại**. App cố giữ vị trí khi thử lại. Nếu đã nhớ đăng nhập, app thử kết nối lại khi phiên hết hạn. Nếu mã đã bị thu hồi/đổi, cần người quản lý cấp lại; app không retry vô hạn. Nếu Windows không mở được dữ liệu mã hóa, đăng xuất để xóa rồi nhập lại mã.

App không tự tải toàn thư viện. Trong bản Windows, dùng icon tải ở từng bài hoặc **Tải về** dưới Bộ lọc để tải nhóm/toàn bộ. Xác nhận cho biết số bài còn thiếu và dung lượng; file được kiểm tra SHA-256 trước khi công nhận hoàn tất. Có tạm dừng/tiếp tục/hủy/thử lại. Dữ liệu lưu trong thư mục ứng dụng của Windows, được giữ khi cập nhật; session/vé phát chỉ trong RAM.

**Nghe offline** lọc cả ba tab, tìm kiếm, yêu thích và gần đây theo bài đã tải. Chọn **Nghe online** để trở lại; bài đã tải vẫn được ưu tiên phát local. Đủ manifest hiện hành thì app mặc định offline và ẩn nút tải chung; xóa bài sẽ hiện lại. Nút thùng rác và dấu kiểm từng bài cho xóa file trên máy, không xóa bản gốc R2. Hai mục cầu nguyện riêng hiện phát online, chưa nằm trong phạm vi tải983 bài chính. Không có mạng vẫn nghe bài đã tải mà không cần đăng nhập lại.

Bấm **Nghe online** sẽ hiện **Đang kết nối…** trong lúc kiểm tra. Nếu chưa truy cập được thư viện, ứng dụng giữ offline và hiện lời nhắc kiểm tra Internet; bài đã tải vẫn nghe được. Khi mạng trở lại, bấm Nghe online để thử lại.

Khi khởi động, app kiểm tra phiên bản ở nền với timeout; không có mạng hoặc đã mới nhất thì im lặng. Có thể bấm **Cài đặt → Kiểm tra cập nhật**. Khi có bản mới, modal giữa cửa sổ có **Để sau** và **Cập nhật ngay**. Chỉ tải sau khi bạn bấm; cần kết nối thư viện để xác minh gói chính thức. Có tiến độ, kiểm tra chữ ký/phiên bản trước cài, rồi đóng/mở lại theo installer hỗ trợ. Không cần đăng nhập GitHub hoặc tải lại audio offline. Nếu lỗi, bản đang cài vẫn dùng được. “Để sau” được tôn trọng tới lần mở app tiếp theo; kiểm tra thủ công vẫn mở lại thông báo.

**Đang dùng 1.0.0:** bản này chưa có chức năng cập nhật, nên cần nhận và chạy bộ cài 1.0.1 từ người quản lý một lần. Từ 1.0.1 trở đi hỗ trợ luồng cập nhật trên. Chữ ký updater bảo vệ file cập nhật; đây không phải chữ ký Windows Authenticode, nên Windows vẫn có thể hiện cảnh báo nhà phát hành chưa xác định. Khi báo lỗi, gửi phiên bản app, tên/số bài và mô tả thao tác; tránh gửi mã truy cập hoặc URL phát tạm thời.

**Bản 1.0.0:** phát hành nội bộ theo yêu cầu người quản lý, dùng API HTTPS và R2 private. Người quản lý đã xác nhận bản trước hoạt động và đăng nhập bằng mã ngắn; máy Windows khác và cài/gỡ bản ONLINE còn cần thử thực tế. Bản phát hành chưa có Authenticode hoặc tự cập nhật. Version1.0.0 không thay thế bằng chứng nghiệm thu còn thiếu. Xem báo cáo trong repository: docs/phase02-online-beta.md.

**Cài đặt:** ưu tiên `AudioTP_1.1.0_x64-setup.exe` khi gửi máy khác. Chạy setup để cài app/shortcut; cần Internet nếu phải bổ sung WebView2. `AudioTP.exe` chạy portable khi máy đã có WebView2. Cần mạng để đăng nhập/tải lần đầu, sau đó file offline hợp lệ phát không cần mạng. Repository GitHub được quan sát là Public ngày15/10; bộ cài và source có thể tải qua Release, còn thư viện R2 vẫn private. Mật khẩu chung cấp riêng, không nằm trong release notes. Bản1.0.1/1.0.3 kiểm tra cập nhật trong Cài đặt;1.0.0 cần cài setup mới một lần. Xem `docs/offline-updates-guide.vi.md` để hiểu cách lưu file và quy trình build/phát hành.
