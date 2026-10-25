## Quick

[[micrometer|Micrometer]] là lớp đo lường của Spring: code ghi metric qua `MeterRegistry`, còn Prometheus, Datadog hay OTLP chỉ là nơi xuất. Từ Boot 3, **[[observation-api|Observation API]]** đo một lần mà ra cả metric lẫn trace, và trace id tự vào log. **Tag phải có ít giá trị** ([[metric-cardinality|cardinality]] thấp): đặt `userId` hay URL thô làm tag là mỗi giá trị một time series, đủ làm phình bộ nhớ ứng dụng và làm sập Prometheus.

## Interview

**Loại meter**:
- `Counter`: chỉ tăng, như số đơn đặt.
- `Timer`: số lần và thời gian, như latency.
- `Gauge`: giá trị hiện tại, như kích thước queue.
- `DistributionSummary`: phân bố của giá trị không phải thời gian, như kích thước payload.
- `LongTaskTimer`: việc đang chạy dở bao lâu, như job batch; `FunctionCounter` và `FunctionTimer` đọc số từ object có sẵn (cache, pool) thay vì tự đếm.

Mỗi tổ hợp tên và tag là một time series.

**Có sẵn từ Boot**: `http.server.requests` (tag `uri` là template `/orders/{id}`, không phải URL thật), JVM, HikariCP, executor, cache, Kafka. Prometheus lấy số qua `/actuator/prometheus` của [[actuator|Actuator]].

**Percentile**: percentile tính sẵn ở client (`publishPercentiles`) **không cộng gộp được** giữa các pod. Muốn p99 của cả dịch vụ thì bật `publishPercentileHistogram` rồi tính bằng `histogram_quantile` phía Prometheus.

**Tracing**:
- Micrometer Tracing (thay Spring Cloud Sleuth từ Boot 3) tạo span cho request vào, gọi ra bằng `RestClient`, `WebClient`, Kafka, JDBC (khi có instrumentation).
- Trace id đi qua header W3C `traceparent`.
- Bridge sang OpenTelemetry hoặc Brave để xuất tới Tempo, Jaeger, Zipkin.
- `management.tracing.sampling.probability` mặc định 0.1, tức 10% request được giữ trace.

**Log correlation**: Boot 3.2+ tự thêm `traceId` và `spanId` vào log pattern khi có tracing. Từ một dòng log lỗi, nhảy được sang trace của đúng request đó.

**Bẫy hay gặp**:
- **Cardinality**: client HTTP gọi `restTemplate.getForObject(baseUrl + "/users/" + id)` thì tag `uri` của metric client là URL thật, mỗi id một series. Truyền URI template (`"/users/{id}", id`) thay vì nối chuỗi.
- **Mất trace khi đổi thread**: `@Async`, `CompletableFuture`, thread pool tự tạo không mang context theo nếu không dùng context propagation ([[thread-local|ThreadLocal]] không sang thread mới; bài @Async, @Scheduled & event).

## Deep

- **Observation API**: `Observation.createNotStarted("order.place", registry).observe(() -> ...)` sinh timer `order.place`, một span, và log có trace id. `@Observed` trên method làm điều tương tự qua AOP: bật `management.observations.annotations.enabled=true` (Boot 3.2+, áp cả `@Timed`, `@Counted`) hoặc tự khai báo `ObservedAspect`, và chịu đủ bẫy của proxy. Tag có ít giá trị đưa vào `lowCardinalityKeyValue` (thành tag metric); giá trị nhiều như order id đưa vào `highCardinalityKeyValue` (chỉ nằm ở span).
- **Giới hạn của Boot**: `management.metrics.web.client.max-uri-tags` và `...server.max-uri-tags` (mặc định 100) chặn thêm giá trị `uri` mới khi vượt, kèm cảnh báo trong log. Đây là lưới an toàn; nó không sửa code nối chuỗi.
- **`MeterFilter`**: đổi tên, bỏ tag, chặn meter, đặt SLO bucket cho histogram (`serviceLevelObjectives`). Dùng để chặn metric của thư viện sinh quá nhiều series.
- **Histogram tốn**: với timer, histogram mặc định (1ms tới 30 giây) sinh 69 series bucket cho mỗi tổ hợp tag (xem phần thực hành). Bật cho vài timer quan trọng, không bật toàn cục.
- **Gauge và tham chiếu yếu**: `Gauge` giữ tham chiếu yếu tới object được đo. Object bị GC thì gauge trả `NaN` mà không báo lỗi; giữ tham chiếu mạnh tới object đó.
- **Exemplar**: với Prometheus (định dạng scrape OpenMetrics) và tracing, histogram mang theo trace id mẫu; trên Grafana bấm vào điểm p99 để mở trace của một request chậm thật.
- **Sampling**: head-based sampling 10% nghĩa là trace của request lỗi hiếm có thể không được giữ. Muốn giữ mọi trace lỗi thì cần tail sampling ở OpenTelemetry Collector.
- **Log vẫn là nguồn chính khi điều tra**: log có cấu trúc (JSON, Boot 3.4+ có sẵn `logging.structured.format.console` với `ecs`, `logstash` hoặc `gelf`) cộng trace id giúp tìm đúng request; metric cho biết có vấn đề, trace cho biết chậm ở đâu, log cho biết vì sao.
- **Bảo mật**: `/actuator/prometheus` không chứa bí mật nhưng lộ cấu trúc hệ thống; đặt ở port quản trị (bài Auto-configuration & cấu hình). Đừng đưa email hay số điện thoại vào tag hoặc tên span.
- **Boot 3 và Boot 4**: Boot 4 có starter riêng `spring-boot-starter-opentelemetry` và `spring-boot-starter-zipkin`, và chuyển cấu hình OTLP sang `management.opentelemetry.tracing.export.otlp.*`; nâng cấp cần chạy `spring-boot-properties-migrator`.
- **Khái niệm chung (RED, USE, SLI, SLO)** thuộc bài Metrics, tracing & SLO; bài này tập trung vào cách Spring cài đặt.
