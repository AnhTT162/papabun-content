## Quick

[[deadlock|Deadlock]] là khi một nhóm thread chờ nhau theo vòng tròn, mỗi thread giữ một lock mà thread tiếp theo cần, nên không ai chạy tiếp được. **Cách phòng hiệu quả nhất: mọi thread lấy nhiều lock theo cùng một thứ tự cố định ([[lock-ordering|lock ordering]]).**

## Interview

Deadlock chỉ xảy ra khi có đủ bốn [[coffman-conditions|điều kiện Coffman]]:
1. **Mutual exclusion**: tài nguyên chỉ một thread giữ được (lock).
2. **Hold and wait**: thread giữ lock này trong khi chờ lock khác.
3. **No preemption**: không ai giật được lock khỏi thread đang giữ.
4. **Circular wait**: các thread chờ nhau thành vòng.

Phá một điều kiện là hết deadlock:
- **Lock ordering** phá circular wait. Ví dụ chuyển tiền: luôn khoá tài khoản có `id` nhỏ hơn trước, bất kể chuyển chiều nào.
- **`tryLock` có timeout** (`ReentrantLock.tryLock(100, MILLISECONDS)`) phá hold-and-wait: không lấy được lock thứ hai thì nhả lock thứ nhất, chờ ngẫu nhiên một chút rồi thử lại.
- **Thu nhỏ vùng khoá**: không gọi code lạ (callback, listener, method có thể khoá thứ khác) khi đang giữ lock.

Phát hiện: lấy [[thread-dump|thread dump]] bằng `jstack <pid>` hoặc `jcmd <pid> Thread.print`. JVM tự phân tích và in `Found one Java-level deadlock:` kèm thread nào giữ lock nào và chờ lock nào. Trong code, `ThreadMXBean.findDeadlockedThreads()` trả về id các thread kẹt, dùng cho health check hoặc watchdog.

JVM **không tự gỡ** deadlock: thread kẹt mãi. `interrupt()` không giải được thread chờ `synchronized` hay `lock()`. Trên production thường chỉ còn cách restart, nên phải phòng từ thiết kế.

Hai họ hàng: [[livelock]] là các thread vẫn chạy, liên tục nhường nhau nhưng không tiến lên được (hai thread cùng `tryLock` thất bại, cùng nhả, cùng thử lại đúng nhịp). [[starvation|Starvation]] là một thread mãi không tới lượt vì thread khác luôn giành được tài nguyên.

## Deep

- **Thread dump khác nhau theo loại lock**: deadlock trên `synchronized` thì thread ở `BLOCKED` với dòng `waiting to lock <0x...>`. Deadlock trên `ReentrantLock` thì thread ở `WAITING (parking)` với `parking to wait for <0x...> (a java.util.concurrent.locks.ReentrantLock$NonfairSync)`; JVM vẫn phát hiện được và in `waiting for ownable synchronizer` trong phần deadlock.
- **`findDeadlockedThreads()` và `findMonitorDeadlockedThreads()`**: cái đầu (Java 6+) tìm cả monitor lẫn `ownable synchronizer` như `ReentrantLock`; cái sau chỉ tìm monitor của `synchronized`, nên bỏ sót deadlock trên `ReentrantLock`. Cả hai trả về `null` khi không có deadlock.
- **Không có `id` tự nhiên để sắp thứ tự**: có thể dùng `System.identityHashCode`, nhưng hai object có thể trùng giá trị đó, nên khi trùng phải khoá thêm một "tie lock" chung trước.
- **`lockInterruptibly()`** cho phép interrupt thread đang chờ lock; `lock()` và `synchronized` thì không.
- **Backoff ngẫu nhiên** khi `tryLock` thất bại để tránh livelock: nếu mọi thread chờ đúng cùng một khoảng thời gian rồi thử lại, chúng có thể va nhau mãi.
- **[[thread-starvation-deadlock|Thread-starvation deadlock]]** không cần lock: task chạy trong một pool cố định gọi `future.get()` chờ task con nộp vào **cùng pool**; khi mọi thread đều đang chờ task con thì không còn thread nào chạy task con.
- **Starvation**: `ReentrantLock` mặc định không công bằng (thread mới tới có thể chen lên). `new ReentrantLock(true)` ưu tiên thread chờ lâu nhất, giảm starvation nhưng throughput thấp hơn.
- **Database cũng deadlock** khi hai transaction khoá các dòng theo thứ tự ngược nhau. Khác JVM, database tự phát hiện và huỷ một transaction, ứng dụng phải bắt lỗi và thử lại. Cách phòng giống nhau: cập nhật các dòng theo thứ tự cố định.
