Trong bếp nhà hàng, đầu bếp đặt món lên **quầy chuyển món** chỉ đủ chỗ cho ba đĩa, phục vụ bàn lấy món từ đó mang ra. Hai bên không cần biết nhau đang làm gì; quầy là chỗ duy nhất họ gặp nhau.

Quầy đầy thì đầu bếp **đứng chờ** có chỗ trống rồi mới nấu tiếp, nên bếp không bao giờ làm nhanh hơn khả năng mang món ra. Quầy trống thì phục vụ **đứng chờ** ở quầy, và bếp gọi khi có món; họ không chạy ra chạy vào hỏi "có món chưa" mỗi giây.

Hết ca, bếp đặt lên quầy một **tấm thẻ "đóng bếp"**. Phục vụ mang nốt các món đứng trước tấm thẻ, gặp tấm thẻ thì về.

Nếu quầy dài vô tận, bếp cứ nấu và chất món lên quầy: món nguội dần vì chờ quá lâu, tới lúc quầy sập.

Trong Java, quầy là [[blocking-queue|`BlockingQueue`]] có giới hạn, đầu bếp đứng chờ là `put()` bị chặn ([[backpressure]]), phục vụ đứng chờ là `take()` bị chặn thay vì [[busy-spin|quay vòng kiểm tra]], tấm thẻ là [[poison-pill|poison pill]], còn quầy vô tận là queue không giới hạn làm đầy heap.
