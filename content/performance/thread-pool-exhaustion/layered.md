## Quick

Request treo mà CPU gần 0 nghĩa là **thread không chạy mà đang chờ**. Chụp [[thread-dump|thread dump]] vài lần: phần lớn thread của [[thread-pool|pool]] đứng cùng một stack, và **khung đầu tiên không phải `park` hay `LockSupport` (ví dụ `FutureTask.get`, `HikariPool.getConnection`) chính là thứ chúng chờ**. Ba nguyên nhân hay gặp: chờ tài nguyên bên ngoài không có [[timeout|timeout]], chờ chính pool của mình ([[thread-starvation-deadlock|thread starvation deadlock]]), và một dependency chậm chiếm hết pool dùng chung vì thiếu [[bulkhead|bulkhead]].

## Interview

**Triệu chứng**: latency tăng vọt rồi request timeout hàng loạt, `tomcat.threads.busy` bằng `threads.max`, CPU thấp. Health check chạy chung pool với API nên cũng không trả lời, Kubernetes restart pod, và hiện trường mất theo.

**Đọc thread dump**: chụp 3 lần cách nhau vài giây, gom thread theo stack và đếm. Bỏ qua các khung `Unsafe.park`, `LockSupport` ở trên cùng; khung đầu tiên của thư viện hoặc code của bạn cho biết chúng chờ gì:
- `HikariPool.getConnection` chờ connection DB;
- `StrictConnPool` hay `PoolingHttpClientConnectionManager` chờ kết nối HTTP;
- `FutureTask.get` hoặc `CompletableFuture.join` chờ kết quả của một task khác;
- `BLOCKED` trên một monitor chờ khoá `synchronized`.

Thread đang đọc socket hiện `RUNNABLE` với khung trên cùng như `Net.poll` hay `SocketDispatcher.read0`, bên dưới là `NioSocketImpl.read`, dù thực ra nó đang chờ mạng: đừng tưởng nó đang tính toán.

**Thread starvation deadlock**: task trong pool gửi task con vào **cùng pool** rồi chặn chờ kết quả. Khi mọi thread đều là task cha đang chờ, task con nằm mãi trong hàng đợi. Không có khoá nào nên JVM không báo deadlock; hàng đợi chỉ dài ra.

**Cầm máu** (quy trình chung ở bài Quy trình điều tra sự cố): chụp thread dump trước, rồi cắt nguồn gây chờ (tắt tính năng, ngắt dependency), sau đó mới restart.

**Phòng ngừa**:
- Mọi chỗ chờ có timeout: `future.get(2, SECONDS)`, `orTimeout`, timeout của pool DB và HTTP client.
- Task cha và task con dùng pool khác nhau, hoặc nối bằng `thenCombine`, `allOf` thay vì chặn trong pool.
- Hàng đợi có giới hạn và [[rejection-policy|rejection policy]] rõ ràng, để quá tải thành lỗi nhanh thay vì treo.
- Bulkhead cho từng dependency, health check trên cổng quản trị riêng.
- Metric `executor.active`, `executor.queued` cho mọi pool tự tạo.

## Deep

- **Gom thread dump nhanh**: `jcmd <pid> Thread.print > dump-1.txt`, lặp 3 lần. Thread `WAITING` kiểu park đều có khung trên cùng là `Unsafe.park`, nên phải gom theo vài khung bên dưới nó (khung đầu tiên của thư viện hay code của bạn). Công cụ như fastThread hay IntelliJ cũng gom thread giống stack. Thread nào giữ nguyên một stack qua cả 3 lần là đang kẹt ở đó.
- **WAITING, TIMED_WAITING, BLOCKED**: `WAITING (parking)` là chờ không thời hạn (`get()`, `join()`, `take()`); `TIMED_WAITING` là chờ có hạn (`get(timeout)`, `sleep`, `poll(timeout)`), nên sớm muộn cũng thoát; `BLOCKED` chỉ dành cho monitor của `synchronized`. Thấy hàng trăm thread `WAITING` ở cùng chỗ là dấu hiệu thiếu timeout.
- **`jcmd` chỉ báo deadlock khoá**: thread dump in "Found one Java-level deadlock" khi có vòng chờ monitor hoặc `ReentrantLock` (bài [[deadlock|Deadlock]]). Starvation deadlock, [[pool-deadlock|pool deadlock]] của [[connection-pool|connection pool]] (bài Connection pool), hay chờ một `CompletableFuture` không bao giờ hoàn thành đều không được báo.
- **Executor mặc định của Spring Boot** (cũng ở bài @Async, @Scheduled & event): bean `applicationTaskExecutor` dùng cho `@Async` có 8 core thread, max và hàng đợi không giới hạn. Vì hàng đợi không bao giờ đầy, pool không bao giờ vượt 8 thread: task chậm làm hàng đợi dài vô hạn và bộ nhớ tăng dần. Đặt `spring.task.execution.pool.queue-capacity` và `max-size`, hoặc dùng executor riêng cho từng loại việc. Bật `spring.threads.virtual.enabled` (Boot 3.2+) thì Boot dùng `SimpleAsyncTaskExecutor` với virtual thread thay vào đó.
- **[[common-pool|Common pool]]**: `CompletableFuture.supplyAsync` không truyền executor và parallel stream dùng chung `ForkJoinPool.commonPool()` (số core trừ 1). Một lời gọi blocking trên đó làm chậm mọi nơi khác trong JVM (bài ExecutorService & Thread Pool và bài CompletableFuture).
- **[[virtual-thread|Virtual thread]]**: `jcmd <pid> Thread.print` chỉ in platform thread; virtual thread phải dump bằng `jcmd <pid> Thread.dump_to_file -format=json dump.json`. Virtual thread không cạn như pool 200 thread, nhưng vẫn cạn tài nguyên phía sau (DB pool) và có thể [[pinning|pin]] [[carrier-thread|carrier thread]]: trên JDK 21–23, chặn bên trong `synchronized` giữ luôn carrier, chỉ vài chục chỗ như vậy là đủ treo cả ứng dụng. JDK 24 (JEP 491) sửa phần `synchronized`; native frame và class initializer vẫn còn pin.
- **`CallerRunsPolicy`**: khi pool đầy, thread gửi task (thường là thread Tomcat) tự chạy task đó. Đó là [[backpressure|backpressure]] tự nhiên, nhưng biến thread xử lý request thành worker chậm; với task blocking lâu, Tomcat cạn thread theo.
- **Timeout ở ngoài không gỡ được thread ở trong**: `future.get(30, SECONDS)` trả thread Tomcat về, nhưng worker vẫn kẹt và task vẫn nằm trong hàng đợi. `future.cancel(true)` chỉ ngắt được code phản hồi `interrupt`; đọc socket chặn thì không. Phải có timeout ở tầng thấp nhất (socket, pool).
- **Health check riêng**: `management.server.port` đặt Actuator lên một server riêng với pool thread riêng, nên liveness probe ([[health-check|health check]]) không chết theo pool API. Liveness chỉ nên báo JVM còn sống; kiểm tra dependency thuộc về readiness, nếu không một DB chậm làm Kubernetes restart toàn bộ pod cùng lúc.
- **Cạn thread vì log hoặc lock**: appender log đồng bộ (bài Log cho production) hay `synchronized` quanh một lời gọi chậm tạo đúng hình ảnh này: hàng trăm thread chờ cùng một khoá, một thread đang giữ nó và làm việc chậm. Tìm thread đang giữ khoá (`- locked <0x...>`) thay vì nhìn đám đang chờ.
