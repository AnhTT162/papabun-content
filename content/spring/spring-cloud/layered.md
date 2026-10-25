## Quick

Spring Cloud là bộ thư viện lắp các mẫu của microservices vào Spring Boot: [[api-gateway|gateway]] (Spring Cloud Gateway), [[service-discovery|service discovery]] (Eureka, Consul), cấu hình tập trung ([[config-server|Config Server]]), [[client-side-load-balancing|load balancing phía client]] (Spring Cloud LoadBalancer), [[circuit-breaker|circuit breaker]] (Resilience4j), HTTP client khai báo (OpenFeign). **Trên Kubernetes, nhiều phần trong số đó nền tảng đã làm sẵn**: Service DNS thay cho discovery, ConfigMap và Secret thay cho Config Server. Chọn từng phần theo nhu cầu, không lấy cả bộ.

## Interview

**Các thành phần và vai trò**:
- **Gateway**: một cửa vào cho client bên ngoài; route theo đường dẫn, xác thực token, rate limit, gắn header. Có hai biến thể: WebFlux trên Netty và Web MVC chạy trên servlet.
- **Discovery**: service tự đăng ký vào Eureka; client hỏi danh sách instance rồi tự chọn một. Gateway route tới `lb://orders`; trong service dùng `@LoadBalanced RestClient.Builder` rồi gọi `http://orders`.
- **Config**: service lấy cấu hình từ Config Server (thường lưu trong Git) qua `spring.config.import=configserver:`; đổi cấu hình lúc chạy bằng `@RefreshScope` và `/actuator/refresh`.
- **Resilience4j**: circuit breaker, [[retry-backoff|retry]], bulkhead, time limiter quanh lời gọi ra ngoài (khái niệm ở bài Timeout, retry, circuit breaker, bulkhead).
- **OpenFeign**: interface có annotation thành HTTP client. Dự án đã tuyên bố "feature complete"; code mới nên dùng HTTP interface client của Spring (`@HttpExchange` trên `RestClient`).

**Những thứ đã bị bỏ** (Spring Cloud 2020.0): Netflix Zuul, Hystrix, Ribbon. Hệ thống cũ nâng Boot phải thay bằng Gateway, Resilience4j và Spring Cloud LoadBalancer.

**Khi nào không cần**:
- Trên Kubernetes, gọi `http://orders` qua Service DNS, kube-proxy chia tải, readiness probe loại pod chưa sẵn sàng. Thêm Eureka là hai nguồn sự thật về "instance nào sống".
- Có service mesh (Istio, Linkerd) thì retry, timeout, mTLS nằm ở sidecar; đặt thêm ở ứng dụng dễ thành retry chồng retry.
- Vài service nội bộ thì một reverse proxy hay Ingress là đủ, chưa cần gateway viết bằng Java (trách nhiệm của gateway, BFF và mesh: bài API gateway, BFF & service mesh).

**Câu trả lời tốt khi phỏng vấn**: nói rõ hệ thống chạy ở đâu (VM hay Kubernetes), cái gì nền tảng đã lo, và mỗi thư viện Spring Cloud thêm vào giải quyết vấn đề gì còn thiếu.

## Deep

- **Phiên bản**: Spring Cloud đặt tên theo năm và đi theo Boot: 2025.0 cho Boot 3.5, 2025.1 cho Boot 4. Lệch cặp phiên bản thường lỗi ngay lúc khởi động (`spring.cloud.compatibility-verifier`). Quản lý bằng BOM `spring-cloud-dependencies`.
- **Gateway**:
  - Từ 2025.0, artifact đổi tên thành `spring-cloud-starter-gateway-server-webflux` và `-server-webmvc`; tên cũ bị deprecated. Prefix property cũng đổi sang `spring.cloud.gateway.server.webflux.*` (hoặc `.server.webmvc.*`), và header `X-Forwarded-*` không còn được tin mặc định: phải khai báo `trusted-proxies`, nếu không link redirect và IP client bị sai sau khi nâng cấp.
  - Bản WebFlux chạy trên event loop của Netty: filter tự viết mà gọi code blocking (JDBC, `RestTemplate`) sẽ chặn event loop và làm treo mọi route (bài Spring WebFlux & Netty).
  - Đặt timeout cho từng route; mặc định không có response timeout nên backend treo là request treo.
  - Gateway có thể chuyển access token xuống service sau (token relay), nhưng mỗi service vẫn phải tự kiểm tra token.
- **Discovery và độ trễ khi instance chết**:
  - Eureka client gia hạn lease mỗi 30 giây. Server coi lease hết hạn sau 90 giây theo cấu hình, nhưng do một lỗi đã biết trong `Lease.renew()` thực tế là khoảng 180 giây, cộng chu kỳ evict 60 giây và response cache 30 giây của server.
  - Client tải lại danh sách instance mỗi 30 giây, và Spring Cloud LoadBalancer còn cache thêm (mặc định 35 giây). Với Eureka nên tắt cache này (`spring.cloud.loadbalancer.cache.enabled=false`) vì client Eureka đã cache, tránh cache chồng cache.
  - Một instance chết đột ngột có thể vẫn nhận request trong vài phút. Cần graceful shutdown (tự huỷ đăng ký trước khi dừng), retry cho request idempotent, và giảm TTL cache nếu cần.
  - Eureka server có self-preservation: khi mất nhiều lease cùng lúc, nó ngừng xoá instance để không xoá nhầm khi chính mạng có vấn đề.
- **Config**:
  - `spring.config.import=configserver:` không có tiền tố `optional:` thì ứng dụng không khởi động được khi Config Server không truy cập được. Có `optional:` thì ứng dụng chạy với cấu hình cục bộ, dễ âm thầm chạy sai.
  - `@RefreshScope` tạo lại bean ở lần gọi tiếp theo sau refresh; bean `@ConfigurationProperties` được bind lại. Không phải mọi thứ đổi được lúc chạy: pool connection, thread pool, cổng server cần khởi động lại.
  - Không dùng Config Server thì đổi cấu hình bằng [[rolling-deployment|rolling restart]].
  - Refresh gọi vào từng instance; Spring Cloud Bus (qua Kafka hoặc RabbitMQ) phát sự kiện refresh cho tất cả.
  - Secret không nên nằm trong Git của Config Server dạng rõ; dùng Vault backend hoặc mã hoá `{cipher}`.
- **Resilience4j**:
  - Thứ tự mặc định khi dùng annotation: `Retry` bọc ngoài `CircuitBreaker`, rồi `RateLimiter`, `TimeLimiter`, `Bulkhead`. Mỗi lần retry đều được circuit breaker đếm.
  - `TimeLimiter` chỉ áp cho lời gọi bất đồng bộ (`CompletableFuture`); lời gọi đồng bộ cần timeout của chính HTTP client.
  - Đừng retry lỗi 4xx, và chỉ retry request idempotent.
- **OpenFeign**:
  - Timeout mặc định: kết nối 10 giây, đọc 60 giây, quá dài cho gọi nội bộ; đặt theo từng client.
  - Feign chạy đồng bộ, không hợp với WebFlux.
  - Framework 7 có `@ImportHttpServices` để đăng ký nhóm HTTP interface client, thay phần lớn việc của Feign mà không cần Spring Cloud.
- **Resilience có sẵn trong Framework 7**: `@Retryable` và `@ConcurrencyLimit` (bật bằng `@EnableResilientMethods`) đủ cho nhu cầu retry đơn giản; circuit breaker vẫn cần Resilience4j.
- **Spring Cloud Kubernetes**: đọc ConfigMap và Secret thành property source, và cung cấp discovery dựa trên API của Kubernetes. Nó cần quyền đọc API server (RBAC); nhiều đội chỉ mount ConfigMap thành file và dùng `spring.config.import=configtree:` cho đơn giản.
