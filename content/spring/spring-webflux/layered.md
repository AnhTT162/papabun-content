## Quick

Spring WebFlux chạy trên Netty với **[[event-loop|event loop]]**: vài thread (mặc định bằng số core, tối thiểu 4) phục vụ hàng nghìn kết nối, vì không thread nào ngồi chờ I/O. Code trả về `Mono`/`Flux` ([[reactive-streams|Reactive Streams]]) mô tả các bước sẽ chạy khi có dữ liệu. **Quy tắc sống còn: không bao giờ chặn (block) event loop.** Một lời gọi JDBC, `RestTemplate` hay `Thread.sleep` trên event loop làm đứng mọi request khác đang dùng thread đó. Từ khi có [[virtual-thread|virtual thread]], phần lớn ứng dụng CRUD nên ở lại Spring MVC.

## Interview

**Cách chạy**:
- Netty nhận kết nối trên event loop. Controller trả `Mono<Order>`; WebFlux subscribe, và mỗi bước chạy trên thread đang có sự kiện (thường là event loop).
- Gọi ra ngoài bằng `WebClient` hay driver R2DBC: gửi yêu cầu rồi trả thread ngay; khi có phản hồi, callback tiếp tục pipeline.
- **Không có gì chạy cho tới khi có subscribe**: tạo `Mono` mà không trả về hay subscribe thì lời gọi không bao giờ xảy ra.

**Block trong reactive**:
- Dấu hiệu: CPU thấp mà latency tăng vọt, health check timeout, thread dump thấy `reactor-http-nio-*` (trên Linux là `reactor-http-epoll-*`) nằm trong `socketRead` hay `Thread.sleep`.
- `block()` gọi trên event loop ném `IllegalStateException` (`block()/blockFirst()/blockLast() are blocking...`), nhưng JDBC hay `RestTemplate` thì không ai báo.
- Phát hiện sớm bằng [[blockhound|BlockHound]] trong test: nó ném lỗi khi có lời gọi blocking trên thread non-blocking (JDK 13+ cần cờ `-XX:+AllowRedefinitionToAddDeleteMethods`).
- Bắt buộc phải gọi thư viện blocking thì đẩy sang `Schedulers.boundedElastic()` bằng `subscribeOn`/`publishOn`.

**[[backpressure|Backpressure]]** (subscriber chỉ nhận số phần tử nó yêu cầu) chỉ có tác dụng khi cả chuỗi từ database tới client đều reactive (khái niệm ở bài Reactive programming & Project Reactor).

**Khi nào chọn WebFlux**:
- Nên: gateway hoặc proxy (rất nhiều kết nối, ít xử lý), streaming (SSE, WebSocket), service gọi song song nhiều downstream và ghép kết quả.
- Không nên: CRUD trên JDBC/JPA, đội chưa quen reactive. Spring MVC với virtual thread (`spring.threads.virtual.enabled=true`) cho mô hình lập trình tuần tự quen thuộc mà vẫn chịu được nhiều request chờ I/O.

## Deep

- **Số thread**: Reactor Netty dùng `max(số core, 4)` thread event loop. Pod giới hạn 2 CPU vẫn có 4 thread; một lời gọi blocking 200ms giữ một phần tư năng lực phục vụ trong 200ms đó.
- **`boundedElastic`**: tối đa 10 × số core thread, mỗi thread có hàng đợi 100.000 task. Không phải chỗ để đẩy mọi thứ vào; nếu phần lớn công việc là blocking thì Spring MVC đơn giản hơn.
- **Không có [[thread-local|`ThreadLocal`]]**: một request đi qua nhiều thread, nên MDC, trace id, `SecurityContextHolder` và `@Transactional` kiểu servlet không dùng được trực tiếp.
  - Dữ liệu theo request nằm trong Reactor `Context`.
  - Thư viện context-propagation, bật bằng `spring.reactor.context-propagation=auto` (Boot 3.2+) hoặc `Hooks.enableAutomaticContextPropagation()`, chép giá trị giữa `Context` và `ThreadLocal` để log có trace id.
  - Security dùng `ReactiveSecurityContextHolder`.
  - Transaction dùng `ReactiveTransactionManager` (R2DBC); `@Transactional` trên method trả `Mono`/`Flux` vẫn chạy nếu có transaction manager reactive.
- **R2DBC**: driver reactive cho PostgreSQL, MySQL, SQL Server, Oracle. Không có JPA, lazy loading hay persistence context; Spring Data R2DBC chỉ ánh xạ bảng đơn giản. Pool là `r2dbc-pool`, cấu hình riêng với HikariCP.
- **`WebClient`**:
  - Đặt `responseTimeout` trên `HttpClient` của Reactor Netty và `.timeout(...)` trên `Mono`; mặc định không có response timeout.
  - Pool mặc định (WebClient của Spring và Boot, `HttpClient.create()`) cho tối đa 500 kết nối mỗi host và 1.000 yêu cầu chờ; vượt quá thì `PoolAcquirePendingLimitException`, chờ quá 45 giây thì `PoolAcquireTimeoutException`. Tự tạo `ConnectionProvider` mà không đặt `maxConnections` thì mặc định là `max(2 × số core, 16)`. Nên tự đặt giới hạn theo năng lực của downstream.
  - Body phải được đọc hoặc giải phóng. `retrieve()` và `exchangeToMono` đều tự giải phóng body khi xong; rò kết nối thường đến từ `exchange()` cũ (deprecated từ Spring 5.3) hoặc giữ `ClientResponse` mà không đọc body.
  - Trong ứng dụng Spring MVC, `RestClient` (Spring 6.1+) là lựa chọn đồng bộ mới; `WebClient` vẫn dùng được nhưng kéo theo Reactor.
- **Lỗi và debug**:
  - Stack trace reactive ít thông tin vì code chạy qua nhiều callback. `checkpoint("tên")` thêm mốc; `Hooks.onOperatorDebug()` tốn kém, chỉ dùng khi debug; `ReactorDebugAgent` (reactor-tools) rẻ hơn.
  - `onErrorResume` nuốt lỗi quá rộng là nguồn bug khó thấy; bắt đúng loại exception.
- **Song song xuống downstream**: `flatMap` mặc định subscribe tới 256 nguồn cùng lúc (`reactor.bufferSize.small`), và pool 500 kết nối không chặn được mức đó; với danh sách lớn đặt `flatMap(fn, 16)`. Operator và scheduler chi tiết ở bài Reactive programming & Project Reactor.
- **Một ứng dụng, hai stack**: có cả `spring-boot-starter-web` và `-webflux` thì Boot chọn Spring MVC. Thêm WebFlux chỉ để dùng `WebClient` không biến ứng dụng thành reactive.
- **Virtual thread và reactive**: virtual thread giải bài toán "nhiều request chờ I/O" với code tuần tự. Reactive vẫn có lợi ở streaming, backpressure và ghép nhiều luồng dữ liệu. Hai mô hình không nên trộn trong cùng một luồng xử lý (bài Reactive programming & Project Reactor).
