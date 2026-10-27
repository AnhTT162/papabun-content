## Quick

Generics chỉ kiểm tra kiểu **lúc biên dịch**; lúc chạy, [[type-erasure|type erasure]] xoá tham số kiểu, `List<String>` và `List<Integer>` là cùng một class `ArrayList`. **Kiểu generic là bất biến (`List<Integer>` không phải `List<Number>`), dùng [[wildcard]] theo [[pecs|PECS]] để API linh hoạt, và không bỏ qua cảnh báo `unchecked`**: đó là chỗ kiểu sai lọt vào và nổ ở nơi khác.

## Interview

Compiler kiểm tra kiểu, chèn ép kiểu ở chỗ đọc, rồi xoá tham số kiểu: `T` thành cận trên của nó (`Object`, hoặc `Comparable` nếu khai báo `T extends Comparable<T>`). Hệ quả: không viết được `new T()`, `new T[10]`, `x instanceof List<String>` với `x` kiểu `Object`, hay hai overload `process(List<String>)` và `process(List<Integer>)` (cùng chữ ký sau khi xoá).

**Bất biến**: nếu `List<Integer>` là `List<Number>` thì ai đó có thể `add(2.5)` vào list số nguyên. Mảng thì hiệp biến (`Integer[]` là `Number[]`) và JVM kiểm lúc chạy bằng `ArrayStoreException`; generics chọn chặn lúc biên dịch.

**Wildcard và PECS** (Producer Extends, Consumer Super):

- `List<? extends Number>`: nguồn để **đọc** ra `Number`; không thêm được gì (trừ `null`) vì không biết kiểu thật.
- `List<? super Integer>`: đích để **ghi** `Integer` vào; đọc ra chỉ được `Object`.
- Ví dụ trong JDK: `Collections.copy(List<? super T> dest, List<? extends T> src)`, `Comparator<? super T>`.

**[[raw-type|Raw type]]** (`List` không tham số) tắt kiểm tra kiểu và chỉ sinh cảnh báo. Code cũ hoặc reflection nhét một `Integer` vào `List<String>` mà không lỗi; `ClassCastException` nổ sau đó ở chỗ **đọc**, có thể cách xa hàng nghìn dòng. Đó là [[heap-pollution|heap pollution]].

Bẫy hay gặp: dùng raw type, `@SuppressWarnings("unchecked")` cho cả class, trả `List<? extends T>` ra ngoài (bắt bên gọi xử lý wildcard), và mảng generic qua varargs.

Cách làm đúng: wildcard ở **tham số** của API, kiểu cụ thể ở **giá trị trả về**; chặn cảnh báo `unchecked` ở phạm vi nhỏ nhất kèm lý do; ở biên với code không an toàn kiểu, kiểm bằng `Collections.checkedList` hoặc `Class.cast`.

## Deep

- **Đã chạy JDK 27 (lab)**: method raw `rows.add(12345)` vào `List<String>` không lỗi; in list ra `[An, 12345]`, `size()` là 2; lỗi chỉ nổ khi duyệt tới phần tử thứ hai với `Integer cannot be cast to class String`. `new ArrayList<String>().getClass() == new ArrayList<Integer>().getClass()` là `true`.
- **[[bridge-method|Bridge method]]**: `Price implements Comparable<Price>` có `compareTo(Price)`, nhưng interface sau khi xoá kiểu là `compareTo(Object)`. Compiler sinh thêm `compareTo(Object)` ép kiểu rồi gọi bản thật (`javap -p` thấy cả hai). Gọi qua kiểu raw `Comparable` với đối số sai kiểu thì bridge ném `ClassCastException`; trong stack trace, bridge hiện thành một dòng `compareTo` thừa.
- **Varargs generic**: `static <T> T[] toArray(T... xs)` gọi từ một method generic khác tạo `Object[]` vì `T` đã bị xoá; gán kết quả cho `String[]` ném `ClassCastException: [Ljava.lang.Object; cannot be cast to [Ljava.lang.String;` (đã chạy). `@SafeVarargs` chỉ đặt khi method không ghi vào mảng và không để mảng lọt ra ngoài; `List.of(E...)` là ví dụ đúng.
- **[[reifiable-type|Kiểu reifiable]]** là kiểu còn đầy đủ thông tin lúc chạy: primitive, class không generic, raw type, `List<?>`. Chỉ kiểu reifiable mới dùng được với `instanceof` (trước Java 16) và làm kiểu phần tử của mảng; từ Java 16, `instanceof` cho phép kiểu generic nếu compiler chứng minh được là an toàn (ép từ `Collection<String>` sang `List<String>`).
- **Tạo object kiểu `T`**: truyền `Class<T>` hoặc `Supplier<T>` (`Map<K, List<V>>` dùng `computeIfAbsent(k, x -> new ArrayList<>())`). `Class<T>` không biểu diễn được `List<Order>`; khi đó cần type token như `TypeReference`.
- **Cận đệ quy**: `<T extends Comparable<? super T>>` (chữ ký của `Collections.sort`) cho phép `LocalDate` dùng được dù nó implement `Comparable<ChronoLocalDate>` chứ không phải `Comparable<LocalDate>`.
- **Wildcard capture**: không gọi được `list.set(0, list.get(0))` trên `List<?>`; viết method helper `<T> void swap(List<T> l)` để compiler "bắt" kiểu ẩn danh.
- **Erasure và functional interface**: `apply(Function<String, Integer> f)` và `apply(Function<Integer, String> f)` là name clash vì cùng xoá thành `apply(Function)`; đặt tên khác. Lambda và overload `submit(Callable)`/`submit(Runnable)` ở bài Java 8 → 11.
- **Những thứ không làm được với `T`**: `catch (T e)`, field `static T`, `T.class`. Cận giao `<T extends Number & Comparable<T>>` yêu cầu `T` thoả cả hai, erasure lấy cận đầu tiên (`Number`).
- **Kiểu primitive không làm tham số kiểu được**: `List<int>` không hợp lệ, nên mọi collection generic phải boxing (bài Kiểu dữ liệu, autoboxing & pass-by-value). Project Valhalla (JEP 401 và các JEP sau) nhắm sửa điều này; JDK 27 chưa có (`value class` không biên dịch kể cả với `--enable-preview`), kiểm lại khi nâng JDK.
- **Kotlin và Scala** có variance khai báo ở định nghĩa (`out T`, `in T`) thay vì ở chỗ dùng như wildcard của Java; Kotlin còn có `reified` cho hàm inline. Hữu ích khi đọc code đa ngôn ngữ.
