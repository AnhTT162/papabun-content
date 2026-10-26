Bấm nút gọi thang máy một lần hay mười lần, thang vẫn chỉ đến một lần. Công tắc đèn gạt sang "bật" thì gạt thêm lần nữa đèn vẫn sáng. Ngược lại, mỗi lần bấm "chuyển 500.000đ" là thêm một khoản tiền đi.

Ở quán phở đông khách, khách nhận một phiếu đánh số ngay khi gọi món. Khách sốt ruột gọi lại "phiếu số 15, hai tô tái nhé", bếp nhìn số phiếu, thấy đã có trong danh sách, nên không nấu thêm hai tô. Nếu không có số phiếu, bếp không phân biệt được "gọi thêm" với "nhắc lại", và quán dễ mang ra bốn tô.

Còn một trường hợp khó hơn: hai phục vụ cùng nhận lời nhắc của bàn 7, cùng chạy vào bếp, cùng nhìn danh sách lúc chưa ai kịp ghi. Cả hai đều nghĩ "chưa có", và bếp lại nấu hai lần. Số phiếu chỉ có tác dụng khi việc "ghi vào danh sách" xảy ra trước, và chỉ một người ghi được.

Thao tác làm nhiều lần cho kết quả như một lần là [[idempotency|idempotent]]. Số phiếu do khách mang theo mỗi lần nhắc lại chính là [[idempotency-key|idempotency key]], và việc hai người cùng kiểm tra rồi cùng làm là lỗi [[check-then-act|check-then-act]].
