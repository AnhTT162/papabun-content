## Quick

`null` là "không trỏ tới object nào"; gọi method trên nó ném `NullPointerException`. [[optional|`Optional`]] là **kiểu trả về** báo cho bên gọi "có thể không có kết quả", không phải cách thay mọi `null`. **Không dùng `Optional` cho field, tham số hay phần tử collection; không gọi `get()` khi chưa kiểm.**

## Interview

NPE xảy ra khi gọi method hay đọc field trên `null`, [[autoboxing|unboxing]] `null` (xem bài Kiểu dữ liệu, autoboxing & pass-by-value), `switch` trên chuỗi `null`, hoặc ném `throw null`. Từ Java 15, [[helpful-npe|helpful NPE]] nói rõ biểu thức nào `null`, ví dụ `because the return value of "java.util.Map.get(Object)" is null`, nên đọc message trước khi đoán.

`Optional` (Java 8) bọc một giá trị có thể vắng. Dùng đúng:

- Tạo bằng `Optional.ofNullable(x)`; `Optional.of(null)` ném NPE ngay.
- Lấy giá trị bằng `orElseThrow()` (Java 10), `orElse`, `orElseGet`, hoặc biến đổi bằng `map`, `flatMap`, `filter`, `ifPresentOrElse` (Java 9), `or` (Java 9), `isEmpty` (Java 11), hoặc `stream()` (Java 9) để nối vào stream.
- `orElse(x)` **luôn tính `x`** trước khi gọi, kể cả khi đã có giá trị. Nếu `x` là lời gọi tốn kém hay có tác dụng phụ (gọi API, INSERT) thì dùng `orElseGet(() -> ...)`.

Anti-pattern hay gặp: `opt.isPresent()` rồi `opt.get()` (chỉ là `null` check dài hơn); trả `Optional<List<T>>` thay vì list rỗng; trả `null` từ method có kiểu `Optional`; dùng `Optional` làm field entity hay tham số.

Với field và tham số, cách hiện đại là annotation: [[jspecify|JSpecify]] 1.0 có `@NullMarked` (mặc định mọi kiểu trong phạm vi là không-null) và `@Nullable` cho chỗ ngoại lệ. Spring Framework 7 dùng JSpecify cho API của mình; NullAway hoặc IntelliJ kiểm lúc biên dịch, Kotlin đọc được để biết kiểu nào nullable.

Collection: `HashMap`, `ArrayList` nhận `null`; `List.of`, `Map.of` (Java 9), `ConcurrentHashMap`, và `TreeMap` dùng thứ tự tự nhiên với key `null` thì ném NPE. `Collectors.toMap` ném NPE nếu có value `null`.

Cách làm đúng: kiểm tra ở biên (request, dữ liệu từ DB, thư viện ngoài) bằng `Objects.requireNonNull` hay validation, bên trong coi mọi thứ là không-null theo mặc định.

## Deep

- **Đã chạy JDK 27**: `Optional.empty().get()` ném `NoSuchElementException: No value present`; `Stream.of("a", null).toList()` (Java 16) và `Collectors.toList()` chấp nhận `null`, còn `Collectors.toUnmodifiableList()`, `List.copyOf` và `List.of` thì không; `List.of("a").contains(null)` cũng ném NPE (Java 9+) vì list bất biến kiểu mới từ chối cả truy vấn `null`.
- **Helpful NPE và tên biến**: message ghi tên biến cục bộ và tham số chỉ khi class được biên dịch có thông tin biến (`javac -g`); không có thì ghi `"<local5>"`, kể cả khi `null` là mảng nằm trong biến cục bộ. `javac` mặc định không ghi tên biến (chạy `java File.java` ra `<local5>`), còn Maven và Gradle bật sẵn. Tên field và method thì luôn có. Tính năng chỉ chạy khi NPE do JVM ném, không áp dụng cho `throw new NullPointerException()` hay `Objects.requireNonNull`.
- **`Collectors.toMap` với value `null`**: ném NPE không có message rõ ràng vì bên trong gọi `Objects.requireNonNull` trên value (Java 9+; Java 8 cũng ném nhưng từ `HashMap.merge`). Lọc trước hoặc dùng `collect(HashMap::new, (m, u) -> m.put(...), Map::putAll)` nếu thật sự cần `null`.
- **`Optional` là [[value-based-class|value-based class]]**: không so bằng `==`, không `synchronized` trên nó, không dựa vào danh tính. Nó `final` và không `Serializable`, nên không làm field của class cần serialize.
- **Chi phí**: mỗi `Optional` khác rỗng là một object; với vòng lặp nóng trả kiểu primitive thì `OptionalInt`, `OptionalLong` tránh boxing, hoặc trả giá trị đặc biệt có ghi tài liệu. Escape analysis của JIT thường khử được `Optional` sống ngắn, nhưng không đảm bảo.
- **Chuỗi `map`**: `user.map(User::address).map(Address::city).orElse("Không rõ")` thay cho ba tầng `if`. `map` tự gói kết quả `null` thành rỗng; hàm trả về `Optional` thì dùng `flatMap` để khỏi thành `Optional<Optional<T>>`.
- **Spring Data**: `findById` trả `Optional<T>`; query method tự khai báo trả `Optional<T>` thì nhận `Optional.empty()`, trả `T` thì nhận `null` khi không thấy. Muốn ném lỗi thì gọi `orElseThrow` ở nơi dùng. `Optional` làm tham số method `@RequestParam` thì Spring hỗ trợ, đó là ngoại lệ có chủ đích của framework.
- **`switch` và `null`**: `switch` kiểu cũ trên `null` ném NPE; từ Java 21 viết được `case null ->` trong `switch` pattern.
- **JSON**: Jackson phân biệt "trường vắng" và "trường `null`" chỉ khi bạn cấu hình (ví dụ `JsonNullable` hay `@JsonSetter(nulls = ...)`); PATCH dựa trên khác biệt này xem bài Thiết kế REST API. `Optional` làm field DTO cần module `Jdk8Module` ở Jackson 2; chi tiết ở bài JSON & Jackson.
- **`NULL` trong SQL** là chuyện khác: so sánh với `NULL` ra UNKNOWN, xem bài SQL cơ bản. Đừng ánh xạ cột nullable sang primitive `int` trong entity, vì Hibernate không gán được `null` cho primitive (`PropertyAccessException`).
- **Helper của `Objects`**: `requireNonNull(x, "message")` kiểm ở constructor để lỗi xảy ra sớm, `requireNonNullElse(x, mặcĐịnh)` (Java 9) thay cho `x != null ? x : mặcĐịnh`.
- **Null Object pattern**: trả một object "không làm gì" (`NoDiscount`) thay vì `null` khi hành vi mặc định có nghĩa nghiệp vụ; hợp hơn `Optional` khi bên gọi luôn gọi method trên kết quả.
