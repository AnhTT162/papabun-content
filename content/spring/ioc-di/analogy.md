Một bếp nhà hàng. Đầu bếp làm món bò lúc lắc cần thịt bò, ớt chuông và chảo. Nếu mỗi đầu bếp **tự đi chợ** mua nguyên liệu, mỗi người mua một kiểu, không ai biết trong bếp đang có gì, và muốn thử món với thịt bò Úc thay bò ta thì phải đi dặn từng người.

Nhà hàng làm ngược lại: đầu bếp chỉ ghi lên phiếu **"món này cần gì"**, còn **quản lý kho** chuẩn bị nguyên liệu và đặt sẵn lên bàn trước khi đầu bếp bắt đầu. Đổi nhà cung cấp thịt thì chỉ quản lý kho biết; đầu bếp vẫn nấu như cũ. Hôm kiểm tra chất lượng, kho đưa nguyên liệu mẫu, và đầu bếp không cần biết đó là hàng thử.

Có một tình huống kho không xử lý được: bếp trưởng chỉ bắt đầu khi phụ bếp đã sẵn sàng, còn phụ bếp chỉ bắt đầu khi bếp trưởng đã ký nhận. Không ai bắt đầu được trước.

Đó là [[ioc|Inversion of Control]]: object không tự tạo thứ nó cần, mà nhận từ bên ngoài. Cách "ghi lên phiếu rồi được đưa tới" là [[dependency-injection|Dependency Injection]], phiếu ghi trên constructor là [[constructor-injection|constructor injection]], quản lý kho là container của Spring ([[application-context|ApplicationContext]]), và hai người chờ nhau là [[circular-dependency|circular dependency]].
