## Quick

Log trên production phải **tìm được** (có cấu trúc, có [[correlation-id|correlation id]] và trace id), **rẻ** (đúng mức log, không ghi thừa) và **an toàn** (không chứa mật khẩu, token, dữ liệu cá nhân). Ghi [[structured-logging|structured log]] dạng JSON ra stdout, để hạ tầng gom về một chỗ (ELK, [[loki|Loki]]). **Log không phải nơi lưu dữ liệu nghiệp vụ**: appender có thể bỏ dòng, và việc ghi log có thể làm chậm cả ứng dụng.

## Interview

**Structured log**: mỗi dòng là một JSON có trường cố định (`timestamp`, `level`, `logger`, `message`, `trace_id`, `order_id`...). Tìm theo trường thay vì regex, stack trace nằm gọn trong một bản ghi thay vì vỡ thành nhiều dòng. Spring Boot 3.4+ bật bằng `logging.structured.format.console=ecs` (hoặc `logstash`, `gelf`).

**Correlation**: filter đặt `trace_id` (hoặc correlation id nhận từ gateway) vào [[mdc|MDC]], nên mọi dòng log của request mang theo nó. MDC dựa trên `ThreadLocal`, không tự sang thread khác (bài ThreadLocal & ScopedValue). Có Micrometer Tracing thì `traceId` và `spanId` tự vào MDC (Boot 3.0+), và từ Boot 3.2 pattern log mặc định in sẵn chúng.

**[[log-level|Mức log]]**: ERROR là cần người xử lý, WARN là bất thường nhưng hệ thống tự xoay xở được, INFO là sự kiện nghiệp vụ quan trọng, DEBUG chỉ bật tạm. Production mặc định INFO; đổi mức một logger lúc chạy qua `/actuator/loggers` mà không restart. Endpoint này phải được expose và có xác thực, chỉ áp dụng cho pod nhận request, và mất khi pod restart.

**Chi phí**: 3.000 request/giây, mỗi request 5 dòng 500 byte là 7,5 MB/giây, khoảng 650 GB mỗi ngày. Dịch vụ log thường tính tiền theo GB nạp vào. Dùng log có tham số (`log.debug("Order {}", id)`) để không ghép chuỗi khi mức đó tắt, không log cả body request, đặt thời gian lưu theo nhu cầu.

**Bẫy hay gặp**:
- `log.error(e.getMessage())` mất stack trace và cause; truyền exception làm tham số cuối: `log.error("Charge failed, order {}", orderId, e)`.
- Log rồi ném lại: một lỗi xuất hiện năm lần ở năm tầng.
- Ghi dữ liệu nhạy cảm (token, số thẻ, email) vào log, nơi nhiều người đọc được và lưu lâu.
- Dùng log làm audit trail: [[async-appender|AsyncAppender]] của Logback mặc định bỏ dòng INFO khi hàng đợi gần đầy.

## Deep

- **Ghi ra stdout trong container**: ứng dụng không tự xoay vòng file hay đẩy log đi; agent trên node (Fluent Bit, Vector, OpenTelemetry Collector) đọc stdout và gửi đi. Agent chậm hoặc đĩa node đầy thì việc ghi vào pipe stdout bị chặn, và `ConsoleAppender` đồng bộ chặn luôn thread xử lý request (xem phần thực hành).
- **Logback ghi đồng bộ có khoá**: `OutputStreamAppender` giữ một `ReentrantLock` (`streamWriteLock` ở Logback 1.5) khi ghi. Một thread ghi chậm là mọi thread khác muốn log phải đợi; thread dump thấy hàng trăm thread `WAITING (parking)` trên `ReentrantLock` trong `OutputStreamAppender.writeBytes`.
- **AsyncAppender đánh đổi gì**: đưa event vào hàng đợi (mặc định 256) cho một thread riêng ghi. Mặc định khi còn dưới 20% chỗ trống thì bỏ TRACE, DEBUG, INFO (`discardingThreshold`), còn khi đầy hẳn thì chặn thread gọi (`neverBlock=false`). `neverBlock=true` thì không bao giờ chặn nhưng bỏ cả WARN, ERROR khi đầy. Không có cấu hình nào vừa không mất vừa không chặn. Log4j2 có async logger dựa trên LMAX Disruptor với lựa chọn tương tự.
- **Tham số vẫn bị tính**: `log.debug("Cart {}", cart.toJson())` vẫn gọi `toJson()` dù DEBUG đang tắt; chỉ phần ghép chuỗi được bỏ qua. Dùng `if (log.isDebugEnabled())` hoặc fluent API của SLF4J 2 với supplier: `log.atDebug().addArgument(() -> cart.toJson()).log("Cart {}")`.
- **Caller data tốn kém**: pattern có `%line`, `%method`, `%file` buộc Logback tạo stack trace cho mỗi dòng log; với AsyncAppender còn cần `includeCallerData=true`. Tránh trên đường nóng.
- **ELK và Loki**: Elasticsearch đánh index toàn văn mọi trường, tìm nhanh và linh hoạt nhưng tốn lưu trữ và vận hành. Loki chỉ đánh index nhãn (service, namespace, level) và quét nội dung khi truy vấn, rẻ hơn nhiều; nhãn phải có ít giá trị, không đặt `user_id` hay `trace_id` làm nhãn. Loki 3.x có structured metadata để gắn `trace_id` vào từng dòng mà không tạo stream mới.
- **Log dồn dập khi lỗi**: dependency hỏng làm mỗi request ghi một stack trace dài; khối lượng log nhân lên đúng lúc hệ thống yếu nhất. Giới hạn bằng circuit breaker (không gọi thì không lỗi), log tóm tắt theo chu kỳ thay vì từng lần, hoặc giới hạn tốc độ ở agent.
- **Che dữ liệu nhạy cảm**: che từ nguồn (`toString()` của DTO không in trường nhạy cảm, record thì override), bổ sung bằng bộ lọc mask ở encoder hoặc agent. Header `Authorization` và cookie không bao giờ được log. Log là dữ liệu cá nhân theo luật bảo vệ dữ liệu khi chứa thông tin định danh: cần thời hạn lưu và quyền truy cập.
- **Log là đầu vào nguy hiểm**: chuỗi người dùng nhập vào log có thể chứa ký tự xuống dòng để giả dòng log (log injection), và Log4Shell (CVE-2021-44228) cho thấy chính thư viện log có thể thực thi chuỗi từ input. Structured log JSON tự escape xuống dòng; chi tiết thư viện ở bài Logging trong Java.
- **Log, metric hay trace**: đếm số lần thì dùng metric (rẻ, alert được); thời gian từng bước dùng trace; log để lại chi tiết khi có lỗi hoặc sự kiện nghiệp vụ hiếm (bài Metrics, tracing & SLO).
