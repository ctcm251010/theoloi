# AudioTP 1.0.3 — Hướng dẫn sử dụng

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

App không tự tải toàn thư viện. Phiên bản này không lưu cache audio lâu dài; dữ liệu buffer do WebView2 quản lý. Yêu thích, lịch sử và giao diện lưu riêng với mã truy cập đã được Windows mã hóa; session và vé phát chỉ giữ trong RAM.

Sau khi kết nối, app kiểm tra phiên bản mới và kiểm tra lại mỗi sáu giờ khi cửa sổ đang hiển thị. Có thể bấm **Cài đặt → Kiểm tra cập nhật**. Khi có bản mới, thông báo nhỏ xuất hiện với nút **Cập nhật**. App chỉ tải bộ cài sau khi bạn bấm nút; phát nhạc tạm dừng, chữ ký và phiên bản được xác minh trước khi mở bộ cài. App đóng để cài đặt; mở lại AudioTP sau khi hoàn tất. Không cần đăng nhập GitHub hoặc tải lại thư viện audio. Nếu lỗi, thông báo có nút Thử lại; bản đang cài vẫn dùng được.

**Đang dùng 1.0.0:** bản này chưa có chức năng cập nhật, nên cần nhận và chạy bộ cài 1.0.1 từ người quản lý một lần. Từ 1.0.1 trở đi hỗ trợ luồng cập nhật trên. Chữ ký updater bảo vệ file cập nhật; đây không phải chữ ký Windows Authenticode, nên Windows vẫn có thể hiện cảnh báo nhà phát hành chưa xác định. Khi báo lỗi, gửi phiên bản app, tên/số bài và mô tả thao tác; tránh gửi mã truy cập hoặc URL phát tạm thời.

**Bản 1.0.0:** phát hành nội bộ theo yêu cầu người quản lý, dùng API HTTPS và R2 private. Người quản lý đã xác nhận bản trước hoạt động và đăng nhập bằng mã ngắn; máy Windows khác và cài/gỡ bản ONLINE còn cần thử thực tế. Bản phát hành chưa có Authenticode hoặc tự cập nhật. Version1.0.0 không thay thế bằng chứng nghiệm thu còn thiếu. Xem báo cáo trong repository: docs/phase02-online-beta.md.

**Gửi sang máy khác:** ưu tiên `AudioTP_1.0.3_x64-setup.exe`. Chạy setup để cài app và shortcut; cần Internet nếu bộ cài phải bổ sung WebView2. Có thể gửi `AudioTP.exe` để chạy portable nếu máy đã có WebView2; không cần chạy setup trong trường hợp đó. Máy nghe vẫn cần Internet để đăng nhập và phát nhạc. Repository GitHub hiện private: người nhận link Release cần có quyền repo, hoặc người quản lý gửi riêng file cài. Mật khẩu chung cấp riêng, không nằm trong release notes.
