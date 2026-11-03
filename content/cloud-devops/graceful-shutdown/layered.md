## Quick

Tắt êm là chuỗi: **ngừng nhận việc mới, làm xong việc đang dở, đóng tài nguyên, thoát**, tất cả trong thời gian nền tảng cho phép trước khi [[sigkill|SIGKILL]]. Trên Kubernetes việc gỡ pod khỏi load balancer diễn ra **song song** với [[sigterm|SIGTERM]], nên cần [[prestop-hook|`preStop`]] chờ vài giây; và mọi thứ chỉ nằm trong bộ nhớ (hàng đợi `@Async`, batch chưa commit) sẽ mất khi quá hạn, nên việc quan trọng phải nằm ở nơi bền.

## Interview

Khi Kubernetes xoá một pod (deploy, scale xuống, node bị rút), hai việc xảy ra cùng lúc. Một, control plane đánh dấu endpoint của pod là đang kết thúc, kube-proxy, Ingress, load balancer của cloud lần lượt ngừng gửi traffic tới, mỗi nơi trễ một chút. Hai, kubelet chạy `preStop` rồi gửi SIGTERM cho PID 1 của container. [[termination-grace-period|Grace period]] mặc định 30 giây được tính từ đầu, gồm cả `preStop`; hết hạn thì SIGKILL.

Spring Boot từ 3.4 bật graceful shutdown mặc định: với Tomcat (đã đo), nhận SIGTERM là đóng cổng nghe ngay (kết nối mới bị từ chối), chờ request đang chạy xong, tối đa `spring.lifecycle.timeout-per-shutdown-phase` 30 giây mỗi pha. Vấn đề là load balancer có thể vẫn gửi request mới tới pod trong vài giây đầu, nên client nhận lỗi kết nối ([[connection-draining|connection draining]] ở load balancer chưa xong). Vì vậy tôi thêm `preStop` ngủ khoảng 10 giây: pod vẫn phục vụ bình thường trong lúc mọi nơi cập nhật, rồi mới nhận SIGTERM.

Spring dừng các thành phần theo phase của `SmartLifecycle`, phase cao dừng trước: Kafka listener container dừng trước cả web server, rồi web server xả request, rồi executor của `@Async` và scheduler; cuối cùng huỷ bean, đóng connection pool. Mỗi phase có hạn riêng. Tôi tính ngân sách: `terminationGracePeriodSeconds` lớn hơn `preStop` cộng tổng thời gian xả của các phase thực sự có việc cộng đóng tài nguyên, ví dụ 10 + 30 + 5 thì đặt 50–60 giây. Với ALB trỏ thẳng vào IP pod, `preStop` phải đủ dài cho ALB gỡ target, và hạ deregistration delay từ 300 giây xuống mức app cần.

Nhưng tắt êm chỉ là tối ưu cho trường hợp tốt. Pod vẫn có thể chết bằng SIGKILL, OOMKilled hay mất node. Thiết kế phải chịu được: việc quan trọng nằm trong queue bền hay bảng outbox, consumer idempotent, message chỉ được ack sau khi xử lý xong.

Bẫy hay gặp: script entrypoint không `exec` (JVM không phải [[pid-1|PID 1]]) nên JVM không nhận SIGTERM; job nền xếp hàng trong bộ nhớ bị bỏ khi quá 30 giây; grace period 30 giây nhỏ hơn tổng các khoảng chờ.

## Deep

- **Tín hiệu và JVM**: SIGTERM (15) và SIGINT chạy các shutdown hook đã đăng ký (`Runtime.addShutdownHook`), Spring đăng ký một hook để đóng context. Các hook chạy song song, không có thứ tự; đừng gọi `System.exit` trong hook (treo vì chờ chính nó). SIGKILL (9), `Runtime.halt` và crash của JVM thì không chạy hook nào. Exit code 143 là tự thoát sau SIGTERM, 137 là bị SIGKILL. JVM có nhận được tín hiệu hay không phụ thuộc PID 1 (bài Docker & container).
- **Đã đo với Spring Boot 4.1.2, JDK 27** (endpoint ngủ 8 giây, gửi SIGTERM ở giây thứ nhất):
  - Mặc định: log `Commencing graceful shutdown. Waiting for active requests to complete`, request dở trả 200 sau 8,0 giây, request mới ngay sau SIGTERM bị từ chối kết nối (curl mã 7), `@PreDestroy` chạy sau `Graceful shutdown complete`, process thoát mã 143.
  - `timeout-per-shutdown-phase=3s`: log `Shutdown phase 2147482623 ends with 1 bean still running after timeout of 3000ms: [webServerGracefulShutdown]`, request dở bị cắt sau khoảng 4 giây, client nhận phản hồi rỗng (curl mã 52).
  - `server.shutdown=immediate`: request dở bị cắt ngay.
- **Thứ tự dừng trong Spring** (đã ghi log trên Boot 4.1.2): readiness chuyển sang `REFUSING_TRAFFIC` ngay trước `ContextClosedEvent`, rồi các `SmartLifecycle` dừng từ phase cao xuống thấp: Kafka listener container (`Integer.MAX_VALUE - 100`) dừng trước, nên request HTTP đang xả không còn consumer chạy (producer vẫn gửi được); web server graceful (phase `Integer.MAX_VALUE - 1024`), executor và scheduler của Spring (phase `Integer.MAX_VALUE / 2`), rồi bean thường bị huỷ (`@PreDestroy`, `close()` của HikariCP). Mỗi phase có hạn riêng là `timeout-per-shutdown-phase`, nên tổng thời gian có thể gấp vài lần 30 giây. Thứ tự phase ở bài Bean lifecycle & scope.
- **`@Async` và executor** (đã đo, pool 2 thread, mỗi việc 2 giây):
  - 6 việc trong hàng đợi lúc SIGTERM: Boot 4 chờ chạy hết rồi mới huỷ bean.
  - 40 việc: chạy được 30 việc trong 30 giây, rồi `Shutdown phase 1073741823 ends with 1 bean still running after timeout of 30000ms: [applicationTaskExecutor]`; 2 việc đang chạy nhận `InterruptedException`, 8 việc trong hàng đợi biến mất không một dòng log.
  - Hành vi này phụ thuộc phiên bản và cách tạo executor (executor tự `new` không do Spring quản lý vòng đời thì không được chờ); kiểm trên đúng phiên bản bạn chạy. Dù phiên bản nào, hàng đợi trong bộ nhớ không bao giờ là nơi giữ việc quan trọng.
- **Kubernetes**:
  - Trình tự theo tài liệu: pod chuyển sang Terminating; kubelet chạy `preStop`, xong mới gửi SIGTERM; đồng thời endpoint của pod được đánh dấu `ready: false`, `terminating: true` trong EndpointSlice và các bộ cân bằng tải gỡ dần. Hết grace period mà `preStop` còn chạy thì kubelet cho thêm 2 giây một lần, rồi SIGKILL.
  - `preStop` có action `sleep` gốc, không cần lệnh `sleep` trong image (distroless không có shell).
  - Grace period gồm cả `preStop`: `preStop` 10 giây với grace 30 giây chỉ còn 20 giây cho app.
  - Sidecar gốc (init container `restartPolicy: Always`) được dừng sau container app, nên proxy hay agent log không tắt trước khi app xả xong.
- **Load balancer bên ngoài**: ALB gỡ target theo deregistration delay (mặc định 300 giây) và health check, độc lập với pod; dùng AWS Load Balancer Controller với target kiểu IP thì `preStop` cần đủ dài cho ALB ngừng gửi (bài AWS cho kỹ sư backend).
- **Consumer message**:
  - Kafka: listener container dừng sớm nhất (phase cao hơn web server); dừng là ngừng poll, chờ xử lý xong batch hiện tại, commit offset, rời group; mỗi lần một pod rời là một lần rebalance. Static membership (`group.instance.id`) với rolling update giảm rebalance (bài Kafka producer & consumer chuyên sâu).
  - SQS: ngừng nhận message mới; message đang xử lý mà chưa xoá sẽ xuất hiện lại sau visibility timeout, nên consumer phải idempotent.
- **Kết nối dài**: SSE, WebSocket, long polling giữ request mở nên graceful shutdown của web server chờ tới hết timeout. Chủ động đóng chúng khi nhận `ContextClosedEvent` và để client tự kết nối lại có backoff (bài gRPC, WebSocket, SSE & long polling).
- **Vòng đời khởi động**: pod chỉ nên nhận traffic khi đã sẵn sàng thật (connection pool mở, cache nạp, JIT đã ấm nếu cần); Boot chuyển readiness sang `ACCEPTING_TRAFFIC` sau `ApplicationReadyEvent`. Khởi động chậm dùng startup probe (bài Vận hành ứng dụng trên Kubernetes).
- **Thiết kế chịu chết đột ngột** (crash-only): coi tắt êm là phần thưởng, không phải bảo đảm. Việc quan trọng ghi vào bảng [[outbox|outbox]] hoặc queue bền trong cùng transaction với dữ liệu nghiệp vụ; worker lấy việc, làm, rồi mới đánh dấu xong; mọi bước idempotent (bài Idempotency).
