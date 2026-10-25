## Quick

`@Async` chạy method trên **thread pool khác** qua proxy; `@Scheduled` chạy job định kỳ trên **scheduler mặc định chỉ có một thread**; `@EventListener` mặc định **đồng bộ**, chạy trên cùng thread và trong cùng transaction với bên publish. **Đổi thread là mất transaction, SecurityContext và MDC**, và chạy nhiều instance là mọi job `@Scheduled` chạy trên mọi pod.

## Interview

**`@Async`**:
- Cần `@EnableAsync`. Lời gọi qua proxy được đẩy vào `TaskExecutor` và trả về ngay. Gọi qua `this` thì vẫn chạy đồng bộ.
- Boot tạo sẵn `applicationTaskExecutor` (`ThreadPoolTaskExecutor`): 8 core thread, queue **không giới hạn**, nên thực tế không bao giờ quá 8 thread và queue có thể phình tới hết heap. Đặt `spring.task.execution.pool.queue-capacity` và `max-size`, hoặc khai báo executor riêng cho từng loại việc. Lưu ý: khai báo bất kỳ bean `Executor` nào là Boot gỡ executor mặc định; chỉ định rõ bằng `@Async("tên-bean")`, `AsyncConfigurer`, hoặc `spring.task.execution.mode=force` (Boot 3.5+) để giữ nó.
- Method `void` ném exception thì chỉ tới `AsyncUncaughtExceptionHandler` (mặc định chỉ log). Trả `CompletableFuture` để caller xử lý kết quả và lỗi.

**`@Scheduled`**:
- Cần `@EnableScheduling`. Boot cấu hình scheduler với **pool size 1**: một job chạy 5 phút làm mọi job khác trễ 5 phút (xem lab). Tăng `spring.task.scheduling.pool.size`, hoặc đẩy việc nặng sang executor.
- `fixedRate` tính từ lúc bắt đầu lần trước, `fixedDelay` từ lúc kết thúc lần trước. Với scheduler pool mặc định, cùng một job không chạy chồng lên chính nó; lỡ lịch thì `fixedRate` chạy bù dồn dập mọi lần đã lỡ (xem lab).
- Chạy 5 pod là job chạy 5 lần. Dùng khoá phân tán (ShedLock), leader election, hoặc chuyển sang batch hay queue.

**Event**:
- `publishEvent()` gọi các `@EventListener` ngay trên thread hiện tại. Listener ném exception thì exception đi ngược về bên publish và có thể rollback transaction của nó.
- Thêm `@Async` để listener chạy riêng.
- [[transactional-event-listener|`@TransactionalEventListener`]] (mặc định `AFTER_COMMIT`) chỉ chạy sau khi transaction commit, hợp để gửi email hay đẩy message mà không gửi nhầm khi rollback.
- Event trong bộ nhớ mất khi process chết, nên việc bắt buộc phải xảy ra cần [[outbox]].

## Deep

- **Truyền context sang thread khác**: dùng `TaskDecorator` trên executor để copy MDC, `SecurityContext` hay locale. Spring Security có `DelegatingSecurityContextAsyncTaskExecutor`. Boot áp các bean `TaskDecorator` cho executor và scheduler nó tạo (Boot 4 gộp nhiều bean theo `@Order`). Trace id và MDC qua Micrometer không tự đi theo: cần `spring.task.execution.propagate-context=true` hoặc tự khai báo `ContextPropagatingTaskDecorator`.
- **Không có Boot**: nếu context không có bean `TaskExecutor` duy nhất hay bean tên `taskExecutor`, Spring Framework thuần dùng `SimpleAsyncTaskExecutor` cho `@Async`, mỗi task một thread mới không giới hạn. Đây là lý do nhiều ứng dụng cũ sập vì hết thread khi tải tăng.
- **Virtual thread**: với `spring.threads.virtual.enabled=true` (Boot 3.2+), executor của `@Async` và scheduler dùng virtual thread. Hết giới hạn thread nhưng không có giới hạn đồng thời: đặt `spring.task.execution.simple.concurrency-limit`, và chặn cả ở tài nguyên phía sau (connection pool, API đối tác). Scheduler khi đó chạy mỗi lần `fixedRate` hay cron trên một thread mới, nên các lần chạy **có thể chồng nhau**; chỉ `fixedDelay` còn giữ tuần tự.
- **Exception trong `@Scheduled`**: được log rồi lịch vẫn tiếp tục. Job lỗi liên tục có thể không ai biết nếu chỉ có log; cần metric (Spring 6.1 / Boot 3.2+ có observation `tasks.scheduled.execution`) và cảnh báo.
- **Cron**: thêm `zone = "Asia/Ho_Chi_Minh"` khi lịch theo giờ địa phương; mặc định theo múi giờ của server, vốn thường là UTC trong container.
- **`@TransactionalEventListener` không có transaction**: publish ngoài transaction thì listener **không chạy**, trừ khi `fallbackExecution = true`. Đây là lỗi im lặng hay gặp khi bỏ `@Transactional` khỏi method publish.
- **Ghi database trong listener `AFTER_COMMIT`**: transaction gốc đã commit, thay đổi mới không được commit nếu không mở transaction riêng. Từ Spring 6.1, listener này nếu có `@Transactional` thì bắt buộc là `REQUIRES_NEW` hoặc `NOT_SUPPORTED`, nếu không thì khởi động lỗi (chi tiết ở bài @Transactional chuyên sâu).
- **Thứ tự listener**: dùng `@Order`. Listener đồng bộ chạy lần lượt, nên một listener chậm làm chậm request publish.
- **Shutdown**: mặc định task đang chạy bị interrupt và queue bị xoá khi ứng dụng dừng. Bật `spring.task.execution.shutdown.await-termination=true` thì executor chạy hết cả queue, giới hạn bởi `await-termination-period`; task vẫn mất nếu pod bị SIGKILL trước khi xong.
- **`@Async` không thay được queue**: task nằm trong bộ nhớ, mất khi deploy hay pod chết, không retry, không thấy được độ trễ. Việc phải chắc chắn chạy (gửi hoá đơn, đồng bộ đối tác) nên đi qua message queue hoặc bảng job trong database.
