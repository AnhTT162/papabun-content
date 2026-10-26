## Quick

Khi gọi một dependency có thể chậm hay lỗi, các lớp bảo vệ xếp chồng lên nhau. **[[timeout|Timeout]]** giới hạn thời gian chờ. **[[retry-backoff|Retry]]** cho lỗi tạm thời, chỉ với thao tác idempotent, có backoff tăng dần cộng [[jitter|jitter]] và giới hạn tổng. **[[circuit-breaker|Circuit breaker]]** ngừng gọi dependency đang hỏng để fail fast và cho nó thời gian hồi phục. **[[bulkhead|Bulkhead]]** tách tài nguyên theo từng dependency để một chỗ chậm không kéo sập cả service. **[[fallback|Fallback]]** trả kết quả xuống cấp thay vì lỗi. Phía bị gọi thì **[[load-shedding|load shedding]]** từ chối sớm khi quá tải, và [[backpressure|backpressure]] báo bên gửi chậm lại.

## Interview

**Retry đúng cách**:
- Chỉ retry lỗi tạm thời (timeout, `503`, mất kết nối), không retry `400`, `404`, lỗi nghiệp vụ.
- Exponential backoff cộng jitter: chờ ngẫu nhiên trong khoảng `[0, min(cap, base × 2^n)]` (full jitter). Không có jitter, mọi client retry cùng nhịp và tạo các đợt tải dồn vào dependency vừa hồi phục.
- Giới hạn: số lần thử, deadline tổng, và [[retry-budget|retry budget]] (retry không quá khoảng 10% số request), để retry không nhân tải khi dependency đã quá tải.
- Chỉ retry ở **một tầng**: 3 tầng, mỗi tầng thử 3 lần, là tới 27 lời gọi cho một request.

**Circuit breaker** (Resilience4j): `CLOSED` đếm tỉ lệ lỗi và tỉ lệ gọi chậm trong một cửa sổ trượt (theo số lời gọi hoặc theo thời gian); tỉ lệ lỗi chạm `failureRateThreshold` (mặc định 50%) hoặc tỉ lệ gọi chậm chạm `slowCallRateThreshold` thì `OPEN`, trả lỗi ngay mà không gọi; sau `waitDurationInOpenState` (mặc định 60 giây) sang `HALF_OPEN`, cho một số lời gọi thử (mặc định 10) để quyết định đóng lại hay mở tiếp. Lời gọi chậm cũng được tính, vì dependency treo nguy hiểm hơn dependency trả lỗi nhanh; nhưng mặc định `slowCallDurationThreshold` là 60 giây và `slowCallRateThreshold` là 100%, nên phải tự đặt thì mới có tác dụng.

**Bulkhead**: semaphore giới hạn số lời gọi đồng thời tới một dependency, hoặc thread pool riêng cho nó. Payment chậm chỉ làm đầy phần của Payment, Catalog vẫn chạy.

**Thứ tự lớp bọc**: Resilience4j mặc định là `Retry(CircuitBreaker(RateLimiter(TimeLimiter(Bulkhead(call)))))`: mỗi lần retry đi qua breaker, nên khi breaker mở thì lần thử bị từ chối ngay bằng `CallNotPermittedException` mà không chạm dependency. Nhưng Retry mặc định retry mọi exception, nên vẫn chờ đủ các lượt backoff; muốn dừng hẳn, đưa `CallNotPermittedException` vào `ignoreExceptions` hoặc chỉ khai báo `retryExceptions` cụ thể.

## Deep

- **Ngưỡng tối thiểu của breaker**: `minimumNumberOfCalls` (mặc định 100) là số lời gọi tối thiểu trước khi tính tỉ lệ lỗi. Dependency chỉ được gọi vài lần mỗi phút thì breaker mở rất muộn hoặc không bao giờ mở; đặt theo lưu lượng thật, hoặc dùng cửa sổ theo thời gian.
- **Breaker nằm trong từng JVM**: 20 pod có 20 breaker độc lập, mỗi cái phải tự thấy đủ lỗi mới mở. Đây là thiết kế đúng (mỗi pod có góc nhìn mạng riêng), nhưng nghĩa là dependency vẫn nhận một lượng lời gọi thử từ mỗi pod.
- **TimeLimiter không dừng được code đang chặn**: `TimeLimiter` của Resilience4j bọc `CompletableFuture`; hết giờ thì bên gọi nhận lỗi, nhưng thread đang chạy lời gọi JDBC hay HTTP blocking vẫn tiếp tục cho tới khi socket timeout. `cancelRunningFuture` (mặc định `true`) gọi `cancel` trên future, nhưng `CompletableFuture.cancel` không interrupt thread. Với Spring Boot, `@TimeLimiter` chỉ áp cho method trả `CompletionStage` hay kiểu reactive. Timeout thật phải đặt ở client bên dưới (HTTP client, JDBC `socketTimeout`).
- **Fallback có thể tệ hơn lỗi**: fallback gọi sang một dependency khác dưới cùng tải có thể làm sập cả nó; fallback trả "giá 0" hay "còn hàng" mặc định có thể gây sai nghiệp vụ. Fallback tốt: dữ liệu cache cũ có đánh dấu, ẩn tính năng phụ, hay báo lỗi rõ ràng. Luôn có metric cho số lần dùng fallback.
- **Load shedding ở phía server**: khi hàng đợi hoặc số request đang xử lý vượt ngưỡng, trả `503` ngay (kèm `Retry-After`) thay vì nhận thêm rồi xử lý tất cả chậm. Ưu tiên giữ request quan trọng (thanh toán hơn gợi ý sản phẩm), và bỏ request đã quá deadline vì client đã bỏ đi. Giới hạn đồng thời thích nghi (adaptive concurrency limit) tự điều chỉnh ngưỡng theo latency đo được.
- **Backpressure**: hàng đợi có giới hạn, Reactive Streams `request(n)`, Kafka consumer tự kéo theo tốc độ xử lý. Hàng đợi không giới hạn chỉ dời lỗi từ "từ chối" sang "hết bộ nhớ" (bài Reactive).
- **Spring Framework 7**: có sẵn `@Retryable` (backoff, jitter) và `@ConcurrencyLimit` trong `org.springframework.resilience.annotation`, bật bằng `@EnableResilientMethods`. `@Retryable` mặc định retry mọi exception (3 lần, chờ 1 giây), nên cần giới hạn `includes`; `@ConcurrencyLimit` chặn chờ khi hết chỗ, khác bulkhead của Resilience4j vốn từ chối ngay. Resilience4j vẫn cần cho circuit breaker và metric chi tiết.
- **OPEN không tự chuyển sang HALF_OPEN** theo mặc định (`automaticTransitionFromOpenToHalfOpenEnabled = false`): phải có một lời gọi tới sau khi hết thời gian chờ thì breaker mới chuyển.
- **Retry và idempotency đi cùng nhau**: retry thao tác ghi mà không có idempotency key là đổi lỗi tạm thời lấy dữ liệu trùng (bài Idempotency).
- **Kiểm thử bằng cách gây lỗi thật**: Toxiproxy hay fault injection của service mesh thêm latency, cắt kết nối, trả lỗi, để kiểm tra breaker mở đúng lúc, timeout đúng giá trị, và dashboard thấy được. Cấu hình chưa từng được kiểm tra dưới lỗi thường sai.
