Ngày trước muốn gọi một cửa hàng mà không có số, bạn gọi tổng đài hỏi số. Tổng đài viên không thuộc hết; họ tra danh bạ theo tỉnh, rồi theo ngành, rồi mới ra số. Cả xóm hay hỏi cùng một số nên cô hàng nước ở đầu ngõ chép lại vào sổ để trả lời ngay, nhưng sổ của cô có thể đã cũ nếu cửa hàng vừa đổi số.

Một sàn thương mại điện tử không giao mọi đơn từ kho chính ở Bình Dương. Hàng bán chạy được để sẵn ở kho vệ tinh gần khách tại Hà Nội, Đà Nẵng. Khách đặt thì kho gần nhất giao trong ngày; kho vệ tinh hết hàng thì mới gọi về kho chính. Đổi mẫu mã thì phải báo các kho vệ tinh thu hồi hàng cũ, hoặc đặt mã sản phẩm mới để khỏi lẫn.

Tổng đài là [[recursive-resolver|recursive resolver]], danh bạ theo tỉnh và ngành là chuỗi [[authoritative-dns|authoritative DNS]], cuốn sổ đầu ngõ là cache có [[ttl|TTL]]. Kho vệ tinh là [[edge-location|edge]] của [[cdn|CDN]], kho chính là origin, mã sản phẩm là [[cache-key|cache key]], còn thu hồi hàng cũ là [[cache-purge|purge]].
