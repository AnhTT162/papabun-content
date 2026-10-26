## Quick

Observability là khả năng trả lời "hệ thống đang làm gì và vì sao" từ dữ liệu nó phát ra: **metric cho biết có vấn đề, [[distributed-tracing|trace]] cho biết chậm ở đâu, log cho biết vì sao**. [[opentelemetry|OpenTelemetry]] là chuẩn chung để thu cả ba. Đo trải nghiệm người dùng bằng [[sli|SLI]], đặt mục tiêu bằng [[slo|SLO]], và **alert khi [[error-budget|error budget]] cháy nhanh**, không alert theo CPU.

## Interview

**Metric**: số tổng hợp theo thời gian, rẻ để lưu lâu và để alert. Dashboard mỗi service theo RED (Rate, Errors, Duration), tài nguyên theo USE (bài Phương pháp phân tích hiệu năng). Latency lưu dạng histogram để tính percentile chung cho nhiều pod.

**Distributed tracing**: một trace là cây các [[span]], mỗi span là một bước (request HTTP, query, gửi message) có thời điểm bắt đầu, thời lượng và thuộc tính. Trace id đi qua header W3C `traceparent` ([[context-propagation|context propagation]]), kể cả qua header của message Kafka. Không lưu được mọi trace nên phải sampling: head-based quyết định ngay từ đầu (rẻ, nhưng có thể bỏ mất trace lỗi hiếm); [[tail-sampling|tail-based]] quyết định sau khi trace kết thúc, giữ mọi trace lỗi hoặc chậm, nhưng cần bộ đệm ở OpenTelemetry Collector.

**OpenTelemetry**: API và SDK cho nhiều ngôn ngữ, Java agent tự instrument mà không sửa code, giao thức OTLP, và Collector để nhận, lọc, lấy mẫu rồi gửi tới Prometheus, Tempo, Jaeger hay dịch vụ thương mại. Đổi backend không phải sửa ứng dụng.

**SLI, SLO, error budget**:
- SLI là tỉ lệ sự kiện tốt: request không lỗi 5xx và nhanh hơn 300ms trên tổng request, đo ở load balancer hoặc gateway.
- SLO là mục tiêu cho SLI trong một cửa sổ: 99,9% trong 30 ngày.
- Error budget là phần được phép hỏng: 0,1%, tương đương 43 phút hỏng hoàn toàn mỗi 30 ngày.
- SLA là cam kết hợp đồng, luôn lỏng hơn SLO.

**Alert theo [[burn-rate|burn rate]]**: tốc độ tiêu budget so với mức đều. Burn rate 14,4 trong 1 giờ nghĩa là mất 2% budget của cả tháng chỉ trong một giờ: gọi người on-call. Burn rate thấp kéo dài thì tạo ticket. Alert theo triệu chứng người dùng thấy, còn CPU cao hay pod restart chỉ là nguyên nhân có thể có và nên nằm trên dashboard.

**Bẫy**: tag có giá trị không giới hạn làm nổ số time series, SLO 100% hoặc quá nhiều SLO, đo SLI ở chỗ người dùng không cảm nhận được.

## Deep

- **Kiểu metric**: counter chỉ tăng (đọc bằng `rate()`), gauge là giá trị hiện tại, histogram đếm theo bucket. Percentile tính sẵn ở mỗi pod không gộp được; histogram thì gộp được rồi dùng `histogram_quantile`. Cách Spring cài đặt (Micrometer, `publishPercentileHistogram`, cardinality của tag `uri`) ở bài Micrometer & tracing.
- **Pull và push**: Prometheus kéo `/metrics` theo chu kỳ (thường 15–30 giây), nên biết ngay target nào chết (`up == 0`) nhưng job ngắn kết thúc trước lần scrape thì mất số; job batch đẩy qua Pushgateway hoặc OTLP. OTLP là push, đi qua Collector.
- **Dữ liệu mỗi loại tốn bao nhiêu**: metric rẻ và không phụ thuộc lưu lượng (phụ thuộc số series); trace và log tăng theo lưu lượng. 3.000 request/giây, mỗi request 10 span, sampling 10% vẫn là 3.000 span mỗi giây. Ngân sách lưu trữ quyết định tỉ lệ sampling.
- **Tail sampling cần đủ span ở một chỗ**: mọi span của một trace phải tới cùng một instance Collector để nó quyết định. Chạy nhiều Collector thì đặt lớp load balancing theo trace id phía trước (`loadbalancingexporter`), và chấp nhận độ trễ quyết định (ví dụ chờ 10–30 giây).
- **[[exemplar|Exemplar]]**: histogram gắn kèm trace id mẫu của request rơi vào bucket đó. Từ điểm p99 trên Grafana mở thẳng trace của một request chậm thật: nối metric sang trace. Cần Prometheus bật lưu exemplar (`--enable-feature=exemplar-storage`) và scrape bằng định dạng OpenMetrics, nếu không exemplar bị bỏ qua mà không báo lỗi.
- **Trace qua message**: producer ghi `traceparent` vào header của message, consumer tạo span mới. Consumer xử lý theo batch thường dùng span link thay vì quan hệ cha con, vì một span xử lý nhiều message thuộc nhiều trace.
- **SLI đo ở đâu**: đo ở LB hoặc gateway gần người dùng hơn đo trong ứng dụng (bắt được cả lúc ứng dụng không trả lời). Synthetic check (gọi định kỳ từ bên ngoài) bắt được lỗi DNS và chứng chỉ, nhưng ít mẫu. SLI cho job hoặc pipeline là độ tươi dữ liệu ("99% bản ghi có mặt trong 10 phút").
- **Alert nhiều cửa sổ**: theo SRE Workbook, gọi người khi burn rate ≥ 14,4 trong cửa sổ 1 giờ và cả cửa sổ 5 phút (cửa sổ ngắn để alert tự tắt nhanh khi đã hết lỗi); ≥ 6 trong 6 giờ và 30 phút cũng gọi người; ≥ 1 trong 3 ngày và 6 giờ thì tạo ticket. Một cửa sổ đơn lẻ thì hoặc báo quá muộn, hoặc báo động giả nhiều.
- **SLO 99,99% đắt hơn nhiều so với 99,9%**: 4,3 phút mỗi tháng không đủ cho một lần rollback thủ công. Mỗi số 9 thêm đòi deploy tự động rollback, multi-zone, và mọi dependency cũng phải tin cậy hơn. Dùng error budget còn lại để quyết định nên đẩy tính năng hay dừng lại sửa độ ổn định (chính sách error budget: bài Độ tin cậy & SRE).
- **Continuous profiling** đang được coi là loại tín hiệu thứ tư: async-profiler hay JFR chạy liên tục, gắn với trace để biết span chậm tiêu CPU vào method nào (bài Profiling).
- **Đừng đo trùng ba lần**: một sự kiện "đơn đặt thành công" không cần cả metric, log INFO và span event. Metric cho đếm, span cho thời gian, log cho chi tiết khi có lỗi.
