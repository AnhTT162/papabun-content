## Quick

[[lambda-expression|Lambda]] là cài đặt ngắn gọn của một [[functional-interface|functional interface]] (interface có đúng một method abstract). Nó không tạo class lúc biên dịch mà được dựng lúc chạy qua [[invokedynamic]]. **Lambda chỉ đọc được biến local [[effectively-final|effectively final]]; `this` trong lambda là object bao ngoài; [[method-reference|method reference]] `obj::m` tính `obj` ngay lúc tạo**, còn lambda `() -> obj.m()` tính lúc chạy.

## Interview

**Lambda bên trong**: javac đưa thân lambda vào một method `private static` (hoặc instance nếu dùng `this`) của class bao, và tại chỗ dùng sinh lệnh `invokedynamic`. Lần chạy đầu, `LambdaMetafactory` sinh một class ẩn implement interface; lambda không capture gì thì HotSpot hiện tại dùng lại một instance (JLS không bảo đảm, đừng dựa vào danh tính của lambda). Anonymous class thì tạo file `Outer$1.class`, mỗi lần chạy `new` một object, và `this` trỏ tới chính anonymous object.

**Capture**: lambda chép giá trị biến local vào object của nó, nên biến phải không bị gán lại (effectively final). Muốn đếm trong lambda thì dùng `AtomicInteger`, `LongAdder`, hoặc tốt hơn là `count()`/`reduce` của stream.

**Functional interface** trong `java.util.function`: `Function<T,R>`, `Supplier<T>`, `Consumer<T>`, `Predicate<T>`, `BiFunction`, và bản primitive (`IntPredicate`, `ToLongFunction`) để tránh boxing. Không cái nào trong `java.util.function` khai báo `throws`, nên lambda gọi code ném checked exception phải bọc lại hoặc tự định nghĩa interface `ThrowingFunction`. `@FunctionalInterface` chỉ để compiler kiểm.

**Method reference** có bốn dạng: static (`Integer::parseInt`), method của object có sẵn (`log::info`), method instance của tham số (`String::length`), constructor (`ArrayList::new`). Với dạng `obj::m`, `obj` được đánh giá **ngay lúc tạo**: `null` thì NPE ngay, và object được giữ lại kể cả khi field sau đó trỏ sang object khác.

**[[local-variable-type-inference|`var`]]** (Java 10) suy luận kiểu biến local từ vế phải lúc biên dịch, vẫn là kiểu tĩnh. Bẫy: `var list = new ArrayList<>();` ra `ArrayList<Object>`; `var x = 1;` là `int` dù bạn định `long`; `var` cho kiểu cài đặt (`ArrayList`) chứ không phải interface. Không dùng cho field, tham số, kiểu trả về.

API nhỏ hay dùng: `List.of`/`Map.of` (9), `Optional.orElseThrow()` và `Collectors.toUnmodifiableList` (10), `String.isBlank`, `strip`, `lines`, `repeat`, `Files.readString`, `HttpClient` (JEP 321) và chạy thẳng file nguồn `java App.java` (JEP 330) ở 11. Thêm: try-with-resources nhận biến effectively final (9), `var` trong tham số lambda để gắn annotation (11, JEP 323), `Predicate.not` và `Optional.isEmpty` (11).

## Deep

- **Đã chạy JDK 27**: field `conn` đổi từ kết nối 1 sang 2; runnable tạo bằng `conn::send` vẫn gửi qua kết nối 1, runnable `() -> conn.send()` gửi qua kết nối 2. Với `String name = null`, lambda `() -> name.toUpperCase()` tạo được và chỉ NPE khi gọi, còn `name::toUpperCase` NPE ngay dòng tạo. Lớp lambda có tên chứa `$$Lambda`, anonymous class là `F1$1`.
- **Lambda capture `this` ngầm**: lambda dùng field hay method instance giữ tham chiếu tới object bao; gửi lambda đó vào executor hay cache sống lâu là giữ cả object, giống inner class (bài OOP trong Java).
- **Lambda không serializable** trừ khi kiểu đích là `Serializable` (`(Runnable & Serializable) () -> ...`), và hình thức serialize phụ thuộc tên method sinh ra; đừng serialize lambda qua mạng.
- **Stack trace có `lambda$process$0`**: tên method tổng hợp cho thân lambda; số cuối là thứ tự trong class. Trace sâu qua stream có thêm nhiều frame của `java.util.stream`, đọc từ frame đầu tiên thuộc package của bạn.
- **Overload mơ hồ**: `submit(Callable<T>)` và `submit(Runnable)` phân biệt bằng việc lambda có trả giá trị không; `executor.submit(() -> { throw new IOException(); })` biên dịch được và chọn `Callable`: thân lambda tương thích cả hai, luật chọn overload cụ thể nhất ưu tiên interface có kiểu trả về (đã chạy JDK 27, `Future.get()` ném `ExecutionException` bọc `IOException`).
- **`trim()` và `strip()`**: `trim` chỉ bỏ ký tự có mã ≤ U+0020; `strip` (11) dùng `Character.isWhitespace`. Chuỗi bọc em space U+2003 sau `trim` vẫn dài 5, sau `strip` còn 3 (đã chạy). Dữ liệu copy từ Word, web hay có ký tự này.
- **Interface có method `private`** từ Java 9 để chia sẻ code giữa các [[default-method|default method]].
- **Java 9 module system (JPMS)** và việc JDK 9+ tách module, bỏ Java EE (JAXB, JAX-WS bị xoá ở Java 11 theo JEP 320) là nguyên nhân chính của lỗi khi nâng từ 8; xem bài Java 17 → 21 cho phần nâng cấp và bài Classpath, JPMS & xung đột dependency.
- **Hiệu năng**: lambda không capture gần như miễn phí sau lần đầu; lambda capture tạo object mỗi lần chạy qua (thường được escape analysis khử). Lần gọi đầu tiên của mỗi lambda tốn chi phí dựng class, góp vào thời gian khởi động; CDS và AOT cache (JDK 24+) giảm phần này.
- **Phiên bản LTS**: 8, 11, 17, 21, 25 là bản hỗ trợ dài hạn; từ Java 10 mỗi 6 tháng có một bản mới. Thư viện thường đặt baseline theo LTS (Spring Boot 3 cần Java 17).
