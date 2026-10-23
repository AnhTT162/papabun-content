Một quán phở có **2 đầu bếp chính** làm cả ngày, **4 ghế chờ** trước quầy, và chủ quán có số điện thoại của **2 người phụ bếp** có thể gọi tới khi cần. Khách mới vào: nếu còn đầu bếp chính chưa có việc thì đầu bếp đó nấu ngay. Hết đầu bếp rảnh thì khách **ngồi ghế chờ**.

Điểm bất ngờ: chủ quán **không gọi phụ bếp khi đầu bếp chính bận**, mà chỉ gọi khi **ghế chờ đã kín**. Phụ bếp tới thì nấu luôn cho vị khách vừa bước vào, còn khách đang ngồi chờ vẫn chờ. Đã đủ 2 phụ bếp mà ghế chờ vẫn kín thì khách tiếp theo bị **mời về**. Phụ bếp ngồi không quá 30 phút thì được cho về.

Đó chính là cách `ThreadPoolExecutor` hoạt động: đầu bếp chính là [[core-pool-size|core threads]], ghế chờ là [[work-queue|work queue]], phụ bếp là thread thêm tới [[maximum-pool-size|maximumPoolSize]] và được cho về sau [[keep-alive-time|keepAliveTime]], còn mời khách về là [[rejection-policy|rejection policy]].
