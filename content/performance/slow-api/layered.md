## Quick

Điều tra API chậm là **chia thời gian của một request ra từng tầng và tìm tầng chiếm phần lớn**. Bắt đầu bằng câu hỏi chậm cho ai: mọi request hay chỉ [[tail-latency|tail]], một endpoint hay tất cả, một pod hay mọi pod. Sau đó **so [[latency|latency]] đo ở nhiều điểm** (client, [[load-balancer|load balancer]], ứng dụng, dependency): khoảng chênh giữa hai điểm đo chính là thời gian chờ nằm giữa chúng.

## Interview

Tôi đi theo bốn bước.

**1. Khoanh hình dạng của chậm**: p50 tăng (mọi request chậm, thường do tải hoặc một dependency chính) khác hẳn chỉ p99 tăng (một phần request gặp chuyện: GC, chờ pool, retry, một pod lỗi). Tách theo endpoint, theo pod, theo thời gian. Chậm theo chu kỳ đều đặn gợi ý job định kỳ hoặc GC; chậm chỉ trên vài pod gợi ý node hoặc cấu hình.

**2. So các điểm đo**: thời gian ở load balancer lớn hơn `http.server.requests` của ứng dụng nghĩa là request chờ trước khi tới controller (hàng đợi của Tomcat, mạng). Thời gian `http.client.requests` lớn hơn thời gian phía server của downstream nghĩa là mất ở giữa: chờ pool kết nối, mở kết nối, DNS, mạng.

**3. Mở [[distributed-tracing|trace]] của request chậm, không phải request trung bình**: [[span|span]] nào dài nhất? Nếu không span nào dài mà tổng vẫn lớn, thời gian nằm ở **khoảng trống giữa các span**: chờ [[connection-pool|connection pool]], chờ khoá, GC pause, [[cpu-throttling|CPU throttling]]. Trace có 300 span DB ngắn là [[n-plus-one|N+1]], không phải DB chậm.

**4. Kiểm tra từng tầng bằng metric riêng của nó**:
- DB: thời gian query, `hikaricp_connections_pending`, lock wait.
- Downstream: `http.client.requests` theo host, timeout, retry.
- JVM: GC pause, safepoint, thread `BLOCKED`.
- [[thread-pool|Thread pool]]: thread bận, hàng đợi.
- Mạng: retransmit, thời gian connect, DNS.

**Bẫy hay gặp**: nhìn trung bình thay vì [[percentile|percentile]]; đọc trace của request nhanh; tin metric của ứng dụng trong khi request chưa tới được ứng dụng; sửa ngay tầng nghi ngờ đầu tiên (thêm index, thêm pod) mà chưa có bằng chứng. Latency gom thành cụm ở con số tròn như 1 giây, 3 giây, 5 giây thường là timeout hoặc cơ chế gửi lại, không phải code chậm.

## Deep

- **Dấu vân tay của con số**: cụm quanh 200ms là RTO tối thiểu khi [[tcp-retransmission|gửi lại gói TCP]] trên Linux; cụm 1 giây và 3 giây là SYN bị mất và gửi lại (1 giây, rồi thêm 2 giây); cụm 5 giây hay 10 giây thường là [[timeout|timeout]] [[dns|DNS]] của resolver (`timeout:5` mặc định trong `resolv.conf`) hoặc timeout tự đặt. Cụm 40ms trên kết nối nhỏ, nhiều lượt ghi là tương tác giữa Nagle và delayed ACK.
- **Thời gian connect bị giấu trong span client**: span `http.client.requests` gồm cả chờ pool, DNS, TCP, TLS. Span phía server của downstream bắt đầu muộn hơn span client bao lâu thì đó là thời gian trước khi request tới được server.
- **[[conntrack|conntrack]] đầy**: trên node Kubernetes, mỗi kết nối qua Service được kernel ghi vào bảng conntrack, và kết nối đã đóng vẫn nằm ở đó ở trạng thái TIME_WAIT của conntrack 120 giây (`nf_conntrack_tcp_timeout_time_wait`), lâu hơn socket [[time-wait|TIME_WAIT]] 60 giây ở máy gọi. Ứng dụng mở kết nối mới cho mỗi request làm bảng đầy, kernel bỏ gói SYN (`nf_conntrack: table full, dropping packet` trong `dmesg`), latency nhảy lên 1 giây và 3 giây. kube-proxy đặt `nf_conntrack_max` theo số core (32768 mỗi core, tối thiểu 131072).
- **GC**: pause [[stop-the-world|stop-the-world]] làm chậm cùng lúc mọi request trên một pod, nên đỉnh latency thẳng hàng giữa các endpoint của pod đó và không có trên pod khác. Đối chiếu với GC log (`-Xlog:gc`) hoặc `jvm.gc.pause`. Safepoint lâu (time-to-safepoint) cũng dừng mọi thread mà không hiện là GC.
- **CPU throttling**: container chạm CPU limit bị dừng tới hết chu kỳ CFS 100ms, nên latency tăng theo bậc khoảng 100ms dù CPU trung bình chỉ 50%. Xem `container_cpu_cfs_throttled_periods_total`; chi tiết ở bài Ứng dụng Java CPU 100%.
- **Request đầu sau deploy chậm**: [[jit|JIT]] chưa biên dịch code nóng, class chưa load, cache rỗng, pool kết nối tới downstream chưa mở. Gửi request khởi động (warm-up) trước khi pod nhận traffic thật, hoặc dùng readiness probe chỉ báo sẵn sàng sau khi warm-up xong.
- **DNS trong JVM**: JVM cache kết quả phân giải thành công 30 giây mặc định (`networkaddress.cache.ttl`) và kết quả lỗi 10 giây. Resolver trong pod với `ndots:5` thử lần lượt các domain tìm kiếm trước khi tới tên thật, nên một tên ngoài cụm có thể tốn năm lần truy vấn; dùng tên đầy đủ có dấu chấm cuối hoặc giảm `ndots`. Ca timeout DNS 5 giây nổi tiếng trên Kubernetes: glibc gửi song song truy vấn A và AAAA trên cùng socket UDP, hai gói đua nhau khi tạo mục conntrack và một gói bị bỏ, resolver chờ hết 5 giây mới thử lại (`options single-request-reopen` hoặc NodeLocal DNSCache giảm được). musl (Alpine) xử lý `resolv.conf` khác glibc, nên cùng cấu hình có thể cho kết quả khác.
- **Chờ ở chỗ không có metric**: lock trong code (`synchronized` quanh lời gọi chậm), appender log đồng bộ (bài Log cho production), `@Transactional` giữ connection suốt lời gọi HTTP (bài Connection pool). Thread dump chụp đúng lúc chậm cho thấy những chỗ này; [[jfr|JFR]] ghi cả sự kiện chờ khoá và đọc socket có thời gian.
- **Payload lớn**: serialize hoặc parse JSON vài MB tốn CPU và tạo nhiều rác cho GC; latency tăng theo kích thước response chứ không theo tải. Nhìn `http.server.requests` theo endpoint cùng kích thước response.
- **Đo đúng ở client**: load test hay synthetic check phải tính thời gian từ lúc request lẽ ra được gửi, không phải lúc thực sự gửi, nếu không sẽ giấu mất thời gian chờ ([[coordinated-omission|coordinated omission]], bài Load & performance testing).
