## Quick

[[virtual-thread|Virtual thread]] (Java 21, JEP 444) là `Thread` do JVM lập lịch trên một nhóm nhỏ [[carrier-thread|carrier thread]]. Khi nó block ở chỗ JDK hỗ trợ (socket, `sleep`, lock của `java.util.concurrent`), stack được chép ra heap và carrier đi chạy virtual thread khác. **Virtual thread tăng số việc chờ I/O chạy đồng thời, không làm việc tính toán nhanh hơn; nó không bị ngắt theo thời gian, và không thay được việc giới hạn tài nguyên.**

## Interview

Tạo bằng `Thread.ofVirtual().start(task)` hoặc `Executors.newVirtualThreadPerTaskExecutor()`; Spring Boot 3.2+ bật bằng `spring.threads.virtual.enabled=true`. Mỗi virtual thread bọc một [[continuation]]. Scheduler mặc định là một `ForkJoinPool` riêng (không phải common pool), chạy FIFO, số carrier bằng số core.

Khi virtual thread gọi một thao tác blocking mà JDK đã viết lại, ví dụ đọc socket chưa có dữ liệu, nó tự **unmount**: các frame được chép thành một object trên heap, socket được đăng ký với poller của JDK, carrier rảnh. Dữ liệu tới thì poller đưa virtual thread trở lại hàng đợi, nó **mount** lại, có thể trên carrier khác, và chạy tiếp như chưa có gì xảy ra. Vì vậy code blocking tuần tự vẫn đạt throughput như code bất đồng bộ.

Lợi ích đến từ [[littles-law|Little's law]]: throughput = số việc đồng thời / thời gian mỗi việc. Request chờ database 50 ms thì cần nhiều thread đồng thời, và platform thread (mỗi cái một thread của hệ điều hành, stack dự trữ cỡ 1 MB) đắt; virtual thread nhàn rỗi chỉ tốn vài trăm byte đến vài KB heap.

[[pinning|Pinning]] là khi virtual thread block mà không unmount được, nên giữ luôn carrier: bên trong `synchronized` hoặc `Object.wait()` ở Java 21–23 (JEP 491 của Java 24 gỡ bỏ), trong native code, trong class initializer. Phát hiện bằng JFR event `jdk.VirtualThreadPinned`.

Khi nào không dùng:
- Việc CPU-bound: số carrier vẫn bằng số core, và virtual thread chỉ nhả carrier khi block.
- Làm bộ giới hạn: pool 20 thread từng ngầm giới hạn 20 truy vấn; với virtual thread phải dùng `Semaphore` hoặc bulkhead.
- Cache object đắt trong `ThreadLocal`: một triệu thread là một triệu bản.

## Deep

- **Không có time slicing**: JEP 444 ghi rõ scheduler hiện không chia thời gian. Một vòng tính toán dài giữ carrier tới khi xong; đủ số job như vậy bằng số carrier thì mọi virtual thread khác, kể cả health check, phải chờ (xem lab). Việc CPU-bound nên chạy trên pool platform thread có giới hạn, nơi hệ điều hành chia thời gian.
- **Stack nằm trên heap**: khi unmount, các frame được chép thành object stack chunk, GC quét như mọi object. Stack sâu (framework nhiều tầng, đệ quy) làm mỗi virtual thread tốn hơn; một triệu virtual thread nhàn rỗi vẫn có thể cần vài GB heap. Mount lại chỉ chép vài frame trên cùng, phần còn lại chép dần khi cần.
- **Tham số scheduler**: `-Djdk.virtualThreadScheduler.parallelism` (mặc định số core, theo cgroup khi chạy container) và `maxPoolSize` (mặc định `max(parallelism, 256)`). Số carrier chỉ vượt `parallelism` khi JVM bù cho thao tác chặn carrier. Java 21–22 bù cho đọc/ghi file và `Object.wait()`. Từ JDK 23 (JDK-8329593), đọc/ghi file thường vẫn chặn carrier nhưng **không còn được bù**; chỉ còn bù cho direct I/O, ghi `O_SYNC`, `force`/`sync`, tra DNS, `Process.waitFor`. Vì vậy trên JDK 23+, nhiều virtual thread cùng đọc file thật sự chiếm hết carrier.
- **Pinning theo phiên bản**: Java 21–23 ghim khi block trong `synchronized` hoặc `Object.wait()`, và có cờ `-Djdk.tracePinnedThreads=full` in stack lúc bị ghim. Java 24 (JEP 491) cho virtual thread unmount cả trong `synchronized`, đồng thời bỏ cờ đó; vẫn ghim khi block trong native method hay foreign function, trong `static {}` của class, hoặc khi chờ class khác khởi tạo xong. JFR event `jdk.VirtualThreadPinned` (ngưỡng mặc định 20 ms) dùng được ở mọi bản.
- **Bẫy khi chuyển sang virtual thread trên Java 21**: thư viện cũ bọc I/O trong `synchronized` (driver JDBC, HTTP client đời cũ, logging appender) ghim carrier. Với 8 core, 8 request cùng vào hoặc chờ vào khối đó (ở Java 21–23, chờ monitor cũng ghim) là cả ứng dụng đứng. Nâng thư viện lên bản đã đổi sang `ReentrantLock`, hoặc lên Java 24+.
- **Thuộc tính khác platform thread**: luôn là daemon, `setPriority` không có tác dụng, không đổi được thread group, tên mặc định rỗng (đặt bằng `Thread.ofVirtual().name("req-", 0)`). `Thread.currentThread()` trả về chính virtual thread, carrier bị ẩn.
- **Quan sát**: `jstack` chỉ thấy carrier thread. Xem virtual thread bằng `jcmd <pid> Thread.dump_to_file -format=json dump.json`; JFR có thêm `jdk.VirtualThreadStart`, `jdk.VirtualThreadEnd` (tắt mặc định vì tốn khi có hàng triệu thread) và `jdk.VirtualThreadSubmitFailed` (bật sẵn, cùng `jdk.VirtualThreadPinned`).
- **Đừng gom virtual thread vào pool**: tạo mới cho mỗi task là cách dùng đúng. `newFixedThreadPool(200, Thread.ofVirtual().factory())` vừa mất lợi ích vừa giữ giới hạn sai chỗ. Giới hạn đặt ở tài nguyên: `Semaphore`, pool connection, rate limiter.
- **`ExecutorService` là `AutoCloseable`** (Java 19+): `try (var executor = Executors.newVirtualThreadPerTaskExecutor()) { ... }` chờ mọi task xong khi ra khỏi khối. 100.000 task, mỗi task `sleep(1000)`, xong trong khoảng 1,3 giây kể cả khi chỉ có 2 carrier.
- **[[structured-concurrency|Structured concurrency]]**: `StructuredTaskScope` cho các task con chạy trên virtual thread trong một phạm vi, lỗi một task thì huỷ các task còn lại, và thread dump hiện cây cha con. API vẫn là preview tới JDK 27 (cần `--enable-preview`) và đã đổi đáng kể ở JDK 25 (JEP 505, `StructuredTaskScope.open(...)` với `Joiner`). Đi cùng là [[scoped-value|`ScopedValue`]] (chính thức từ JDK 25) thay `ThreadLocal` để truyền context xuống task con.
- **So với reactive**: virtual thread giải quyết cùng bài toán "nhiều việc chờ I/O" mà không phải viết chuỗi callback hay `Mono`/`Flux`, stack trace và debug như code thường. Reactive vẫn có lợi thế ở backpressure và streaming; bài Reactive programming & Project Reactor so sánh chi tiết.
