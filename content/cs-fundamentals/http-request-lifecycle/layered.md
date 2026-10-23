## Quick

Một HTTP request đi qua các chặng: [[dns|DNS]] tìm IP, [[tcp-handshake|TCP handshake]] mở kết nối, [[tls-handshake|TLS handshake]] mã hoá, gửi request, qua [[load-balancer|load balancer]] tới app server, app server gọi database rồi trả response. **Phần lớn độ trễ của request đầu tiên nằm ở các vòng [[rtt|RTT]] trước khi byte dữ liệu đầu tiên được gửi đi, nên tái sử dụng kết nối ([[keep-alive]]) là tối ưu quan trọng nhất.**

## Interview

Giả sử người dùng mở `https://shop.example.com/orders`.

1. **DNS**: trình duyệt hỏi cache của chính nó, rồi cache của OS, rồi recursive resolver (thường của ISP hoặc 8.8.8.8). Resolver đi từ root → TLD `.com` → authoritative server của `example.com` để lấy bản ghi A/AAAA. Kết quả được cache theo TTL (thời gian sống của bản ghi, tính bằng giây).
2. **TCP**: client gửi SYN, server trả SYN-ACK, client gửi ACK. Mất 1 RTT trước khi gửi được dữ liệu.
3. **TLS**: với TLS 1.3, client gửi ClientHello kèm key share và SNI (tên miền cần chứng chỉ), server trả chứng chỉ và hoàn tất trong 1 RTT. TLS 1.2 cần 2 RTT. Client kiểm tra chứng chỉ theo chuỗi CA.
4. **HTTP request**: method, path, header (`Host`, `Cookie`, `Authorization`...), body nếu có.
5. **Load balancer / [[reverse-proxy|reverse proxy]]**: thường làm [[tls-termination|TLS termination]], chọn một instance còn khoẻ theo health check, chuyển tiếp request qua một kết nối khác tới backend, thêm header như `X-Forwarded-For`.
6. **App server**: ví dụ Tomcat nhận request, giao cho một worker thread, chạy filter chain rồi tới controller. Controller gọi database qua [[connection-pool|connection pool]].
7. **Response** đi ngược lại: status code, header, body.

Bẫy hay gặp: nghĩ rằng mỗi request đều trả giá DNS + TCP + TLS. Thực tế HTTP/1.1 mặc định giữ kết nối mở (persistent connection), request sau đi thẳng tới bước 4. Nếu client hoặc service-to-service tạo kết nối mới mỗi lần gọi, latency tăng thêm vài RTT và server tốn CPU cho handshake.

HTTP/2 cho nhiều request chạy song song trên một kết nối bằng [[multiplexing]]. HTTP/3 chạy trên [[quic|QUIC]] (UDP), gộp handshake transport và TLS, và tránh [[head-of-line-blocking|head-of-line blocking]] ở tầng TCP.

## Deep

- **Đo từng chặng**: `curl -w "dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer}\n" -o /dev/null -s https://example.com`. Các giá trị là mốc thời gian cộng dồn tính từ lúc bắt đầu, không phải thời lượng của riêng từng chặng.
- **DNS TTL và failover**: TTL dài làm cache lâu, chuyển IP khi sự cố sẽ chậm. JVM cũng cache DNS: security property `networkaddress.cache.ttl` (trong OpenJDK mặc định 30 giây khi không có security manager), đáng kiểm tra khi backend đổi IP.
- **HTTP/1.1 chỉ xử lý một request mỗi lúc trên một kết nối** (pipelining hầu như không dùng). Trình duyệt mở khoảng 6 kết nối mỗi host để chạy song song.
- **HTTP/2 multiplexing**: request và response được chia thành frame có stream id, đan xen trên một kết nối TCP. Header được nén bằng HPACK. Nhưng mất một gói TCP thì mọi stream phải chờ gửi lại: head-of-line blocking chuyển xuống tầng TCP.
- **HTTP/3 trên QUIC** (RFC 9114, RFC 9000): mỗi stream được đánh số thứ tự riêng nên mất gói chỉ chặn stream đó. QUIC tích hợp TLS 1.3, handshake 1 RTT, có 0-RTT khi kết nối lại (dữ liệu 0-RTT có thể bị replay, chỉ nên dùng cho request idempotent). Connection ID giúp kết nối sống sót khi điện thoại đổi từ Wi-Fi sang 4G.
- **Load balancer L4 và L7**: L4 chỉ nhìn IP/port và chuyển tiếp byte. L7 hiểu HTTP nên route được theo path/header, terminate TLS, retry. Sau TLS termination, đoạn LB → backend có thể là HTTP thường hoặc mã hoá lại tuỳ yêu cầu bảo mật.
- **Idle timeout phải tăng dần theo chiều đi vào**: keep-alive timeout của client nên nhỏ hơn idle timeout của LB, và idle timeout của LB nên nhỏ hơn keep-alive timeout của backend. Nếu backend đóng kết nối trước, LB có thể gửi request vào kết nối vừa bị đóng và trả 502 lẻ tẻ.
- **App server**: Tomcat có `maxConnections` (số kết nối giữ được) tách biệt với `maxThreads` (số request xử lý đồng thời). Request chờ connection pool DB hết chỗ cũng làm thread của Tomcat bị giữ.
