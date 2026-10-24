Chuyển 5 triệu cho bạn ở quầy ngân hàng gồm hai việc: trừ tài khoản của bạn và cộng tài khoản người nhận. Nếu giao dịch viên trừ xong thì mất điện, bạn mất 5 triệu mà người nhận không được gì. Ngân hàng phải đảm bảo hai việc đó hoặc cùng xảy ra, hoặc cùng không. Một khi đã đưa biên lai "thành công", dù hệ thống sập ngay sau đó thì giao dịch vẫn phải còn.

Giao dịch viên còn ghi mọi thao tác vào sổ nhật ký trước khi sửa sổ cái. Sập giữa chừng thì sáng hôm sau đọc nhật ký để làm nốt hoặc huỷ phần dở dang.

Trong database, nhóm thao tác "hoặc tất cả, hoặc không gì" là một [[transaction]]. Bốn đảm bảo của nó gọi là [[acid|ACID]]. Sổ nhật ký ghi trước chính là [[wal|write-ahead log]].
