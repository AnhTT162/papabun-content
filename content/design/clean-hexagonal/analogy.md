Một chiếc laptop chỉ có vài cổng USB-C. Hãng làm laptop đặt ra chuẩn của cổng; ai làm sạc, màn hình hay ổ cứng muốn cắm vào thì phải theo chuẩn đó. Đổi từ sạc hãng này sang sạc hãng khác, bo mạch bên trong không phải sửa gì.

Có hai loại thiết bị cắm vào. Bàn phím, chuột là thứ **ra lệnh cho** máy: bạn gõ thì máy làm. Máy in, ổ cứng là thứ **máy ra lệnh cho**: máy cần lưu thì gọi ổ cứng. Hôm kiểm tra ở nhà máy, kỹ sư cắm một thiết bị giả lập vào cổng để thử bo mạch, không cần máy in thật.

Không ai thiết kế laptop bằng cách hàn thẳng dây máy in vào bo mạch. Nhưng cũng không ai làm hộp bút với 12 cổng chuẩn hoá: thứ đơn giản thì không cần cổng.

Đó là [[hexagonal-architecture|Hexagonal Architecture]]: lõi nghiệp vụ định nghĩa [[port|port]], còn web, database, broker là adapter cắm vào. Vì chuẩn cổng do bên trong đặt ra, thiết bị phải theo laptop chứ laptop không theo thiết bị: đó là [[dependency-rule|dependency rule]] của [[clean-architecture|Clean Architecture]].
