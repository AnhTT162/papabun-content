## Quick

[[sampling-profiler|Sampling profiler]] chụp stack của thread định kỳ (async-profiler mặc định mỗi 10ms, JFR 20ms hoặc 10ms với cấu hình `profile`) rồi gộp lại thành [[flame-graph|flame graph]]: khối càng rộng, càng nhiều mẫu rơi vào đó. **Chọn event theo câu hỏi**: CPU cao thì profile `cpu`, latency cao mà CPU thấp thì profile [[wall-clock-profiling|wall-clock]], GC nhiều thì profile [[allocation-profiling|allocation]], tranh khoá thì profile `lock`. **Đọc theo tổng thời gian của nhánh, không theo [[self-time|self time]] của từng method.**

## Interview

**Profiler làm gì**: không đo từng lời gọi (như instrumentation) mà lấy mẫu stack định kỳ, nên chi phí chỉ vài phần trăm và chạy được trên production. Kết quả là tỉ lệ: method có mặt trong 56% số mẫu là đang chiếm khoảng 56% thời gian đo được.

**Đọc flame graph**: trục ngang là số mẫu, không phải thời gian; khối con nằm trên khối gọi nó. Đọc từ dưới lên theo nhánh rộng nhất. Khối phẳng trên đỉnh là self time; nhánh rộng là tổng. Chi phí thật thường rải trong hàng trăm method nhỏ của cùng một lời gọi cha, nên danh sách "hot method" phẳng dễ đánh lừa.

**Chọn event**:
- `cpu`: chỉ đếm thread đang chạy trên CPU, không thấy thời gian chờ DB, HTTP, khoá.
- `wall`: đếm mọi thread bất kể trạng thái, nên phải lọc theo thread xử lý request, nếu không thread rảnh chiếm gần hết mẫu.
- `alloc`: lấy mẫu theo byte cấp phát, tìm nơi tạo rác làm GC chạy nhiều.
- `lock`: thời gian chờ vào `synchronized` hoặc `ReentrantLock`.

**Công cụ**:
- [[async-profiler|async-profiler]]: `asprof -d 30 -e cpu -f cpu.html <pid>` ra flame graph HTML, có cả khung native và kernel.
- [[jfr|JFR]] có sẵn trong JDK: `jcmd <pid> JFR.start settings=profile duration=60s filename=rec.jfr`, đọc bằng JDK Mission Control hoặc `jfr view hot-methods rec.jfr` (JDK 21+).

**Bẫy hay gặp**: profile lúc [[jit|JIT]] chưa nóng, profile một pod không nhận traffic, dùng `cpu` cho bài toán chờ, tin self time, và sửa mà không đo lại.

**Quy trình**: đặt câu hỏi bằng số (CPU mỗi request tăng gấp đôi), chọn event, ghi 30–60 giây trong lúc có vấn đề, đọc nhánh rộng nhất, sửa, rồi profile lại và so trước/sau.

## Deep

- **Self time và total time**: trong một ca thật (ứng dụng tạo `ObjectMapper` mới cho mỗi lần ghi log), method nóng nhất theo self chỉ chiếm 4,6%, nhưng nhánh `toJson` chiếm 56% tổng. Trong nhánh đó, dựng serializer (`BeanSerializerFactory`) tốn 43%, ghi JSON thật chỉ 3% và constructor của `ObjectMapper` chỉ 3%: Jackson cache serializer trong từng mapper, nên mapper mới nào cũng introspect lại class bằng reflection.
- **Wall-clock cần lọc thread**: chạy `wall` trên cả process có 30 thread rảnh và một thread xử lý request thì thread request chỉ chiếm khoảng 2% số mẫu. Lọc theo thread (`asprof -e wall -t`, rồi chỉ xem `http-nio-*`) mới thấy 90% thời gian của request nằm ở lời gọi downstream mà profile `cpu` gần như không ghi nhận (dưới 1%).
- **Nguồn mẫu CPU của async-profiler**: mặc định dùng `perf_events` của Linux, thấy cả khung kernel. Trong container thường bị chặn (`perf_event_paranoid`, seccomp); khi đó dùng `-e ctimer` hoặc `-e itimer`. Nó dùng `AsyncGetCallTrace` nên không bị [[safepoint-bias|safepoint bias]] (bài Ứng dụng Java CPU 100%). Từ bản 3.0, lệnh là `asprof` thay cho `profiler.sh`.
- **Allocation profiling**: async-profiler `-e alloc` (hoặc `--alloc 512k`) lấy mẫu mỗi khi một thread xin TLAB mới hoặc cấp phát ngoài TLAB, nên chi phí thấp và tỉ lệ theo byte. JFR có `jdk.ObjectAllocationSample` (JDK 16+) với giới hạn số mẫu mỗi giây. Nhiều byte cấp phát chưa chắc là leak: đó là áp lực lên young GC; leak xem heap sau GC (bài Bộ nhớ tăng dần & OOM).
- **Lock profiling**: async-profiler `-e lock` đo thời gian chờ cả `synchronized` lẫn khoá `java.util.concurrent`; JFR ghi `jdk.JavaMonitorEnter` và `jdk.ThreadPark` khi chờ quá ngưỡng (20ms với cấu hình mặc định). Một khối rộng trên appender log đồng bộ hay một `synchronized` quanh lời gọi chậm là thủ phạm hay gặp.
- **JFR chạy liên tục**: `-XX:StartFlightRecording=maxage=6h,maxsize=500m,settings=default` giữ bản ghi vòng tròn trên đĩa; `jcmd <pid> JFR.dump name=1 filename=incident.jfr` lấy đúng khoảng có sự cố. Cấu hình `default` tốn dưới khoảng 1%, `profile` khoảng 2% theo tài liệu Oracle; `profile` lấy mẫu execution dày hơn và bật thêm sự kiện. `jdk.ExecutionSample` chỉ lấy mẫu thread đang chạy code Java; thread đang ở native có `jdk.NativeMethodSample` riêng, còn thread đang chờ thì không có trong cả hai. JDK 25 thêm `jdk.CPUTimeSample`, lấy mẫu theo CPU time trên Linux (JEP 509, experimental), sát với profile `cpu` của async-profiler hơn.
- **Đọc JFR không cần GUI**: `jfr summary rec.jfr` cho biết có sự kiện gì; `jfr view hot-methods`, `allocation-by-site`, `gc`, `contention-by-site` (JDK 21+) in bảng ngay trong terminal; `jfr print --events jdk.ExecutionSample` in từng mẫu. JDK Mission Control có flame graph và so sánh hai bản ghi.
- **Khung bị inline**: JIT gộp method nhỏ vào method gọi nó. Thêm `-XX:+UnlockDiagnosticVMOptions -XX:+DebugNonSafepoints` để JVM giữ thông tin vị trí ở cả những điểm không phải safepoint, nhờ đó mẫu rơi đúng dòng và đúng method (kể cả method đã inline) thay vì bị dồn về điểm debug gần nhất. Cờ này có ích cho cả async-profiler lẫn JFR.
- **Differential flame graph**: so hai profile cùng tải (trước và sau release) để thấy nhánh nào rộng ra. Chuẩn hoá theo số request, không theo thời gian ghi, vì tổng số mẫu thay đổi theo tải.
- **Continuous profiling**: Pyroscope, Grafana, Datadog chạy async-profiler hay JFR liên tục trên mọi pod và gắn profile với trace, nên xem được span chậm tiêu CPU vào đâu (bài Metrics, tracing & SLO).
- **Profiler không thay benchmark**: profiler cho biết chỗ tốn trong hệ thống thật; xác nhận một bản sửa nhỏ ở mức method thì dùng JMH, vì vòng lặp tự viết bị JIT tối ưu bỏ hoặc đo lẫn cả warm-up.
