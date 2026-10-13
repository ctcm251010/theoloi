# AudioTP 0.2 — Hướng dẫn sử dụng

Lần đầu mở bản ONLINE, phần **Kết nối thư viện** tự hiện để bạn dán mã và chọn Nhớ đăng nhập. Nếu đã nhớ mã và tự kết nối thành công, app vào thư viện trực tiếp. Bạn luôn có thể mở lại phần kết nối trong Cài đặt.

Bản ONLINE mới hỗ trợ mã chung ngắn từ 4 ký tự theo lựa chọn của người quản lý. Mã không có sẵn trong app: nhập mã được cấp một lần rồi chọn Nhớ đăng nhập. Khi quản lý đổi mã, hãy dùng bản app mới; mã cũ đã lưu sẽ bị từ chối và app yêu cầu nhập lại. Không coi mã ngắn là bảo vệ mạnh hoặc chia sẻ mã ra ngoài nhóm nội bộ.

**Bản ONLINE:** dùng API HTTPS đã cấu hình và thư viện R2 private; máy người nghe không cần workspace, Node, Python hoặc media local. Bản LOCAL cũ mở bằng `Mo-AudioTP.cmd` chỉ dùng trên máy phát triển; bản TEST chỉ có âm tự tạo. Chọn đúng installer ONLINE do người quản lý bàn giao.

Nhận bản cài từ người quản lý thư viện. Kết nối Internet, cài và mở AudioTP. Nếu máy thiếu Microsoft Edge WebView2, bộ cài có thể đề nghị cài runtime này; cần Internet. Bản EXE portable cũng cần WebView2 trên máy.

Mở **Cài đặt → Kết nối thư viện**, dán mã truy cập được cấp. Trên máy cá nhân, chọn **Nhớ đăng nhập trên máy này**, rồi bấm **Kết nối**. Bạn không cần học thuộc mã. Windows mã hóa mã đã nhớ theo tài khoản đang dùng và địa chỉ API; lần mở app tiếp theo tự đăng nhập, không tự phát nhạc. Nếu không chọn, mã chỉ giữ trong phiên chạy. Không gửi mã qua ảnh chụp hoặc báo lỗi; đây là mã của AudioTP, không phải mật khẩu Cloudflare.

Chọn **Đăng xuất** hoặc bỏ chọn Nhớ đăng nhập để xóa mã đã nhớ. Đăng xuất dừng player và xóa phiên trong RAM; không thu hồi các thiết bị khác. Trên máy dùng chung, để Nhớ đăng nhập tắt. Trình duyệt preview không có tùy chọn lưu này; không lưu credential vào localStorage. DPAPI không bảo vệ trước phần mềm độc hại đang chạy bằng chính tài khoản Windows của bạn.

Tìm bằng số hoặc tên không dấu; dùng `PL 1` để tìm phụ lục. Hướng dẫn và Nhạc đệm là hai bản của cùng bài; Nhạc ngẫm nghĩ là nhóm riêng. Chuyển tab không tự đổi bài đang phát, hãy chọn bài muốn nghe.

Thanh dưới có phát/dừng, tua và bài trước/sau; desktop có âm lượng. Nút **…** mở ngẫu nhiên, lặp và phát liên tục. Space phát/dừng, ←/→ tua 5 giây, N/P đổi bài, M bật/tắt tiếng khi không nhập văn bản. Điều hướng trên mở Yêu thích/Gần đây; Cài đặt đổi sáng/tối; Bộ lọc chọn chủ đề/phụ lục.

**Nghe nhanh** nằm dưới ba tab. Nhạc ngẫm nghĩ mở danh sách riêng và phát “Tâm Linh Tha Thiết Cầu Nguyện”, bài đầu trong nguồn hiện có. Bấm lại để tạm dừng/phát tiếp; bài tiếp theo tuân theo chế độ phát đã chọn. Hai mục cầu nguyện ghi “Chưa khả dụng” đến khi có nguồn được xác minh, không có âm thanh thay thế. Nhập từ khóa sẽ ẩn Nghe nhanh; xóa từ khóa sẽ hiện lại. Thu gọn thủ công được nhớ, chỉ mở lại khi bạn bấm Mở rộng.

Nếu mất mạng, chờ kết nối lại và bấm **Thử phát lại**. App cố giữ vị trí khi thử lại. Nếu đã nhớ đăng nhập, app thử kết nối lại khi phiên hết hạn. Nếu mã đã bị thu hồi/đổi, cần người quản lý cấp lại; app không retry vô hạn. Nếu Windows không mở được dữ liệu mã hóa, đăng xuất để xóa rồi nhập lại mã.

App không tự tải toàn thư viện. Phiên bản này không lưu cache audio lâu dài; dữ liệu buffer do WebView2 quản lý. Yêu thích, lịch sử và giao diện lưu riêng với mã truy cập đã được Windows mã hóa; session và vé phát chỉ giữ trong RAM.

Chỉ cập nhật từ bản cài chính thức của người quản lý, đóng app trước khi chạy bản cài mới. Chưa có tự động cập nhật hoặc chữ ký phát hành được kiểm chứng. Khi báo lỗi, gửi phiên bản app, tên/số bài và mô tả thao tác; tránh gửi mã truy cập hoặc URL phát tạm thời.

**Tình trạng bản 0.2:** ONLINE Beta dành cho nghiệm thu có kiểm soát. Không coi build thành công hoặc health200 là đã kiểm tra playback R2, native/máy đích hoặc quyền phân phối rộng rãi. Xem [Phase02](phases/phase-02.md) cho bằng chứng và phần còn pending.
