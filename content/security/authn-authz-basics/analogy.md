Bạn tới làm việc ở một toà văn phòng. Lần đầu, lễ tân **xem CCCD và đối chiếu mặt** với danh sách khách hẹn. Đó là bước xác minh bạn là ai. Xong, lễ tân phát một **thẻ từ**, để từ giờ bạn chỉ cần quẹt thẻ chứ không phải trình CCCD ở mỗi cửa.

Quẹt thẻ ở cổng tầng 12 thì cửa mở, ở phòng máy chủ thì đèn đỏ. Thẻ vẫn là thẻ thật, chỉ là **bạn không được vào phòng đó**. Mỗi cửa tự hỏi hệ thống: thẻ này có được mở cửa này không.

Toà nhà có hai kiểu thẻ. Thẻ từ của nhân viên chỉ mang một số, bảo vệ tra số đó trong máy: báo mất là khoá ngay. Vé giấy cho khách sự kiện thì in sẵn tên, khu được vào và giờ hết hạn, có đóng dấu: cửa nào cũng đọc được mà không cần gọi về quầy, nhưng ai nhặt được vé thì dùng được tới giờ hết hạn.

Xem CCCD là [[authentication|authentication]], cửa kiểm quyền là [[authorization|authorization]]. Thẻ từ tra trong máy là [[http-session|session]], vé giấy có dấu là token tự chứa như [[jwt|JWT]]. Còn danh sách khách hẹn của lễ tân không ghi CCCD gốc mà chỉ giữ thứ đủ để đối chiếu, giống như [[password-hashing|băm mật khẩu]].
