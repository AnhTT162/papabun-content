## Quick

Trong một process, lời gọi method chỉ có hai kết cục: trả về hoặc ném exception. Qua mạng có thêm kết cục thứ ba: **không biết**. Request có thể mất, có thể đã được xử lý nhưng response mất, hoặc chỉ đang chậm, và [[timeout|timeout]] không phân biệt được ba trường hợp đó. Vì vậy hệ phân tán phải được thiết kế với giả định có [[partial-failure|partial failure]]: **mọi lời gọi có timeout, chỉ retry thao tác idempotent, và chấp nhận rằng message có thể trùng hoặc đến sai thứ tự**.

## Interview

**Tám ngộ nhận về hệ phân tán** ([[fallacies-of-distributed-computing|fallacies of distributed computing]]): mạng tin cậy được; latency bằng 0; băng thông vô hạn; mạng an toàn; topology không đổi; chỉ có một người quản trị; chi phí truyền dữ liệu bằng 0; mạng đồng nhất. Code viết như gọi method trong process là đang ngầm tin vào cả tám.

**Ba kết cục của một lời gọi**: `OrderService` gọi `PaymentService` để trừ tiền rồi hết thời gian chờ.
- Request chưa tới nơi: an toàn để gửi lại.
- Payment đã trừ tiền, response mất: gửi lại là trừ hai lần.
- Payment đang chậm: gửi lại làm nó quá tải thêm.

Cách làm đúng: gửi kèm [[idempotency-key|idempotency key]] để bên nhận nhận ra lần gửi lại, hoặc hỏi trạng thái trước khi gửi lại.

**Timeout là bắt buộc, và mặc định thường là vô hạn**: `HttpURLConnection`, JDK `HttpClient` (Java 11+, không đặt `timeout` cho request), `RestTemplate` với `SimpleClientHttpRequestFactory` đều chờ mãi nếu server nhận kết nối mà không trả lời. Một dependency treo là đủ làm cạn thread pool và kéo sập service gọi nó. Đặt cả connect timeout lẫn timeout cho response, và một deadline tổng cho cả request. Chọn giá trị theo p99 hoặc p99.9 đo được của dependency cộng biên an toàn: quá ngắn thì kết luận nhầm là bên kia chết và retry thừa, quá dài thì giữ thread lâu và phát hiện lỗi chậm.

**Latency cộng dồn và đuôi phóng đại**: một request gọi song song 10 backend, mỗi backend có 1% lời gọi chậm (p99), thì khoảng 9,6% request bị chậm; gọi 100 backend thì khoảng 63%. Tối ưu p99 của từng service quan trọng hơn trung bình.

## Deep

- **Process bị dừng trông như chết**: GC pause dài, VM bị migrate, hay container bị throttle CPU làm một node không trả lời vài giây. Các node khác kết luận nó đã chết, chọn leader mới, rồi node cũ tỉnh lại và vẫn tưởng mình là leader ([[split-brain|split brain]]). Đây là lý do cần [[fencing|fencing token]] (bài Distributed lock).
- **Không biết chắc node đã chết**: hệ thống chỉ có thể nghi ngờ, bằng heartbeat cộng timeout. Một số hệ (Cassandra, Akka) dùng phi accrual failure detector: tính mức nghi ngờ theo phân bố thời gian giữa các heartbeat gần đây, nên thích nghi với mạng chậm thay vì dùng một ngưỡng cố định.
- **Đồng hồ không đáng tin**: đồng hồ các máy lệch nhau vài mili giây tới vài giây, và NTP có thể chỉnh lùi. Không sắp xếp sự kiện giữa các máy chỉ bằng timestamp (bài Đồng hồ, thứ tự & sinh ID).
- **ACK của TCP không phải là "đã xử lý"**: TCP chỉ đảm bảo byte tới được kernel bên kia. Ứng dụng có thể crash trước khi đọc. Muốn biết thao tác đã xong thì cần xác nhận ở tầng ứng dụng.
- **Exactly-once delivery không có qua mạng không tin cậy**: chỉ chọn được at-most-once (gửi một lần, có thể mất) hoặc at-least-once (gửi lại tới khi được xác nhận, có thể trùng). "Exactly-once" mà Kafka nói tới là exactly-once **processing** trong phạm vi của nó, đạt được bằng at-least-once cộng dedup hoặc transaction.
- **[[gray-failure|Gray failure]]**: một node vẫn trả lời health check nhưng xử lý request thật rất chậm hoặc lỗi một phần. Health check chỉ kiểm tra "process còn sống" không phát hiện được; cần theo dõi tỉ lệ lỗi và latency của request thật.
- **[[network-partition|Network partition]]**: hai nhóm node vẫn chạy nhưng không nói chuyện được với nhau. Mỗi bên phải quyết định tiếp tục phục vụ (chấp nhận dữ liệu lệch) hay dừng (mất khả dụng), đúng nội dung của CAP (bài Consistency, CAP & PACELC).
- **Hỏng dây chuyền**: một dependency chậm làm thread chờ, pool cạn, service gọi nó cũng chậm, và lan ngược lên. Retry ở mọi tầng còn nhân tải lên: 3 tầng, mỗi tầng thử tối đa 3 lần, là 27 lời gọi xuống tầng cuối cho một request gốc. Timeout, retry có giới hạn, [[circuit-breaker|circuit breaker]] và [[bulkhead|bulkhead]] là các công cụ chặn (bài Timeout, retry, circuit breaker).
- **Mô hình lỗi**: phần lớn hệ thống doanh nghiệp giả định crash-recovery (node có thể chết rồi sống lại, mất trạng thái trong bộ nhớ). Byzantine (node nói dối hay gửi dữ liệu sai cố ý) dùng trong blockchain và hệ an toàn cao như hàng không, hiếm khi cần trong hệ thống nội bộ.
- **Quan sát được là điều kiện tiên quyết**: correlation id đi theo request qua mọi service, distributed tracing (OpenTelemetry) và log có cấu trúc. Không có chúng, câu hỏi "request này chết ở đâu" mất hàng giờ.
