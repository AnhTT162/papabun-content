## Quick

[[thread-pool|Thread pool]] tái sử dụng một số thread cố định để chạy nhiều task, tránh tạo thread mới cho mỗi việc. Thứ tự của `ThreadPoolExecutor` là **core threads → queue → thread thêm tới `maximumPoolSize` → reject**: thread thêm chỉ được tạo khi queue đã đầy, nên **queue không giới hạn đồng nghĩa với `maximumPoolSize` vô dụng**.

## Interview

`ExecutorService` tách việc "nộp task" khỏi việc "chạy task bằng thread nào". Cài đặt chính là `ThreadPoolExecutor` với 5 tham số:

- **`corePoolSize`**: số thread giữ lại kể cả khi rảnh.
- **`maximumPoolSize`**: số thread tối đa.
- **`keepAliveTime`**: thread vượt core rảnh quá thời gian này thì bị huỷ.
- **`workQueue`**: hàng đợi task, ví dụ `ArrayBlockingQueue` (có giới hạn), `LinkedBlockingQueue` (mặc định không giới hạn), `SynchronousQueue` (không chứa gì, trao tay trực tiếp).
- **`RejectedExecutionHandler`**: xử lý task không nhận được.

Khi gọi `execute(task)`:
1. Số thread < `corePoolSize`: tạo thread mới, **kể cả khi có thread khác đang rảnh**.
2. Đủ core: đưa task vào queue.
3. Queue đầy và số thread < `maximumPoolSize`: tạo thread mới chạy ngay task này.
4. Đã tới max (hoặc pool đã shutdown): gọi rejection handler. Mặc định `AbortPolicy` ném `RejectedExecutionException`; `CallerRunsPolicy` bắt thread gọi tự chạy task, tạo [[backpressure]] tự nhiên.

Bẫy hay gặp: `Executors.newFixedThreadPool(n)` dùng `LinkedBlockingQueue` không giới hạn, khi tải tăng task dồn lên tới hết heap. `newCachedThreadPool()` có max là `Integer.MAX_VALUE` với `SynchronousQueue`, nên mỗi đợt tăng tải sinh hàng nghìn thread. Production nên tự tạo `ThreadPoolExecutor` với queue có giới hạn, rejection policy rõ ràng và `ThreadFactory` đặt tên thread.

Sizing: việc [[cpu-bound|CPU-bound]] dùng khoảng số core. Việc [[io-bound|IO-bound]] dùng `số core × (1 + thời gian chờ / thời gian tính)`, rồi kiểm tra lại bằng [[littles-law|Little's law]] và giới hạn của hệ thống phía sau.

Tắt pool: `shutdown()` ngừng nhận task mới nhưng chạy hết task đã nhận, `awaitTermination` chờ có thời hạn, quá hạn thì `shutdownNow()` để interrupt thread đang chạy.

Từ Java 21, [[virtual-thread|virtual thread]] thay đổi bài toán IO-bound: `Executors.newVirtualThreadPerTaskExecutor()` tạo một virtual thread cho mỗi task, không cần pool. Khi đó giới hạn đồng thời bằng `Semaphore`, không bằng kích thước pool.

## Deep

- **Core thread tạo lười**: pool mới tạo chưa có thread nào; `prestartAllCoreThreads()` tạo sẵn. `allowCoreThreadTimeOut(true)` cho core thread cũng bị huỷ khi rảnh.
- **`core < max` với queue lớn là cấu hình đánh lừa**: thread thêm chỉ xuất hiện khi queue đầy, lúc đó task trong queue đã chờ rất lâu. Nếu muốn mở rộng thread sớm, đặt core = max và dùng queue vừa đủ, hoặc dùng `SynchronousQueue`.
- **`execute` và `submit` khác nhau khi task ném exception**: `execute` để exception lên `UncaughtExceptionHandler`, thread worker chết và được thay. `submit` gói exception vào `Future`; không ai gọi `get()` thì lỗi biến mất không dấu vết.
- **`shutdownNow()`** interrupt các worker và trả về danh sách task chưa bắt đầu. Task không kiểm tra interrupt (vòng lặp tính toán, IO không phản hồi interrupt) vẫn chạy tiếp.
- **Java 19+**: `ExecutorService` là `AutoCloseable`; `close()` gọi `shutdown()` rồi chờ tới khi mọi task xong, nên dùng được với try-with-resources.
- **Virtual thread không làm CPU-bound nhanh hơn**: số carrier thread mặc định bằng số core. Đừng pool virtual thread, và đừng dùng chúng để giới hạn tài nguyên.
- **[[pinning|Pinning]]**: ở Java 21–23, virtual thread chặn bên trong `synchronized` sẽ giữ luôn carrier thread. JEP 491 (Java 24) bỏ hạn chế này với `synchronized`; native call vẫn pin.
- **Pool riêng cho từng downstream** (pattern [[bulkhead]]): một API chậm chỉ làm đầy pool của nó, không kéo theo cả service.
- **`ForkJoinPool.commonPool()`** dùng chung cho parallel stream và `CompletableFuture.*Async` mặc định; chạy IO blocking trên đó sẽ làm nghẽn mọi nơi khác.
