## Quick

Java có 8 kiểu [[primitive-type|primitive]] giữ chính giá trị; mọi thứ khác là [[reference-type|reference]], biến chỉ giữ tham chiếu tới object. **`==` trên reference so tham chiếu, không so giá trị**, và **Java luôn [[pass-by-value]]**: method nhận bản sao của giá trị trong biến, kể cả khi giá trị đó là tham chiếu.

## Interview

Primitive gồm `byte`, `short`, `int`, `long`, `float`, `double`, `char`, `boolean`. Chúng không thể `null`, có giá trị mặc định (0, `false`) khi là field, và phép toán chạy trực tiếp trên giá trị. Mỗi primitive có một [[wrapper-class|wrapper class]] (`Integer`, `Long`...) là object bất biến, dùng được trong generics và collection.

[[autoboxing|Autoboxing]] là cú pháp của compiler: `Integer x = 5` biên dịch thành `Integer.valueOf(5)`, còn `int y = x` thành `x.intValue()`. Từ đó ra ba bẫy:

- `valueOf` trả object có sẵn trong [[integer-cache]] cho giá trị -128..127. Vì vậy `Integer a = 127, b = 127` cho `a == b` là `true`, còn với 128 là `false`. `Long` cũng vậy. So id kiểu `Long` bằng `==` qua được test với id nhỏ rồi sai trên production.
- Unboxing `null` ném `NullPointerException`: `int n = map.get("SKU-1")` khi key không có.
- Toán tử `? :` trộn `int` với `Integer` sẽ unboxing cả nhánh `Integer`, nên `flag ? 1 : map.get(k)` ném NPE dù kết quả gán vào `Integer`.

Pass-by-value: method nhận bản sao tham chiếu. Gọi `list.add(...)` thì bên gọi thấy thay đổi vì hai bản sao cùng trỏ một object. Gán `list = new ArrayList<>()` trong method chỉ đổi bản sao, biến bên gọi giữ nguyên. Vì vậy không viết được hàm `swap(a, b)` cho hai biến của bên gọi.

`final` trên biến nghĩa là **không gán lại**, không phải object bất biến: `final List` vẫn `add` được. `static` nghĩa là thuộc về class, một bản dùng chung cho mọi instance trong classloader đó; field `static` có thể sửa là trạng thái toàn cục, dễ gây [[race-condition|race condition]].

Cách làm đúng: so wrapper bằng `equals` hoặc `Objects.equals`, dùng primitive khi giá trị không thể vắng, và kiểm `null` trước khi unboxing.

## Deep

- **Phạm vi cache**: JLS §5.1.7 bắt buộc cache cho `int`, `short`, `byte` trong -128..127, `char` 0..127 và `boolean`. `Long` cũng cache -128..127 theo cài đặt của JDK. `Float`, `Double` không cache: `Double d1 = 1.0, d2 = 1.0` cho `d1 == d2` là `false`. Riêng trần của `Integer` chỉnh được bằng `-XX:AutoBoxCacheMax=2000` (đã chạy JDK 27: `Integer` 1000 so `==` ra `true`, `Long` 1000 vẫn `false`). Đừng dựa vào cờ này để vá code so `==`.
- **`==` trên `String`** có cùng bẫy so tham chiếu, cộng thêm string pool; xem bài String & String Pool. Hai bẫy số học khác: `Math.abs(Integer.MIN_VALUE)` vẫn âm, và `-7 % 3` ra `-1` (dùng `Math.floorMod`).
- **Constructor wrapper đã bị loại**: `new Integer(5)` bị deprecate từ Java 9 và đánh dấu sẽ xoá từ Java 16 (JEP 390); nó luôn tạo object mới nên `new Integer(5) == new Integer(5)` là `false`. Dùng `valueOf` hoặc autoboxing.
- **`List<Integer>.remove(1)`** gọi `remove(int index)`, không phải `remove(Object)`: compiler ưu tiên overload không cần boxing. Với `[10, 20, 30]`, `remove(1)` xoá 20. Muốn xoá giá trị thì viết `remove(Integer.valueOf(10))`.
- **`Long.equals` so cả kiểu**: `Long.valueOf(1000L).equals(1000)` là `false` vì `1000` boxing thành `Integer`. Gặp khi so id `Long` với số đọc từ JSON hay map kiểu `Object`.
- **Helpful NPE** (JEP 358, bật mặc định từ Java 15) chỉ đúng chỗ unboxing: `Cannot invoke "java.lang.Integer.intValue()" because the return value of "java.util.Map.get(Object)" is null`. Thấy `intValue()` trong message là biết lỗi do unboxing.
- **[[integer-overflow|Tràn số]] im lặng**: `long micros = 24 * 60 * 60 * 1000 * 1000;` ra `500654080` vì phép nhân chạy trên `int` rồi mới gán sang `long`. Viết `24L * ...`, hoặc dùng `Math.multiplyExact`/`addExact` để ném `ArithmeticException` khi tràn. Ép `(int) 3_000_000_000L` ra `-1294967296`.
- **Nới kiểu vẫn mất chính xác**: `int` sang `float` không cần ép nhưng `float` chỉ có 24 bit mantissa, nên `16_777_217` thành `16777216`. Tiền tệ và `double` xem bài Số thực & tiền tệ.
- **Toán tử gán kép tự ép kiểu**: `short s = 10; s = s + 5;` không biên dịch, còn `s += 5;` thì được vì `+=` ngầm ép về `short`, có thể tràn mà không báo.
- **[[compile-time-constant|Hằng số lúc biên dịch]] bị chép vào nơi dùng**: field `static final` kiểu primitive hoặc `String` khởi tạo bằng hằng được compiler chép thẳng vào class gọi. Đã chạy: thư viện đổi `MAX_ITEMS` từ 50 lên 100, chỉ biên dịch lại thư viện, class gọi vẫn in 50; field `static final Integer` thì in 100 vì không phải hằng. Đổi hằng public của thư viện phải biên dịch lại mọi nơi dùng.
- **`final` field còn có ý nghĩa đa luồng**: giá trị gán trong constructor được đảm bảo thấy được khi object được công bố qua [[data-race|data race]], xem bài Java Memory Model. Đó là lý do [[immutable|object bất biến]] an toàn chia sẻ.
- **Chi phí boxing**: mỗi `Integer` là object 16 byte cộng 4 byte tham chiếu (compressed oops), nằm rải trên heap; `Map<Long, Long>` một triệu entry tốn cỡ 70 MB so với 16 MB cho hai `long[]`. Số đo và ảnh hưởng tới cache CPU xem bài Cấu trúc dữ liệu và bài CPU, bộ nhớ & latency numbers. [[jit|JIT]] đôi khi khử được boxing nhờ escape analysis, nhưng đừng trông vào nó trong vòng lặp nóng.
