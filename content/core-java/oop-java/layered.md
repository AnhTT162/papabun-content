## Quick

[[polymorphism|Đa hình]] trong Java chỉ áp dụng cho **method instance được override**: JVM chọn cài đặt theo kiểu thật của object lúc chạy. **Overload, field và method `static` được chọn lúc biên dịch theo kiểu khai báo**, nên không đa hình. Ưu tiên composition, dùng kế thừa khi thật sự là quan hệ "là một".

## Interview

Gọi `animal.speak()` trải qua hai bước. Lúc biên dịch, compiler nhìn kiểu khai báo `Animal` để chọn **chữ ký** method, kể cả chọn giữa các bản [[method-overloading|overload]] theo kiểu tĩnh của tham số. Lúc chạy, lệnh `invokevirtual` tìm cài đặt của chữ ký đó theo **kiểu thật** của object, nên `Dog` override thì chạy bản của `Dog`. Đó là [[dynamic-dispatch]]. JVM tra bảng method (vtable) nên lời gọi gần như không tốn thêm, và [[jit|JIT]] thường inline được khi chỉ thấy một kiểu thật.

Vì overload chọn lúc biên dịch: `Object o = "hi"; printer.print(o)` gọi `print(Object)`, không phải `print(String)`. Bẫy kinh điển là viết `equals(Money other)`: đó là overload, không override `equals(Object)`, nên `HashSet.contains` không dùng tới. Luôn gắn `@Override` để compiler bắt lỗi này.

Field không đa hình: lớp con khai báo field trùng tên là [[field-hiding]], `Animal a = new Dog(); a.name` đọc field của `Animal`. Method `static` cũng chỉ bị che, không override.

[[abstract-class|Abstract class]] có trạng thái, constructor, method `protected`; một class chỉ kế thừa một class. Interface mô tả khả năng; từ Java 8 có [[default-method]] và method `static`, Java 9 có method `private`, nhưng không có field instance.

Kế thừa buộc lớp con phụ thuộc vào cài đặt của lớp cha ([[fragile-base-class]]), nên mặc định nên dùng [[composition-over-inheritance|composition]] và khai báo `final` cho class không thiết kế để kế thừa. Java 17 có [[sealed-class|`sealed`]] để giới hạn đúng những lớp con được phép, hợp với domain có số biến thể cố định và `switch` không cần nhánh `default`.

Bẫy production hay gặp: constructor lớp cha gọi method bị override. Lúc đó field của lớp con chưa được gán, nên lớp con thấy `null` hoặc 0.

## Deep

- **Thứ tự khởi tạo**: `new SalesReport("hn")` cấp phát object với mọi field ở giá trị mặc định, chạy constructor `Report` (gọi `title()` của lớp con), rồi mới chạy initializer và thân constructor của `SalesReport`. Từ Java 25 (JEP 513, Flexible Constructor Bodies) được viết lệnh trước `super(...)`, kể cả gán field của chính class (`this.region = region; super();`), miễn là không đọc `this`; đã chạy JDK 27, lớp cha thấy giá trị. Cách này cứu được code cũ, nhưng quy tắc vẫn là không gọi method có thể override trong constructor. Ngoại lệ gây khó hiểu: field `final` gán bằng [[compile-time-constant|hằng số]] (`private final String prefix = "Doanh so";`) được compiler thay bằng hằng nên vẫn đọc được; field `final` gán bằng `new String("x")` thì ra `null` (đã chạy). Đây cũng là một dạng [[this-escape]]; từ JDK 21 có `javac -Xlint:this-escape`.
- **Overload với boxing và varargs**: compiler chọn theo ba vòng: khớp không cần boxing, rồi có boxing, rồi varargs. Vì thế `List<Integer>.remove(1)` xoá theo index (xem bài Kiểu dữ liệu, autoboxing & pass-by-value).
- **Xung đột default method**: class implement hai interface cùng có `default hi()` thì bắt buộc override và chọn bằng `A.super.hi()`. Quy tắc: method của class luôn thắng default method; interface cụ thể hơn (kế thừa interface kia) thắng; còn lại là lỗi biên dịch.
- **`private`, `static`, `final` không cần tra vtable**: `static` dùng `invokestatic`. Method `private` và `final` vẫn được gọi bằng `invokevirtual` (với `private` là từ Java 11, nhờ nestmates của JEP 181; `invokespecial` giờ chỉ còn cho constructor và `super.x()`), nhưng JVM biết đích là duy nhất nên gọi thẳng. Không có lý do hiệu năng để rắc `final` khắp nơi; JIT tự phát hiện method chưa bị override (class hierarchy analysis) và bỏ tối ưu nếu sau đó nạp lớp con.
- **[[inner-class|Inner class]] giữ tham chiếu tới outer**: inner class (không `static`) và anonymous class nhận outer qua constructor; nếu dùng tới outer thì giữ trong field `this$0`. Đưa object đó vào nơi sống lâu (listener, cache, task chạy nền) thì giữ luôn cả outer, gây rò rỉ bộ nhớ. Từ JDK 18 javac bỏ field `this$0` khi inner class không dùng tới outer (đã kiểm javap trên JDK 27; biên dịch `--release 17` vẫn sinh field). Mặc định khai báo nested class là `static`. Lambda chỉ giữ `this` khi thân lambda dùng tới field hoặc method instance.
- **Enum là class**: enum là lớp con ngầm của `java.lang.Enum`; mỗi hằng là một instance `static final` của chính enum đó (hoặc của lớp con ẩn danh nếu hằng có thân riêng để override method). Constructor luôn `private`. `values()` tạo mảng mới mỗi lần gọi; `valueOf("paid")` ném `IllegalArgumentException` vì phân biệt hoa thường.
- **[[enummap|`EnumMap`]] và `EnumSet`**: lưu theo `ordinal()` trong mảng (EnumSet là bit vector), duyệt theo thứ tự khai báo, nhanh và nhỏ hơn `HashMap`. Dùng `ordinal()` trong bộ nhớ như vậy thì ổn; lưu ra ngoài thì không.
- **Enum singleton**: enum một phần tử chống được reflection và deserialization tạo instance thứ hai; chi tiết và lý do nên để container quản lý thay vì singleton tự viết xem bài Creational patterns.
- **Sealed (Java 17, JEP 409)**: lớp con được phép phải là `final`, `sealed` hoặc `non-sealed`, và nằm cùng module (hoặc cùng package nếu không dùng module). Kết hợp record và `switch` pattern (Java 21) thì thêm biến thể mới sẽ thành lỗi biên dịch ở mọi `switch` chưa xử lý. Chi tiết cú pháp ở bài Java 17 → 21.
- **Composition có giá**: phải viết method chuyển tiếp, và các ví dụ fragile base class trong JDK (`HashSet.addAll` gọi `add`) được phân tích ở bài Nguyên tắc thiết kế; Liskov và đa hình ở bài SOLID.
