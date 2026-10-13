# AudioTP 0.2 — Hướng dẫn sử dụng

**Trên máy phát triển hiện tại:** mở `Mo-AudioTP.cmd` trong `D:\Workspace\AudioTP` để chạy bản LOCAL dùng đủ485 Hướng dẫn/485 Nhạc đệm/13 Ngẫm nghĩ thật. Launcher tự mở backend+EXE và app tự kết nối, không nhập mã. Đóng app thì backend do launcher tạo sẽ dừng. Đừng mở bản TEST cũ để nghe Bài ca mới. Bản LOCAL cần workspace/Node/Python/media, chưa phải R2 live; mở EXE trực tiếp cần backend đang chạy. Các hướng dẫn kết nối Internet/mã bên dưới dành cho bản online tương lai.

Nhận bản cài từ người quản lý thư viện. Kết nối Internet, cài và mở AudioTP. Nếu máy thiếu Microsoft Edge WebView2, bộ cài có thể đề nghị cài runtime này; cần Internet. Bản EXE portable cũng cần WebView2 trên máy.

Mở **Cài đặt → Kết nối thư viện**, nhập mã truy cập được cấp rồi bấm **Kết nối**. Bản phát hành được cấu hình sẵn địa chỉ thư viện. Không gửi mã truy cập qua ảnh chụp hoặc báo lỗi. Mã chỉ giữ trong phiên chạy, không lưu lại khi đóng app.

Tìm bằng số hoặc tên không dấu; dùng `PL 1` để tìm phụ lục. Hướng dẫn và Nhạc đệm là hai bản của cùng bài; Nhạc ngẫm nghĩ là nhóm riêng. Chuyển tab không tự đổi bài đang phát, hãy chọn bài muốn nghe.

Thanh dưới có phát/dừng, tua và bài trước/sau; desktop có âm lượng. Nút **…** mở ngẫu nhiên, lặp và phát liên tục. Space phát/dừng, ←/→ tua 5 giây, N/P đổi bài, M bật/tắt tiếng khi không nhập văn bản. Điều hướng trên mở Yêu thích/Gần đây; Cài đặt đổi sáng/tối; Bộ lọc chọn chủ đề/phụ lục.

**Nghe nhanh** nằm dưới ba tab. Nhạc ngẫm nghĩ mở danh sách riêng và phát “Tâm Linh Tha Thiết Cầu Nguyện”, bài đầu trong nguồn hiện có. Bấm lại để tạm dừng/phát tiếp; bài tiếp theo tuân theo chế độ phát đã chọn. Hai mục cầu nguyện ghi “Chưa khả dụng” đến khi có nguồn được xác minh, không có âm thanh thay thế. Nhập từ khóa sẽ ẩn Nghe nhanh; xóa từ khóa sẽ hiện lại. Thu gọn thủ công được nhớ, chỉ mở lại khi bạn bấm Mở rộng.

Nếu mất mạng, chờ kết nối lại và bấm **Thử phát lại**. App cố giữ vị trí khi thử lại. Khi phiên hết hạn, nhập lại mã truy cập.

App không tự tải toàn thư viện. Phiên bản này không lưu cache audio lâu dài; dữ liệu buffer do WebView2 quản lý. Yêu thích, lịch sử và giao diện lưu trên máy; mã truy cập và vé phát không nằm trong dữ liệu này.

Chỉ cập nhật từ bản cài chính thức của người quản lý, đóng app trước khi chạy bản cài mới. Chưa có tự động cập nhật hoặc chữ ký phát hành được kiểm chứng. Khi báo lỗi, gửi phiên bản app, tên/số bài và mô tả thao tác; tránh gửi mã truy cập hoặc URL phát tạm thời.

**Tình trạng bản 0.2:** đã có EXE/installer LOCAL dùng thư viện thật trên máy và bản TEST riêng dùng âm tự tạo. Bản production online chỉ phát hành sau nghiệm thu API live, native trên máy đích, quyền phục vụ và quy trình phân phối. Xem [Phase02](phases/phase-02.md).
