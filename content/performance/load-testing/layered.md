## Quick

Load test phải trả lời **một câu hỏi có số**: chịu được bao nhiêu req/s mà p99 còn trong [[slo|SLO]], bản mới có chậm hơn bản cũ không, chạy 8 giờ có rò bộ nhớ không. Chọn đúng [[open-workload-model|mô hình tải]]: người dùng thật đến không phụ thuộc server nhanh hay chậm (mô hình mở), còn công cụ chạy [[virtual-user|virtual user]] vòng lặp kín sẽ tự giảm tải khi server chậm và giấu mất thời gian chờ ([[coordinated-omission|coordinated omission]]). **Đọc kết quả bằng p99 theo throughput thật đạt được, kèm metric phía server, và kiểm tra máy tạo tải không phải là nút cổ chai.**

## Interview

**Loại test theo câu hỏi**: *load test* ở đỉnh dự kiến; *[[stress-test|stress test]]* tăng dần tới khi vỡ để tìm trần và xem hệ thống hỏng ra sao; *spike test* tăng đột ngột như campaign; *[[soak-test|soak test]]* chạy nhiều giờ để thấy rò bộ nhớ, connection, đĩa đầy.

**Mô hình tải**:
- *[[closed-workload-model|Đóng]]*: N virtual user, mỗi user gửi, chờ response, nghỉ [[think-time|think time]], gửi tiếp. Throughput = `N / (R + Z)`: 200 user không nghỉ, R = 110ms là khoảng 1.800 req/s; server chậm tới 2 giây thì chỉ còn 100 req/s. Tải tự giảm đúng lúc hệ thống gặp khó.
- *Mở*: request đến theo tốc độ định trước. k6 dùng executor `constant-arrival-rate`, `ramping-arrival-rate`; Gatling dùng `constantUsersPerSec`, `rampUsersPerSec`.

**Coordinated omission**: test 200 giây, 100 req/s, server trả trong 1ms nhưng đứng đúng một lần, kéo dài 10 giây. Một user vòng kín ghi 19.001 mẫu, p99 và p99.9 đều 1ms. Đo từ lúc request lẽ ra được gửi: 20.000 mẫu, p99 khoảng 8,2 giây, 5% request chậm hơn 1 giây (1.000 request lẽ ra được gửi trong lúc đứng, chờ từ 10 giây giảm dần).

**Cho giống thật**: tỉ lệ endpoint lấy từ access log; dữ liệu đủ lớn và đủ đa dạng (10 product id thì cache hit 100%); bỏ phần [[jit|JIT]] khởi động khỏi kết quả; môi trường cùng cấu hình; dependency giả lập phải có latency như thật.

**Đọc kết quả**: throughput đạt được thấp hơn mục tiêu nghĩa là hệ thống (hoặc máy tạo tải) đã bão hoà. Nhìn p99 tăng theo tải để tìm điểm gãy, đếm lỗi riêng (lỗi trả nhanh làm latency trông đẹp), và đặt USE metric phía server cạnh kết quả để biết tài nguyên nào bão hoà trước. So với baseline, chạy lại vài lần trước khi kết luận.

## Deep

- **k6**: `dropped_iterations` đếm lần lặp không bắt đầu được vì thiếu VU trong executor arrival-rate; đặt `maxVUs` đủ (theo [[littles-law|Little's law]], 3.000 req/s × 2 giây khi server chậm cần 6.000 VU) và đặt threshold cho nó. `http_req_duration` bằng sending + waiting + receiving, không gồm thời gian chờ connection (`http_req_blocked`) bắt tay TCP (`http_req_connecting`) và TLS (`http_req_tls_handshaking`); đọc cả hai khi nghi pool hay TLS. Threshold như `http_req_duration: ['p(99)<300']` làm test trả exit code khác 0, dùng được trong CI; thêm `abortOnFail: true` để dừng test sớm khi đã vượt ngưỡng rõ ràng.
- **Gatling** (Java DSL, kiểm với 3.16): `injectOpen(rampUsersPerSec(10).to(300).during(...), constantUsersPerSec(300).during(...))` là mô hình mở, `injectClosed(constantConcurrentUsers(...))` là mô hình đóng; assertion `global().responseTime().percentile(99.0).lt(300)`. Mỗi user trong mô hình mở chạy hết kịch bản rồi kết thúc, nên một user có `pause` dài vẫn không làm giảm tốc độ đến.
- **JMeter và Locust**: Thread Group thường của JMeter là mô hình đóng (mỗi thread là một user vòng kín); mô hình mở cần Open Model Thread Group (từ JMeter 5.5) hoặc plugin Arrivals Thread Group. Locust cũng chạy theo số user, tức mô hình đóng.
- **Mô hình mở cũng có giới hạn**: người dùng thật cũng bỏ đi hoặc bấm lại khi chậm. Mô hình mở đo đúng thời gian chờ nhưng không mô phỏng retry; muốn thấy [[retry-storm|retry storm]] thì phải cấu hình retry trong kịch bản giống client thật.
- **Sửa sau khi đo**: [[hdrhistogram|HdrHistogram]] có `recordValueWithExpectedInterval` để bù các mẫu bị bỏ sót khi biết khoảng gửi mong muốn; wrk2 ra đời từ wrk để gửi theo tốc độ cố định. Trong mô phỏng ở trên, cách bù này cho p99 khoảng 8 giây, gần với đo theo mô hình mở.
- **Máy tạo tải là nút cổ chai**: CPU của máy tạo tải trên 80%, hết ephemeral port, GC của chính Gatling, băng thông mạng. Dấu hiệu là latency phía client tăng mà latency phía server không đổi. Theo dõi máy tạo tải như một server, và chia tải ra nhiều máy khi cần. Chạy nhiều máy thì gộp histogram (HdrHistogram cộng được) rồi mới tính p99, không lấy trung bình p99 của từng máy.
- **Kết nối không giống thật**: một VU giữ keep-alive suốt test thì không có chi phí bắt tay TLS; người dùng thật mở connection mới thường xuyên. Ngược lại, mỗi lần lặp mở connection mới (k6 `noConnectionReuse`) có thể làm TLS thành nút cổ chai không có trên production. Chọn theo cách client thật dùng connection.
- **Phân phối dữ liệu**: phân bố truy cập thật lệch (vài sản phẩm hot, đa số lạnh). Lấy id theo phân bố từ log, không lặp một id và cũng không chọn đều ngẫu nhiên; cả hai đều cho tỉ lệ cache hit và lock khác production. Database staging nhỏ hơn 20 lần thì plan và thời gian query khác (bài Database chậm trên production).
- **Warm-up và thời lượng**: bỏ vài phút đầu khỏi kết quả vì JIT và cache chưa nóng, nhưng đo riêng giai đoạn này nếu muốn biết p99 sau deploy hay khi autoscale. Mỗi mức tải nên giữ đủ lâu (5–10 phút) để có đủ mẫu cho p99 và thấy được chu kỳ GC.
- **Lỗi làm sai latency**: request lỗi `503` trả trong 2ms kéo p99 xuống. Đọc latency riêng cho request thành công, và đặt threshold tỉ lệ lỗi (`http_req_failed`) song song với latency.
- **Đọc đường cong**: tăng tải từng bậc, vẽ p99 và throughput đạt được theo tải mục tiêu. Throughput đi ngang trong khi p99 tăng vọt là điểm gãy; trần để lập kế hoạch là bậc cuối cùng p99 còn trong SLO (bài Capacity planning & autoscaling). Kiểm tra bằng Little's law: số request đồng thời phía server ≈ throughput × latency trung bình; lệch nhiều thì có chỗ đo sai.
- **Staging nhỏ hơn production**: ít pod hơn thì không nhân tuyến tính kết quả lên; đo ở 2–3 kích thước cụm và ngoại suy thận trọng ([[universal-scalability-law|Universal Scalability Law]], bài Capacity planning & autoscaling).
- **Đo ở đâu**: latency phía client gồm hàng đợi ở load balancer, accept queue và mạng; latency phía server thì không. Khoảng cách giữa hai con số cho biết thời gian chờ trước khi request vào ứng dụng (bài Điều tra API chậm).
- **Regression test trong CI**: môi trường dùng chung ồn, dao động 10–20% là bình thường. So tương đối với baseline chạy cùng môi trường, đặt ngưỡng rộng hơn độ dao động, và chạy lại khi vượt ngưỡng trước khi chặn build. Hiệu năng một method thì dùng JMH, không dùng load test.
- **Test trên production**: shadow traffic (nhân bản request thật sang bản mới, bỏ response), replay access log, hoặc [[canary-release|canary]] với lưu lượng thật. Không ghi dữ liệu thật trong shadow, và không replay request thanh toán hay gửi email.
- **Không được test hệ thống của người khác**: tạo tải lên API bên thứ ba hay dịch vụ cloud dùng chung có thể vi phạm điều khoản và bị coi là tấn công; giả lập dependency đó với latency và giới hạn như thật.
