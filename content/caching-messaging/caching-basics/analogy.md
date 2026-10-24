Một kế toán làm báo cáo cuối tháng. Bảng tỉ giá và danh sách khách hàng lớn chị dùng mỗi ngày nên **để ngay trên bàn**. Hồ sơ dùng vài lần mỗi tuần nằm ở **tủ hồ sơ chung của phòng**: cả năm kế toán cùng lấy từ đó, nhưng mỗi lần phải đứng dậy đi vài bước. Mọi chứng từ gốc nằm trong **kho lưu trữ dưới tầng hầm**: đủ nhất, chính xác nhất, nhưng mỗi lần xuống lấy mất mười phút.

Bàn làm việc thì nhỏ. Khi đầy, chị phải cất bớt thứ gì đó vào tủ, thường là tờ lâu rồi không đụng tới. Và bảng tỉ giá trên bàn có thể đã cũ: sáng nay ngân hàng vừa đổi tỉ giá mà chị chưa in bản mới. Vì vậy chị ghi lên góc mỗi tờ "dùng tới hết hôm nay".

Mỗi người một bàn riêng, nên bảng tỉ giá trên bàn của hai người có thể khác nhau.

Đó chính là [[cache]]: bàn riêng là [[local-cache|cache trong ứng dụng]] (mỗi instance một bản), tủ chung của phòng là [[distributed-cache|cache dùng chung]] như Redis, kho lưu trữ là database. Tỉ lệ lần tìm thấy ngay trên bàn là [[cache-hit-ratio|hit ratio]], dọn bớt khi bàn đầy là [[cache-eviction|eviction]], còn dòng "dùng tới hết hôm nay" là [[ttl|TTL]].
