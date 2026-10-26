## Quick

Hiệu năng có hai trục: [[latency]] (một request mất bao lâu) và [[throughput]] (bao nhiêu request mỗi giây). **Đọc latency bằng [[percentile]] (p50, p95, p99), không bằng trung bình**, và tìm [[bottleneck|nút cổ chai]] bằng phương pháp chứ không đoán: [[red-method|RED]] cho từng service, [[use-method|USE]] cho từng tài nguyên. [[littles-law|Little's law]] và [[amdahls-law|Amdahl's law]] cho biết giới hạn trước cả khi đo.

## Interview

**Latency và throughput** là hai đại lượng khác nhau. Latency gồm thời gian chờ (trong hàng đợi) cộng thời gian xử lý thật. Tăng thread có thể tăng throughput, nhưng nếu tài nguyên phía sau đã bận thì chỉ làm hàng đợi dài thêm và latency tăng.

**Percentile**: p99 là 200ms nghĩa là 99% request nhanh hơn 200ms. Trung bình che mất phần đuôi: 100 request gồm 95 cái 20ms, 4 cái 300ms và 1 cái 3 giây thì trung bình 61ms, p50 20ms, p99 300ms, chậm nhất 3 giây. Đuôi quan trọng vì một trang gọi 10 backend thì 9,6% lượt tải trang dính ít nhất một request chậm hơn p99 của backend ([[tail-latency|tail latency]]).

**Phương pháp, không đoán**:
- *RED* cho mỗi service, nhìn từ phía người gọi: Rate, Errors, Duration.
- *USE* cho mỗi tài nguyên: Utilization (bận bao nhiêu), [[saturation|Saturation]] (bao nhiêu việc đang phải chờ), Errors. Tài nguyên gồm cả CPU, bộ nhớ, đĩa, mạng lẫn thread pool, connection pool, lock. Saturation là dấu hiệu nút cổ chai rõ nhất.

**Hai định luật dùng hằng ngày**:
- Little's law `L = λ × W`: 200 request/giây, mỗi request 250ms thì trung bình 50 request đang chạy cùng lúc. Downstream chậm làm latency lên 2 giây thì cần 400, vượt 200 thread mặc định của Tomcat, và request bắt đầu xếp hàng.
- Amdahl's law: phần tuần tự giới hạn mức tăng tốc. 90% việc song song hoá được thì 8 core chỉ nhanh hơn 4,7 lần, vô hạn core cũng không quá 10 lần.

**Bẫy hay gặp**: tối ưu thứ không phải nút cổ chai, nhìn latency trung bình, đổi nhiều thứ cùng lúc rồi không biết cái nào có tác dụng, đo trên máy dev rồi suy ra production. Quy trình đúng: đặt mục tiêu bằng số (p99 dưới 300ms ở 500 request/giây), đo, tìm tài nguyên bão hoà, sửa một chỗ, đo lại.

## Deep

- **Hàng đợi làm latency tăng phi tuyến**: theo mô hình hàng đợi đơn giản nhất (M/M/1), thời gian phản hồi ≈ `S / (1 − U)` với `S` là thời gian xử lý và `U` là utilization. `S` = 10ms thì U 50% cho 20ms, 80% cho 50ms, 90% cho 100ms, 95% cho 200ms. Hệ thống thật không đúng từng con số, nhưng hình dạng đường cong thì đúng: gần 100% là latency vọt lên. Vì vậy cần chừa headroom (bài Capacity planning & autoscaling).
- **Percentile không cộng, không lấy trung bình được**: p99 của bốn pod lấy trung bình không phải p99 của dịch vụ. Phải gộp histogram rồi mới tính (bài Micrometer & tracing). Cửa sổ cũng quan trọng: p99 trong 1 phút và trong 1 giờ là hai con số khác nhau.
- **Trung bình vẫn có chỗ dùng**: Little's law đúng với giá trị trung bình ở trạng thái ổn định, bất kể phân phối của latency, nên trung bình và throughput dùng để tính tài nguyên (bao nhiêu thread, bao nhiêu connection); percentile dùng cho trải nghiệm người dùng và SLO (bài Metrics, tracing & SLO).
- **Đo ở đâu thì thấy cái đó**: timer phía server chỉ bắt đầu khi thread nhận request. Thời gian nằm trong accept queue của Tomcat, trong load balancer hay trong connection pool của client không có trong metric đó. Đo thêm ở client hoặc LB; khi tạo tải giả lập thì coi chừng [[coordinated-omission|coordinated omission]] (bài Load & performance testing).
- **Điểm gãy của throughput**: tăng tải dần thì throughput tăng gần tuyến tính, tới một điểm thì đi ngang, rồi có thể giảm vì tranh chấp (lock, context switch, đồng bộ cache giữa các node). Latency vọt lên đúng quanh điểm đó. Universal Scalability Law của Neil Gunther mô hình hoá thêm phần giảm này mà Amdahl không có.
- **Phần tuần tự không chỉ là code**: một lock, một dòng dữ liệu nóng trong database, một partition Kafka, Redis xử lý lệnh trên một luồng chính. Thêm instance không giúp nếu mọi request phải đi qua đúng chỗ đó.
- **USE cho một service Java**: CPU (utilization %, saturation qua run queue hoặc [[cpu-throttling|CPU throttling]] trong container); heap (dung lượng sau GC, saturation qua % thời gian GC); thread pool của Tomcat (`tomcat.threads.busy` / `tomcat.threads.config.max`; Spring Boot chỉ xuất hai metric này khi bật `server.tomcat.mbeanregistry.enabled=true`); connection pool (`hikaricp_connections_active` / max, `hikaricp_connections_pending`); mạng (retransmit). Errors: task bị từ chối, timeout khi lấy connection.
- **Four golden signals** của Google SRE (latency, traffic, errors, saturation) là RED cộng thêm saturation. Hai phản-phương pháp nên tránh: chỉ nhìn công cụ mình quen ("tìm chìa khoá dưới cột đèn"), và đổi cấu hình ngẫu nhiên cho tới khi hết lỗi.
- **Benchmark nhỏ cũng có bẫy**: đo một method bằng `System.nanoTime()` trong vòng lặp dễ sai vì JIT chưa nóng hoặc loại bỏ code chết; dùng JMH (bài JIT compiler).
