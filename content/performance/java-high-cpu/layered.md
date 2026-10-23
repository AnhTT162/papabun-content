## Quick

CPU 100% luôn là **một vài thread cụ thể đang chạy liên tục**: thread của ứng dụng (vòng lặp, regex, serialize...), thread GC, hoặc thread JIT. **Quy trình: `top -H` tìm thread nóng → đổi TID sang `nid` → đối chiếu trong [[thread-dump|thread dump]] chụp vài lần liên tiếp**, đồng thời kiểm tra GC. Thu bằng chứng trước khi restart.

## Interview

Tôi đi theo bốn bước, và luôn thu bằng chứng trước khi restart vì restart xoá sạch dấu vết.

1. **Xác nhận tiến trình**: `top` để chắc chắn tiến trình Java là thủ phạm. Trong container, xem cả [[cpu-throttling|CPU throttling]]: chạm CPU limit cũng làm latency tăng dù `top` không hiện 100% trên toàn máy.
2. **Tìm thread nóng**: `top -H -p <pid>` liệt kê từng thread. Trên Linux, cột PID ở chế độ này là TID của thread, và tên thread Java hiện ở cột COMMAND (cắt còn 15 ký tự, ví dụ `http-nio-8080-e`).
3. **Đối chiếu với thread dump**: chụp `jcmd <pid> Thread.print` (hoặc `jstack <pid>`) 3 lần, cách nhau 5–10 giây. Mỗi thread trong dump có [[native-thread-id|nid]]. Từ JDK 18, `nid` in dạng thập phân, khớp thẳng với TID trong `top`. Đến JDK 17, `nid` in dạng hex nên phải đổi: `printf '%x\n' 4123` ra `101b`, rồi tìm `nid=0x101b`. Thread nào cùng một stack ở cả 3 lần là đang kẹt ở đó.
4. **Loại trừ GC**: nếu thread nóng tên là `GC Thread#0`, `G1 Conc#0`... thì vấn đề là bộ nhớ, không phải code. `jstat -gcutil <pid> 1000` cho thấy Old gen gần 100% và cột FGC tăng liên tục; GC log cho thấy [[full-gc|Full GC]] nối tiếp nhau mà giải phóng được rất ít. Khi đó CPU cao chỉ là triệu chứng, cần điều tra heap.

Khi thread dump không đủ rõ (CPU dàn trải trên nhiều method, không có thread nào kẹt hẳn), dùng [[sampling-profiler|sampling profiler]]: async-profiler xuất [[flame-graph|flame graph]], hoặc [[jfr|JFR]] với `jcmd <pid> JFR.start duration=60s settings=profile filename=cpu.jfr`. Cả hai đủ nhẹ để chạy trên production.

Nguyên nhân hay gặp: regex bị [[catastrophic-backtracking|catastrophic backtracking]], vòng [[busy-spin|busy-spin]] retry không có backoff, GC thrashing gần OOM, log hoặc serialize JSON quá nhiều, JIT compile lúc mới khởi động.

## Deep

- **Thread `RUNNABLE` chưa chắc đang dùng CPU**: thread đọc socket cũng hiện `RUNNABLE` vì đang trong native code. Luôn đối chiếu với `top -H` hoặc trường `cpu=` trong dump (có từ JDK 11+), so giá trị `cpu=` giữa hai lần dump để biết thread nào đang tăng.
- **Deadlock không gây CPU cao**: thread deadlock ở trạng thái `BLOCKED`, không tốn CPU. CPU cao kèm ứng dụng treo thì nghĩ tới vòng lặp hoặc spin, không phải deadlock.
- **GC thrashing**: heap gần đầy, JVM chạy GC liên tục. Collector [[stop-the-world|stop-the-world]] như Full GC dừng toàn bộ thread ứng dụng, nên throughput gần bằng 0 dù CPU 100%. Cần GC log (`-Xlog:gc*:file=gc.log:time,uptime`) và heap dump, không phải thread dump.
- **Safepoint bias**: một số profiler cũ chỉ lấy mẫu tại safepoint, nên đổ lỗi sai cho method gần safepoint. async-profiler dùng `perf_events`/`AsyncGetCallTrace` nên không bị lỗi này; trong container bị chặn `perf_events` thì dùng `-e itimer`.
- **JIT lúc khởi động**: `C2 CompilerThread0` nóng trong vài phút đầu sau deploy là bình thường. Chỉ đáng lo khi kéo dài.
- **Regex trong Java không có timeout và không phản hồi `interrupt()`**: một `Matcher.matches()` bị backtracking có thể chạy hàng phút. Cách phòng thủ: viết pattern không mơ hồ, giới hạn độ dài input trước khi match, dùng possessive quantifier (`++`) hoặc atomic group (`(?>...)`).
- **Busy-spin**: vòng `while (!done) {}` hoặc retry không `sleep`/backoff đốt trọn một core. Dùng `BlockingQueue`, `CompletableFuture`, `LockSupport.parkNanos` hoặc backoff có giới hạn.
