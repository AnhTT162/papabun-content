## Quick

Behavioral pattern phân chia **ai làm gì và ai gọi ai**. Năm pattern dùng nhiều nhất trong Java/Spring: [[strategy-pattern|Strategy]] (thay thuật toán lúc chạy), [[template-method|Template Method]] (khung cố định, bước thay đổi), [[observer-pattern|Observer]] (báo cho nhiều bên khi có sự kiện), [[chain-of-responsibility|Chain of Responsibility]] (request đi qua chuỗi xử lý) và [[state-pattern|State]] (hành vi đổi theo trạng thái). **Trong Java hiện đại, nhiều pattern chỉ còn là một lambda hay một `Map` được inject.**

## Interview

**Strategy**: một interface, nhiều cài đặt, chọn lúc chạy. Spring inject `List<PaymentGateway>` rồi dựng `EnumMap<PaymentMethod, PaymentGateway>` từ `gateway.method()` của từng cài đặt. Thêm cổng là thêm một bean. Strategy chỉ một method thì một lambda (`Comparator`, `Function`) là đủ.

**Template Method**: lớp cha cố định thứ tự các bước, lớp con cài các bước thay đổi. Ví dụ `AbstractReportExporter.export()` gọi `header()`, `rows()`, `footer()`. Nhược điểm là kế thừa, nên Spring thường làm "template + callback" thay vì lớp con: `JdbcTemplate.query(sql, rowMapper)` (cũng như `TransactionTemplate`, `JdbcClient`) giữ phần cố định (lấy connection, xử lý exception, đóng resource), phần thay đổi là lambda `RowMapper`.

**Observer**: bên phát không biết ai nghe. Trong Spring là `ApplicationEventPublisher` với `@EventListener`. Bẫy cần nói được khi phỏng vấn: **mặc định đồng bộ, cùng thread và cùng transaction** với bên phát. Listener gửi email ném exception là đơn hàng rollback. Dùng [[transactional-event-listener|`@TransactionalEventListener`]] (`AFTER_COMMIT`) để chỉ chạy khi đã commit, thêm `@Async` nếu không muốn chặn, và [[outbox]] nếu không được mất sự kiện.

**Chain of Responsibility**: mỗi mắt xích xử lý rồi quyết định có chuyển tiếp hay không. [[servlet-filter|Servlet filter]] và Spring Security filter chain là ví dụ: quên gọi `chain.doFilter` là request dừng ở đó với response rỗng. [[handler-interceptor|`HandlerInterceptor.preHandle`]] trả `false` cũng chặn chuỗi.

**State**: đơn hàng `PENDING → PAID → SHIPPED`, cùng method `cancel()` nhưng hành vi khác nhau theo trạng thái. Với vài trạng thái, `enum` kèm bảng chuyển trạng thái hợp lệ là đủ; State pattern (mỗi trạng thái một class) hợp khi mỗi trạng thái có nhiều hành vi riêng.

**Bẫy chung**: dùng pattern để "trông có thiết kế". Một `switch` ba nhánh không bao giờ thêm nhánh mới không cần Strategy.

## Deep

- **Strategy theo tên bean là mong manh**: `Map<String, PaymentGateway>` có key là tên bean, sinh từ tên class (`ZaloPayGateway` thành `zaloPayGateway`). Ghép key từ dữ liệu (`method.toLowerCase() + "Gateway"`) hỏng khi đổi tên class. Quy tắc đặt tên còn có ngoại lệ: Spring 6 dùng `StringUtils.uncapitalizeAsProperty` (cùng quy tắc với `Introspector.decapitalize` mà Spring 5 dùng), nên class bắt đầu bằng hai chữ hoa như `VNPayGateway` giữ nguyên tên `VNPayGateway`. Bean khai báo bằng `@Bean` lấy tên method. Để cài đặt tự khai báo key, dựng map trong constructor và fail fast khi trùng hay thiếu.
- **Strategy bằng enum**: `enum ShippingFee { STANDARD { Money fee(Order o) {...} }, EXPRESS {...} }` gọn khi tập cài đặt cố định và không cần dependency. Cần inject bean (client HTTP, repository) thì dùng bean.
- **Event đồng bộ và thứ tự**: listener chạy tuần tự theo `@Order`, exception của một listener làm các listener sau không chạy và bay về bên phát. `@TransactionalEventListener` không chạy nếu không có transaction đang hoạt động, trừ khi đặt `fallbackExecution = true`. Listener `AFTER_COMMIT` muốn ghi database thì cần transaction mới (`REQUIRES_NEW`), vì transaction cũ đã commit; từ Spring 6.1, listener có `@Transactional` với propagation khác `REQUIRES_NEW` hay `NOT_SUPPORTED` làm ứng dụng không khởi động. Exception ném ra từ listener `AFTER_COMMIT` chỉ được ghi log (Spring gọi nó trong `afterCompletion`), nên bên phát không biết email đã mất: lý do thật để dùng outbox.
- **Observer giữa các service**: trong một JVM là event của Spring; giữa các service là Kafka hay RabbitMQ. Khi đó cần thêm idempotency, thứ tự và schema (bài Messaging fundamentals).
- **Chain of Responsibility và thứ tự**: thứ tự filter quyết định ngữ nghĩa: filter log đặt trước Spring Security thì log cả request bị từ chối; filter log body bọc request bằng `ContentCachingRequestWrapper` và chỉ đọc nội dung đã cache **sau** `chain.doFilter`, vì wrapper chỉ cache phần body mà các bước phía sau đã đọc. Đặt thứ tự bằng `@Order` hoặc `FilterRegistrationBean.setOrder`, không dựa vào thứ tự scan.
- **State và tính nhất quán**: chuyển trạng thái phải kiểm tra trạng thái hiện tại trong cùng transaction với lần ghi (`update orders set status = 'PAID' where id = ? and status = 'PENDING'`, hoặc [[optimistic-locking|optimistic locking]]), nếu không hai request đồng thời đều chuyển được. Bảng chuyển trạng thái nên nằm trong entity (`order.pay()`), không rải trong service.
- **[[command-pattern|Command]]**: đóng gói một yêu cầu thành object để xếp hàng, ghi log, thử lại hay huỷ. `Runnable` và `Callable` gửi vào `ExecutorService` là dạng đơn giản nhất; hàng đợi job và lệnh trong CQRS là dạng phân tán.
- **[[visitor-pattern|Visitor]]**: thêm thao tác cho một cây kiểu cố định mà không sửa các class đó, ví dụ `FileVisitor` của `Files.walkFileTree` hay visitor trên AST của trình biên dịch. Từ Java 21, `sealed` + `switch` pattern matching thường thay được Visitor với ít code hơn (bài SOLID).
- **Iterator và Mediator**: Iterator có sẵn trong `Iterable`/`Stream`. Mediator gom giao tiếp của nhiều object vào một điểm; `DispatcherServlet` điều phối handler, view resolver, exception resolver là một ví dụ (thường được gọi theo tên cụ thể hơn là Front Controller).
