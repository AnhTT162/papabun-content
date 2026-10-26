## Quick

Creational pattern giải quyết **ai tạo object và tạo thế nào** để bên dùng không phụ thuộc vào class cụ thể hay vào thứ tự tham số. Ba pattern hay dùng nhất trong Java: [[static-factory-method|static factory]] và các dạng factory (đặt tên và che cách tạo), [[builder-pattern|Builder]] (object nhiều tham số tuỳ chọn), và [[singleton-pattern|Singleton]]. **Singleton tự quản lý nên tránh**: trong Spring, dùng [[bean-scope|bean scope]] singleton do container quản lý.

## Interview

**Static factory method** (`of`, `from`, `valueOf`, `getInstance`) thay cho constructor public:
- Có tên nói rõ ý: `Money.ofVnd(50_000)` dễ đọc hơn `new Money(50_000, "VND", 0)`.
- Không bắt buộc tạo object mới: `Integer.valueOf(127)` trả object trong cache -128..127, `List.of()` trả cùng một list rỗng.
- Trả được kiểu con, kể cả class ẩn: `List.of(...)` trả một class nội bộ (`ImmutableCollections.List12` hay `ListN`, chi tiết cài đặt), bên gọi chỉ thấy `List`.

**Simple factory, Factory Method, Abstract Factory**: simple factory là một method chọn class theo tham số, như `NotificationSenderFactory.forChannel(channel)`. [[factory-method|Factory Method]] (GoF) dựa trên **kế thừa**: lớp cha `ReportExporter` có method `abstract Writer createWriter()` và dùng nó trong `export()`, lớp con `CsvExporter`, `ExcelExporter` override để quyết định tạo gì. [[abstract-factory|Abstract Factory]] dựa trên **composition**: một object factory được inject, tạo cả một **họ** object phải đi cùng nhau, ví dụ một `PaymentProviderFactory` tạo cùng lúc API client, bộ kiểm chữ ký và bộ đọc webhook của cùng một cổng thanh toán, để không ai ghép nhầm client của cổng này với bộ kiểm chữ ký của cổng kia. Trong Spring, phần lớn nhu cầu này được thay bằng inject `Map<String, Sender>` hoặc method `@Bean`.

**Builder** cho object nhiều tham số, nhất là tham số tuỳ chọn:
- Thay [[telescoping-constructor|telescoping constructor]] (5 constructor chồng tham số) và tránh truyền nhầm hai `int` cạnh nhau.
- Kiểm tra bất biến một lần trong `build()`, và object tạo ra có thể bất biến hoàn toàn.
- Bẫy: Lombok `@Builder` bỏ qua giá trị khởi tạo của field nếu thiếu `@Builder.Default`.

**Singleton**: một instance cho cả ứng dụng. Cách viết an toàn nhất là `enum` một phần tử, hoặc field `static final` ([[holder-idiom|holder idiom]] nếu cần khởi tạo lười). **Vì sao nên tránh**:
- Là trạng thái toàn cục: test sửa nó thì test khác chạy sau trong cùng JVM bị ảnh hưởng.
- Dependency bị ẩn: `ExchangeRates.getInstance()` nằm giữa method, không hiện ở constructor, khó thay bằng bản giả.
- "Một instance" thật ra là một instance **mỗi [[classloader]]**: app server hay hot reload có thể có hai.

Cách làm đúng: class bình thường, nhận dependency qua constructor, để container tạo đúng một bean.

## Deep

- **[[double-checked-locking|Double-checked locking]] cần `volatile`**: thiếu `volatile` thì thread khác có thể thấy tham chiếu khác `null` tới một object chưa khởi tạo xong, vì phép gán có thể được sắp xếp lại trước khi constructor chạy xong (bài `java-memory-model`). Holder idiom (`private static class Holder { static final X INSTANCE = new X(); }`) cho khởi tạo lười mà không cần khoá, vì JVM đảm bảo class được khởi tạo đúng một lần và an toàn giữa các thread.
- **Phá Singleton**: reflection gọi được constructor `private` (`setAccessible(true)`); deserialization tạo object mới nếu không có `readResolve`; `clone()` nếu class implement `Cloneable`. `enum` chặn cả ba: JVM cấm tạo enum bằng reflection, và serialization của enum chỉ lưu tên hằng.
- **Spring singleton khác GoF Singleton**: bean scope singleton là một object **mỗi `ApplicationContext`**. Test dùng hai context khác cấu hình sẽ có hai object. Bean vẫn là class bình thường: test được bằng `new`, thay được bằng mock. Lưu ý bean singleton dùng chung giữa mọi request, nên field có trạng thái thay đổi được là lỗi đồng thời.
- **Lombok `@Builder`**: `private int retries = 3;` mà thiếu `@Builder.Default` thì builder đặt `retries` là 0 (Lombok chỉ in cảnh báo lúc biên dịch). `@Builder` chỉ tự sinh constructor khi class chưa có constructor nào, nên thêm `@NoArgsConstructor` (cho JPA, Jackson) thì phải thêm cả `@AllArgsConstructor`. Với record (Lombok 1.18.20+), `@Builder` hoạt động nhưng không có `@Builder.Default`: dùng kiểu boxed (`Integer`) rồi thay `null` bằng giá trị mặc định trong compact constructor, vì với `int` không phân biệt được "không set" và "set 0".
- **Builder có giá**: thêm một class và dễ để quên field bắt buộc tới lúc chạy. Với 3–4 tham số bắt buộc, constructor hoặc static factory rõ hơn. Có thể đưa tham số bắt buộc vào `builder(requiredA, requiredB)` để compiler kiểm.
- **Builder trong JDK**: `HttpClient.newBuilder()`, `HttpRequest.newBuilder()`, `Stream.builder()`, `Locale.Builder`. `StringBuilder` chỉ giống builder ở tên: nó không kiểm bất biến rồi tạo ra một object khác qua `build()`. Các builder của `java.net.http` trả object bất biến.
- **Prototype và `clone()`**: [[prototype-pattern|Prototype]] tạo object bằng cách sao chép một mẫu. Trong Java, `Object.clone()` sao chép nông ([[shallow-copy|shallow copy]]), bỏ qua constructor và dễ sai với field `final` hay collection. Copy constructor hoặc static factory `copyOf` an toàn hơn; record thì đã bất biến nên thường không cần sao chép.
- **Factory và dependency injection**: container DI là một factory tổng quát. Viết factory riêng khi cần tạo object **lúc chạy** với tham số chỉ biết lúc đó (theo tenant, theo channel). `ObjectProvider<T>` hoặc `@Lookup` của Spring tạo bean prototype theo yêu cầu.
- **[[service-loader|`ServiceLoader`]]**: factory của JDK để nạp cài đặt từ classpath (`META-INF/services`). JDBC 4 dùng nó để tự tìm driver, nên không còn cần `Class.forName("...Driver")`.
