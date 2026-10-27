## Quick

`double` lưu số theo cơ số 2 ([[floating-point|IEEE 754]]) nên không biểu diễn chính xác 0,1; sai số nhỏ cộng dồn thành lệch tiền. **Tiền dùng `BigDecimal` tạo từ `String` hoặc `long` theo [[minor-unit|đơn vị nhỏ nhất]], so bằng `compareTo`, và mọi phép chia hay làm tròn phải ghi rõ [[rounding-mode|`RoundingMode`]].**

## Interview

`double` có 53 bit phần định trị (52 bit lưu tường minh) và số mũ cơ số 2. 0,1 trong hệ nhị phân là phân số tuần hoàn, nên được làm tròn về số gần nhất: `0.1 + 0.2` ra `0.30000000000000004`, cộng 0,1 mười lần ra `0.9999999999999999`. Với tính toán khoa học thì chấp nhận được; với tiền thì không, vì đối soát cần khớp tới từng đồng.

`BigDecimal` lưu một số nguyên không giới hạn (`unscaledValue`) và một [[bigdecimal-scale|scale]]: `12.50` là 1250 với scale 2. Nó [[immutable|bất biến]], mọi phép toán trả object mới.

Bẫy chính:

- `new BigDecimal(0.1)` nhận `double` đã sai sẵn nên ra `0.1000000000000000055511151231257827...`. Dùng `new BigDecimal("0.1")` hoặc `BigDecimal.valueOf(0.1)` (đi qua `Double.toString`). `valueOf` chỉ cứu được literal: `BigDecimal.valueOf(1.1 * 3)` vẫn ra `3.3000000000000003`. Đừng tính bằng `double` rồi mới bọc; nhận tiền từ bên ngoài bằng `String` hoặc `long`.
- `equals` so cả giá trị lẫn scale: `0.00` khác `0`, `1.0` khác `1.00`. So giá trị bằng `compareTo`.
- `divide` không chỉ định scale ném `ArithmeticException: Non-terminating decimal expansion` khi kết quả vô hạn (100/3). Luôn dùng `divide(x, scale, RoundingMode)`.
- Làm tròn: `HALF_UP` là làm tròn kiểu học sinh (2,5 thành 3); `HALF_EVEN` ([[bankers-rounding|banker's rounding]]) đưa về số chẵn (2,5 thành 2, 3,5 thành 4) để sai số không lệch một phía khi cộng nhiều lần. Chọn theo quy định nghiệp vụ hoặc pháp lý, và ghi vào code.

Chia tiền: 100.000 đ chia 3 làm tròn từng phần ra 33.333 × 3 = 99.999, mất 1 đồng. Chia phần nguyên rồi dồn phần dư vào một hoặc vài phần đầu để tổng luôn đúng.

Cách làm đúng: gói tiền vào [[value-object|value object]] `Money(BigDecimal amount, Currency currency)`, chuẩn hoá scale theo loại tiền ngay khi tạo, chỉ làm tròn ở những điểm nghiệp vụ quy định (dòng hoá đơn, tổng thuế), không làm tròn từng bước trung gian.

## Deep

- **Đã chạy JDK 27**: `1.10 * 3` ra `3.3000000000000003`; `Math.round(-2.5)` ra `-2` (làm tròn về phía dương vô cùng), `Math.round(2.5)` ra 3. `(double) 0.1f` ra `0.10000000149011612`: `float` còn tệ hơn.
- **Số chữ số theo loại tiền**: `Currency.getInstance("VND").getDefaultFractionDigits()` là 0, JPY 0, USD 2, KWD 3 (JDK 27), và -1 với mã không phải tiền thật như `XXX`, đưa thẳng vào `setScale` sẽ lỗi. Đừng giả định mọi loại tiền có 2 chữ số thập phân.
- **`BigDecimal` trong `HashMap`/`HashSet`**: `hashCode` phụ thuộc scale, nên `map.get(new BigDecimal("10.00"))` không thấy key `10.0`. `TreeMap` thì thấy vì dùng `compareTo`. `stripTrailingZeros()` chuẩn hoá được nhưng `100` thành `1E+2`.
- **`toString` ra dạng khoa học**: `BigDecimal.valueOf(1e10).toString()` là `1.0E+10`, `stripTrailingZeros()` của 100 là `1E+2`. In ra file, báo cáo hay chữ ký HMAC thì dùng `toPlainString()`.
- **Scale của kết quả**: cộng trừ lấy scale lớn hơn, nhân thì cộng hai scale: `1.10 × 3` ra `3.30`, `19.99 × 0.1` ra `1.999`. Vì vậy cần `setScale` ở điểm làm tròn nghiệp vụ.
- **`MathContext`**: `divide(x, MathContext.DECIMAL64)` giới hạn 16 chữ số có nghĩa, không phải 16 chữ số sau dấu phẩy; hợp cho tỉ lệ trung gian, không hợp cho số tiền cuối cùng.
- **Database**: dùng `NUMERIC(19, 4)` hay `DECIMAL` có độ chính xác cố định; không dùng `FLOAT`/`DOUBLE PRECISION`. Kiểu `money` của PostgreSQL phụ thuộc `lc_monetary` của session, nên tránh. Đọc lên, JDBC trả `BigDecimal` mang scale của cột (`0.0000`), đó là lý do so `equals` với `BigDecimal.ZERO` hỏng.
- **JSON và JavaScript**: số trong JSON bị JavaScript đọc thành `double`; gửi tiền dạng chuỗi (`"12.50"`) hoặc số nguyên đơn vị nhỏ nhất. Jackson đọc số thực vào `double` khi đích là `Object`/`Map` trừ khi bật `USE_BIG_DECIMAL_FOR_FLOATS`, xem bài JSON & Jackson và phần số lớn ở bài Thiết kế REST API. Chiều ghi cũng có bẫy: Jackson 2 mặc định ghi `BigDecimal` bằng `toString()`, nên `1E+2` có thể lọt vào JSON; bật `JsonGenerator.Feature.WRITE_BIGDECIMAL_AS_PLAIN`.
- **Hiệu năng**: phép toán `BigDecimal` chậm hơn `long` nhiều lần và tạo object mới. Vòng lặp tính hàng triệu dòng (rating, báo cáo) có thể tính bằng `long` đơn vị nhỏ nhất rồi đổi sang `BigDecimal` ở biên. `Math.addExact`/`multiplyExact` để không tràn im lặng.
- **Phân bổ theo tỉ lệ** (chia khuyến mãi cho từng dòng hàng): tính phần của từng dòng làm tròn xuống, rồi phân phần dư cho các dòng có phần lẻ lớn nhất (largest remainder) để tổng bằng đúng số gốc và kết quả ổn định giữa các lần chạy.
- **Thư viện**: JSR 354 (Money API, cài đặt Moneta) có `MonetaryAmount`, quy đổi tỉ giá, format theo locale; nặng hơn một record `Money` tự viết, dùng khi cần đa tiền tệ thật sự.
