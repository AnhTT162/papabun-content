## Quick

Structural pattern ghép object lại với nhau. Bốn pattern hay gặp nhất có cấu trúc gần giống nhau (một object bọc object khác) nhưng **khác nhau ở ý định**: [[adapter-pattern|Adapter]] đổi interface cho khớp, [[decorator-pattern|Decorator]] thêm hành vi mà giữ nguyên interface, [[proxy-pattern|Proxy]] kiểm soát việc truy cập vào object thật, [[facade-pattern|Facade]] đưa ra một interface đơn giản cho cả một hệ con.

## Interview

**Adapter**: có sẵn một class nhưng interface không khớp với thứ code của bạn cần.
- JDK: `InputStreamReader` biến byte stream thành character reader; `Arrays.asList` cho mảng dùng được như `List`.
- Spring MVC: `HandlerAdapter` cho `DispatcherServlet` gọi được nhiều kiểu handler khác nhau.
- Thực tế: bọc SDK của cổng thanh toán vào interface `PaymentGateway` của bạn. Đổi nhà cung cấp hay nâng phiên bản SDK thì chỉ adapter phải sửa. Đây chính là phía cài đặt của [[dependency-inversion|Dependency Inversion]].

**Decorator**: cùng interface với object bên trong, thêm hành vi rồi chuyển tiếp lời gọi, và xếp chồng được.
- JDK: `new BufferedReader(new InputStreamReader(new GZIPInputStream(file)))`; `Collections.unmodifiableList`, `Collections.synchronizedList`.
- Thực tế: `CachingRateProvider`, `MetricsPaymentGateway`, `RetryingPaymentGateway` cùng bọc một `PaymentGateway`. Mỗi lớp một việc, thay cho việc tạo lớp con cho mọi tổ hợp (cache + metrics, cache + retry...).
- **Thứ tự xếp chồng là ngữ nghĩa**: metrics đặt ngoài retry đếm một lời gọi, đặt trong retry đếm mỗi lần thử.

**Proxy**: cùng interface, nhưng mục đích là kiểm soát: tạo lười, kiểm tra quyền, gọi từ xa, hay mở transaction quanh lời gọi. Spring tạo proxy cho `@Transactional`, `@Cacheable`, `@Async` ([[aop-proxy|AOP proxy]]); Hibernate dùng proxy cho [[lazy-loading|lazy loading]]. Bẫy lớn nhất là [[self-invocation|self-invocation]]: gọi `this.method()` đi thẳng vào object thật, bỏ qua proxy (bài AOP & proxy).

**Facade**: một điểm vào đơn giản che nhiều class phức tạp. `JdbcTemplate` che `Connection`, `PreparedStatement`, `ResultSet` và việc đóng resource; SLF4J là "Simple Logging Facade for Java". Bẫy: facade lớn dần thành "god class" mà module nào cũng phụ thuộc.

**Cách phân biệt khi bị hỏi**: hỏi object bọc đổi interface (Adapter), thêm việc (Decorator), quyết định có cho gọi hay gọi lúc nào (Proxy), hay gom nhiều thứ thành một lời gọi (Facade).

## Deep

- **Decorator của `Collections` là [[unmodifiable-view|view]], không phải bản sao**: `Collections.unmodifiableList(list)` chặn sửa **qua view**, nhưng list bên dưới đổi thì view thấy ngay, và đang duyệt view mà list bên dưới đổi thì gặp `ConcurrentModificationException`. Cần ảnh chụp bất biến thì dùng `List.copyOf` (Java 10). `Collections.synchronizedList` cũng chỉ đồng bộ từng method: duyệt vẫn phải tự `synchronized (list)`.
- **Decorator làm mất danh tính và kiểu cụ thể**: `list instanceof ArrayList` sai sau khi bọc; `equals` giữa object bọc và object thật có thể không đối xứng; object bên trong đăng ký callback bằng `this` thì callback bỏ qua lớp bọc. Proxy của Hibernate cũng vậy: `getClass()` trả lớp con proxy, nên `equals` so bằng `getClass()` cho kết quả sai.
- **Decorator viết tay và method `default`**: interface thêm method `default` mới thì decorator không override nó, nên lời gọi chạy cài đặt mặc định trên chính decorator và bỏ qua object bên trong mà không ai biết. Mỗi khi interface thêm method, rà lại mọi decorator (hoặc có test kiểm tra mọi method đều được chuyển tiếp).
- **Decorator với Spring**: bean `@Primary` bọc một bean khác cùng interface (inject bằng `@Qualifier`) là cách viết decorator tay. Khi hành vi áp cho nhiều bean (log, metrics, retry), AOP là decorator tổng quát. Spring còn có sẵn decorator như `ContentCachingRequestWrapper` (cache phần body đã được đọc để đọc lại sau khi request xử lý xong) và `TransactionAwareDataSourceProxy`.
- **Thứ tự retry và transaction**: retry phải nằm **ngoài** transaction, để mỗi lần thử là một transaction mới. Spring Retry (`@EnableRetry`) và `@Retryable` của Spring Framework 7 mặc định đã có thứ tự cao hơn advice `@Transactional` để đặt retry ở ngoài; chỉ cần chỉnh khi tự viết aspect hoặc đổi thuộc tính `order`. Bẫy hay gặp hơn: method `@Retryable` được gọi từ bên trong một transaction đang mở (`REQUIRED`), nên mọi lần thử vẫn chung transaction đó, và transaction đã bị đánh dấu rollback-only thì thử lại cũng vô ích.
- **[[jdk-dynamic-proxy|JDK dynamic proxy]] và CGLIB**: JDK proxy chỉ implement interface, nên inject theo class cụ thể thì lỗi `BeanNotOfRequiredTypeException`. Spring Boot 2.0+ mặc định dùng [[cglib|CGLIB]] (`spring.aop.proxy-target-class=true`), tạo lớp con: class `final` làm khởi động lỗi, còn method `final` thì không bị proxy và chạy thẳng trên instance proxy, nơi các field được inject đều `null`, nên thường thấy `NullPointerException` thay vì một thông báo rõ ràng. Spring 7 có `@Proxyable` để chọn kiểu proxy cho từng bean.
- **Adapter hai chiều và anti-corruption layer**: khi tích hợp với hệ thống cũ có mô hình dữ liệu khác hẳn, adapter dịch cả request lẫn response và lỗi (mã lỗi của đối tác thành exception của bạn), để mô hình bên ngoài không tràn vào nghiệp vụ. DDD gọi tầng này là [[anti-corruption-layer|anti-corruption layer]] (bài DDD chiến lược).
- **[[composite-pattern|Composite]]**: cây object mà nút lá và nút nhánh có cùng interface, nên bên gọi xử lý như nhau. Ví dụ: `CompositeCacheManager` của Spring, `CompositeMeterRegistry` của Micrometer gửi metric tới nhiều nơi.
- **[[bridge-pattern|Bridge]]**: tách abstraction khỏi cài đặt để hai bên thay đổi độc lập. JDBC là ví dụ quen thuộc: code của bạn dùng `Connection`, `Statement` của `java.sql`, còn driver PostgreSQL hay MySQL cài đặt chúng.
- **[[flyweight-pattern|Flyweight]]**: dùng chung object bất biến thay vì tạo mới, như `Integer.valueOf` trong khoảng -128..127 hay `String` literal trong string pool. Chỉ đúng khi object thật sự bất biến.
