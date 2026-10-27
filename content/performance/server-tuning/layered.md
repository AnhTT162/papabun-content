## Quick

Server có [[thread-pool|thread pool]], HTTP client có [[connection-pool|connection pool]], cả hai đều có hàng đợi và giá trị mặc định không hợp với production: Tomcat có 200 thread, Apache HttpClient 5 chỉ cho **5 kết nối mỗi host**, chờ mượn kết nối tới 3 phút và không giới hạn thời gian chờ response. **Mọi lời gọi ra ngoài phải có connect timeout, [[read-timeout|response timeout]] và thời gian chờ pool**; kích thước pool tính bằng [[littles-law|Little's law]] từ RPS và latency, không đoán.

## Interview

**Phía server (Tomcat)**: Tomcat nhận tới `server.tomcat.max-connections` kết nối (mặc định 8192); kết nối [[keep-alive|keep-alive]] nhàn rỗi không chiếm thread nhờ NIO. Request được xử lý bởi tối đa `threads.max` thread (200). Thread bận hết thì request đã đọc xếp hàng chờ thread; đủ 8192 kết nối thì kết nối mới chờ trong hàng đợi của hệ điều hành dài [[accept-count|`accept-count`]] (100), đầy nữa thì client bị từ chối hoặc hết giờ khi kết nối.

**Bao nhiêu thread là đủ**: Little's law cho số request đồng thời = RPS × latency. 1.000 request/giây × 0,1 giây là 100 request đang chạy. Nếu latency tăng lên 2 giây vì DB chậm, cần 2.000 thread; thêm thread lúc đó chỉ dời hàng đợi xuống connection pool của DB.

**Timeout phía server**: `connection-timeout` (60 giây ở Tomcat nhúng) là thời gian chờ dữ liệu request, và cũng là keep-alive timeout nếu không đặt `keep-alive-timeout` riêng. Keep-alive của server phải dài hơn idle timeout của [[load-balancer|load balancer]] phía trước (AWS ALB mặc định 60 giây), nếu không load balancer gửi request vào kết nối vừa bị đóng và trả 502 (quy tắc thứ tự idle timeout ở bài HTTP request đi qua những gì).

**Phía HTTP client**: Spring Boot chọn Apache HttpClient 5 cho `RestClient` và `RestTemplate` khi có trên classpath. Pool mặc định 25 kết nối, 5 cho mỗi route (host). Cần đặt ba [[timeout|timeout]]:
- connect timeout: mở TCP (và TLS);
- response timeout: chờ byte tiếp theo của response;
- connection request timeout: chờ mượn kết nối từ pool.

JDK `HttpClient` không giới hạn số kết nối nhưng cũng không có timeout mặc định.

**Cách làm đúng**: kích thước pool = RPS tới downstream × latency p99 của nó, cộng phần dư. Timeout dựa trên latency thật của downstream (p99 150ms thì response timeout khoảng 1 giây), không để vô hạn. Mỗi downstream một pool riêng ([[bulkhead|bulkhead]]), và theo dõi số thread chờ pool như một metric.

## Deep

- **Tomcat NIO gồm ba phần**: acceptor nhận kết nối, poller theo dõi socket nào có dữ liệu, worker thread chạy filter và controller. Vì vậy 8.000 kết nối nhàn rỗi chỉ tốn bộ nhớ socket, không tốn thread. `threads.min-spare` (10) là số thread giữ sẵn khi rảnh.
- **Tăng `threads.max` có giá**: mỗi platform thread giữ một stack (mặc định đặt trước 1 MB trên Linux x64, dùng tới đâu cấp tới đó), nhiều thread thì nhiều context switch hơn. Nếu thread chủ yếu chờ DB, giới hạn thật là `maximum-pool-size` của [[hikaricp|HikariCP]] (mặc định 10); xem bài Connection pool và bài Thread pool & ExecutorService.
- **[[virtual-thread|Virtual thread]]**: `spring.threads.virtual.enabled=true` (Spring Boot 3.2+, Java 21+) cho Tomcat chạy mỗi request trên một virtual thread, `threads.max` không còn là giới hạn. Giới hạn phải chuyển sang pool DB, pool HTTP client hoặc semaphore, nếu không một đợt tải dồn hết vào downstream. Chi tiết ở bài Virtual threads.
- **Undertow**: io thread bằng số core (tối thiểu 2), worker thread bằng io thread × 8. Spring Boot 4 bỏ hỗ trợ Undertow vì chưa tương thích Servlet 6.1; nâng cấp thì chuyển sang Tomcat hoặc Jetty.
- **Keep-alive lệch ở chiều client**: client giữ kết nối nhàn rỗi lâu hơn keep-alive của server thì có lúc dùng một kết nối server vừa đóng, nhận `NoHttpResponseException` (HttpClient 5) hoặc `Connection reset`. HttpClient 5 mặc định retry một lần cho method idempotent, nên lỗi lộ ra ở `POST`. Đặt `evictIdleConnections` ngắn hơn keep-alive của server và `timeToLive` cho kết nối. Phía Tomcat còn `server.tomcat.max-keep-alive-requests` (100): đủ số request đó thì Tomcat chủ động đóng kết nối, client phải xử lý được việc này.
- **Response timeout không phải tổng thời gian**: nó giới hạn khoảng chờ giữa hai lần nhận dữ liệu. Server gửi chậm từng mẩu, mỗi mẩu cách nhau dưới 1 giây, thì lời gọi có thể kéo dài mãi. Muốn giới hạn tổng thời gian thì bọc thêm deadline ở tầng trên (`TimeLimiter`, `orTimeout`) và chia ngân sách thời gian theo chuỗi gọi (bài Tail latency).
- **Thuộc tính của Spring Boot**: Boot 3.4 thêm `spring.http.client.connect-timeout` và `read-timeout` cho client tự cấu hình; Boot 4 đổi thành `spring.http.clients.*`. Kích thước pool vẫn phải tự đặt qua `PoolingHttpClientConnectionManagerBuilder`.
- **Route và bulkhead**: HttpClient 5 giới hạn theo route (scheme, host, port), nên một host chậm chỉ chiếm tối đa `maxPerRoute` kết nối. Nhưng thread Tomcat vẫn bị giữ trong lúc chờ: bulkhead thật cần giới hạn số lời gọi đồng thời (semaphore, bài Resilience patterns) hoặc timeout chờ pool ngắn.
- **[[http-compression|Nén response]]**: `server.compression.enabled` mặc định tắt; bật thì chỉ nén response từ 2 KB (`min-response-size`) với các kiểu text, JSON, XML. Nén tốn CPU của ứng dụng; nếu gateway hay CDN phía trước đã nén thì không nén hai lần. Chọn gzip hay Brotli, nén gì và không nén gì ở bài Hiệu năng phía client.
- **Graceful shutdown**: từ Spring Boot 3.4, `server.shutdown=graceful` là mặc định: ngừng nhận request mới và chờ request đang chạy tới `spring.lifecycle.timeout-per-shutdown-phase` (30 giây). Kết hợp với connection draining ở load balancer để rolling deploy không làm rơi request (bài Load balancing).
- **Metric cần có**: `tomcat.threads.busy` và `tomcat.threads.config.max` (cần `server.tomcat.mbeanregistry.enabled=true`), `http.server.requests`; với HttpClient 5, Micrometer có `PoolingHttpClientConnectionManagerMetricsBinder` cho số kết nối đang mượn và số request đang chờ pool (`httpcomponents.httpclient.pool.total.pending`). Request chờ pool tăng là dấu hiệu sớm nhất của pool quá nhỏ.
