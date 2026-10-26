## Quick

[[load-balancer|Load balancer]] chia request cho nhiều instance và bỏ qua instance hỏng. **L4** chia theo kết nối TCP/UDP (IP, port): nhanh, không nhìn nội dung. **L7** hiểu HTTP: định tuyến theo path, header, cookie, [[tls-termination|kết thúc TLS]], retry. Thuật toán phổ biến: [[round-robin|round robin]], [[least-connections|least connections]] (hay least outstanding requests), và hash theo key khi cần cùng một client về cùng một instance. **Instance phải stateless để LB thay được bất kỳ instance nào; sticky session là lựa chọn cuối.**

## Interview

**Chọn thuật toán**:
- *Round robin* (có trọng số nếu instance không đều): ổn khi request tốn chi phí gần như nhau.
- *Least connections / least outstanding requests*: tốt hơn khi chi phí request chênh lệch (báo cáo nặng lẫn API nhẹ), vì instance đang bận nhận ít việc hơn.
- *Power of two choices*: chọn ngẫu nhiên hai instance rồi gửi tới cái ít việc hơn. Gần bằng least connections mà không cần trạng thái toàn cục; Envoy dùng cho `LEAST_REQUEST`.
- *Hash theo key* (IP, user id): giữ cache cục bộ nóng cho cùng một key, đổi lại phân phối không đều khi có key nóng. Hash modulo N chuyển gần hết key sang instance khác mỗi khi thêm hay bớt instance; consistent hashing (ring hash, Maglev trong Envoy) chỉ chuyển khoảng 1/N (bài Consistent hashing).

**[[health-check|Health check]]**: chủ động (LB gọi `/health` định kỳ) và bị động (đếm lỗi của request thật rồi loại instance). Trong Kubernetes: readiness probe quyết định pod có nhận traffic không; liveness probe quyết định có restart không. **Liveness không được kiểm tra dependency** như database: database chậm một phút mà mọi pod bị restart cùng lúc là sự cố tự gây ra.

**Deploy không rơi request** ([[connection-draining|connection draining]]): trước khi tắt, instance phải được rút khỏi LB rồi mới dừng nhận request, xử lý nốt request đang chạy. Spring Boot 3.4+ bật graceful shutdown mặc định (2.3–3.3 phải đặt `server.shutdown=graceful`), giới hạn bởi `spring.lifecycle.timeout-per-shutdown-phase` (mặc định 30 giây). Kubernetes cần thêm `preStop` chờ vài giây vì việc gỡ pod khỏi endpoint lan tới các node không tức thì. `terminationGracePeriodSeconds` (mặc định 30 giây, tính cả `preStop`) phải lớn hơn tổng hai khoảng đó, nếu không kubelet gửi SIGKILL giữa chừng.

**[[sticky-session|Sticky session]]**: gắn client với một instance (cookie của LB). Dùng khi session nằm trong bộ nhớ, nhưng instance chết là mất session, và tải lệch khi scale. Nên đưa session ra ngoài (Spring Session với Redis) hoặc dùng token.

## Deep

- **L4 trong Kubernetes và cloud**: kube-proxy (iptables hay IPVS) và AWS NLB là L4; Ingress controller (NGINX, Envoy), AWS ALB, service mesh là L7. L4 không thấy HTTP nên không retry hay định tuyến theo path được, và không chia đều request của kết nối lâu dài (HTTP/2, gRPC, WebSocket).
- **Kết nối lâu dài không tự cân bằng lại**: scale từ 3 lên 6 instance, các kết nối [[keep-alive|keep-alive]] cũ vẫn bám vào 3 instance đầu cho tới khi đóng. Đặt tuổi tối đa cho kết nối (`max-connection-age` ở phía server gRPC, giới hạn số request mỗi kết nối ở proxy) để tải lan sang instance mới.
- **Retry ở LB**: LB L7 thường retry khi upstream trả `502`/`503` hay mất kết nối. Với `POST` không idempotent, retry có thể tạo đơn trùng. Giới hạn retry theo method, hoặc yêu cầu idempotency key.
- **Slow start**: instance vừa khởi động (JIT chưa nóng, cache rỗng, connection pool chưa mở) nhận ngay toàn bộ phần tải của nó sẽ chậm và lỗi. Tăng dần trọng số cho instance mới (slow start của Envoy, ALB), hoặc warm-up trước khi báo ready.
- **DNS làm load balancing và cache của JVM**: DNS trả nhiều IP thì client chọn một và giữ theo TTL. JVM cache kết quả DNS theo `networkaddress.cache.ttl` (mặc định 30 giây khi không có security manager), cộng thêm việc connection pool giữ kết nối cũ, nên IP mới không được dùng ngay.
- **Header của proxy**: sau LB L7, `request.getRemoteAddr()` là IP của LB. IP thật nằm trong `X-Forwarded-For` hoặc `Forwarded`. Spring Boot đọc theo `server.forward-headers-strategy`: mặc định `NATIVE` khi chạy trên nền tảng cloud nó nhận ra (kể cả Kubernetes), `NONE` ở nơi khác; với Tomcat, `NATIVE` dùng `RemoteIpValve` và chỉ tin proxy khớp `server.tomcat.remoteip.internal-proxies`. Đừng tự đọc phần tử bên trái nhất của `X-Forwarded-For`: client giả mạo được phần đó. Đi từ phải sang trái, bỏ qua các proxy bạn tin cậy, phần tử đầu tiên còn lại mới là IP client.
- **[[client-side-load-balancing|Client-side load balancing]]**: client tự giữ danh sách instance (Spring Cloud LoadBalancer, gRPC) và chọn, bỏ được một hop và thấy được latency của từng instance. Đổi lại, mỗi ngôn ngữ cần thư viện, và cấu hình nằm rải ở mọi client; service mesh chuyển phần này vào sidecar.
- **LB cũng là điểm lỗi**: LB cần chạy dư (nhiều node, nhiều zone) và có giới hạn kết nối, băng thông. Cloud LB tự scale nhưng có thể cần "pre-warm" trước một đợt tăng tải đột ngột như flash sale.
