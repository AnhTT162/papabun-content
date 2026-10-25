## Quick

[[producer-consumer|Producer–consumer]] tách bên tạo việc khỏi bên làm việc bằng một hàng đợi dùng chung: producer bỏ vào, consumer lấy ra, mỗi bên chạy theo tốc độ của mình. Trong Java dùng [[blocking-queue|`BlockingQueue`]]: `put()` chặn khi queue đầy, `take()` chặn khi queue rỗng, không thread nào phải [[busy-spin|quay vòng kiểm tra]]. **Queue phải có giới hạn**: queue đầy chặn producer lại, đó là [[backpressure]]. Queue không giới hạn chỉ dời lỗi sang chỗ khác: latency tăng dần rồi hết heap.

## Interview

**Tự viết bằng `wait`/`notify`** (câu hỏi phỏng vấn kinh điển):
```java
synchronized void put(T item) throws InterruptedException {
    while (items.size() == capacity) wait();
    items.add(item);
    notifyAll();
}
```
- Phải giữ [[monitor]] mới được gọi `wait`/`notify`, nếu không ném `IllegalMonitorStateException`. `wait()` nhả monitor của chính object đó trong lúc chờ (các monitor khác thread đang giữ vẫn bị giữ) và lấy lại trước khi trả về.
- Dùng `while`, không dùng `if`: thread có thể thức dậy khi điều kiện vẫn sai, do [[spurious-wakeup|spurious wakeup]] hoặc do consumer khác đã lấy mất phần tử.
- Producer và consumer chờ trên cùng một monitor. `notify()` đánh thức một thread bất kỳ, có thể cùng loại (consumer đánh thức consumer); thread đó thấy điều kiện vẫn sai và chờ tiếp, còn thread cần được gọi thì không ai gọi, tới khi mọi thread cùng chờ. Dùng `notifyAll()`, hoặc `ReentrantLock` với hai [[condition-variable|`Condition`]] `notFull`/`notEmpty` như `ArrayBlockingQueue`.

**Bốn kiểu method của `BlockingQueue`**:

- Ném exception khi không làm được: `add`, `remove`.
- Trả giá trị đặc biệt: `offer` trả `false`, `poll` trả `null`.
- Chặn tới khi làm được: `put`, `take`.
- Chặn có giới hạn thời gian: `offer(e, timeout, unit)`, `poll(timeout, unit)`.

Không chứa được `null` (`NullPointerException`), vì `poll` dùng `null` để báo rỗng.

**Chọn cài đặt**:
- `ArrayBlockingQueue(n)`: có giới hạn, mảng cấp sẵn, một lock cho cả hai đầu; `ArrayBlockingQueue(n, true)` cho thread chờ lâu nhất đi trước, đổi lại thông lượng thấp hơn.
- `LinkedBlockingQueue`: hai lock riêng cho đầu thêm và đầu lấy nên ít tranh chấp hơn, nhưng mỗi phần tử cấp thêm một node (thêm việc cho GC); **không truyền capacity thì giới hạn là `Integer.MAX_VALUE`**.
- `SynchronousQueue`: không chứa gì, `put` chờ tới khi có `take` nhận.
- `PriorityBlockingQueue`, `DelayQueue`: không giới hạn, `put` không bao giờ chặn.

**Dừng consumer**: gửi [[poison-pill|poison pill]] (một object đánh dấu, mỗi consumer một cái) để consumer xử lý nốt việc rồi thoát, hoặc [[thread-interrupt|interrupt]] khi muốn dừng ngay.

## Deep

- **[[bounded-queue|Queue có giới hạn]]: chọn cách phản ứng khi đầy**:
  - Chặn (`put`): producer chậm lại theo consumer. Hợp với job nền.
  - Chặn có hạn (`offer` có timeout): quá hạn thì báo lỗi lên trên, ví dụ trả 503 cho client.
  - Bỏ (`offer` trả `false`): chấp nhận mất, chỉ dùng cho dữ liệu như metric hay log, và phải đếm số lần bỏ.
- **Kích thước queue là thời gian chờ**: queue chứa 10.000 việc, consumer xử lý 500 việc mỗi giây thì việc mới vào chờ khoảng 20 giây ([[littles-law|Little's Law]]). Đặt giới hạn theo thời gian chờ chấp nhận được, không theo "càng lớn càng an toàn".
- **`ThreadPoolExecutor` chính là producer–consumer**: `execute()` dùng `offer` chứ không `put`, nên queue đầy thì không chặn mà tạo thêm thread hoặc reject. Muốn bên gửi chậm lại thì dùng [[rejection-policy|`CallerRunsPolicy`]] (bài ExecutorService & Thread Pool, [[work-queue|work queue]]). `ThreadPoolTaskExecutor` của Spring (dùng cho `@Async`) mặc định `queue-capacity` là `Integer.MAX_VALUE`: cùng cái bẫy queue không giới hạn.
- **Poison pill chi tiết**:
  - N consumer cần N pill, hoặc consumer nhận pill thì `put` lại pill trước khi thoát để consumer khác cũng thấy.
  - Nhiều producer: chỉ gửi pill khi producer **cuối cùng** xong (đếm bằng `CountDownLatch` hoặc `AtomicInteger`), nếu không pill đứng trước việc của producer chậm hơn.
  - Producer gửi tiếp sau khi consumer đã dừng sẽ làm đầy queue rồi kẹt ở `put` mãi mãi.
- **Interrupt**:
  - `take()` và `put()` ném `InterruptedException` khi thread bị interrupt; `ExecutorService.shutdownNow()` interrupt mọi worker.
  - Bắt exception thì thoát vòng lặp và gọi lại `Thread.currentThread().interrupt()` để bên ngoài biết; nuốt nó trong `while (true)` làm thread không bao giờ dừng.
  - Interrupt dừng ngay nên việc còn trong queue bị bỏ lại. Muốn xử lý hết thì gửi pill (hoặc dùng cờ dừng kết hợp `poll(timeout)`), rồi mới `shutdown()` và `awaitTermination`. `shutdown()` một mình chỉ dọn work queue của executor, không dừng được consumer đang `take()` trên queue của bạn.
- **Consumer chết âm thầm**: exception không bắt trong vòng lặp làm thread kết thúc. Queue đầy dần, producer bị chặn, và log chỉ có một stack trace từ lâu; chạy consumer bằng `executor.submit()` thì exception nằm trong `Future` không ai đọc, log không có gì. Bắt exception cho từng phần tử, ghi log, đưa phần tử hỏng ra chỗ riêng (giống [[dead-letter-queue|DLQ]]) rồi lấy tiếp.
- **Gom lô bằng `drainTo`**: `take()` chờ phần tử đầu, rồi `queue.drainTo(batch, 499)` lấy thêm những gì đang có mà không chờ. Hợp để ghi database bằng JDBC batch: tải thấp thì lô nhỏ và nhanh, tải cao thì lô lớn.
- **`size()` chỉ là ảnh chụp**: `if (queue.size() < limit) queue.put(x)` là check-then-act (bài Race condition, atomicity & thread-safe). Dùng giới hạn của chính queue. `remainingCapacity()` cũng chỉ đúng ở thời điểm gọi.
- **Queue trong bộ nhớ mất dữ liệu khi tiến trình dừng**: deploy, OOM hay `kill -9` làm mất mọi thứ còn trong queue. Việc không được mất phải đi qua nơi bền vững như Kafka, RabbitMQ hay [[outbox|bảng outbox]]; queue trong bộ nhớ chỉ để tách nhịp giữa các thread trong một tiến trình. Khi shutdown có kiểm soát, ngừng nhận việc mới rồi xử lý nốt queue.
- **Virtual thread**: `BlockingQueue` dùng lock của `java.util.concurrent`, nên virtual thread chờ ở `take()` không giữ carrier thread. Bản tự viết bằng `synchronized` + `wait()` từng [[pinning|ghim (pin)]] carrier thread trước JDK 24 ([[virtual-thread|virtual thread]], JEP 491).
- **Khi cần hơn `BlockingQueue`**: `LinkedTransferQueue.transfer()` chờ tới khi consumer nhận; LMAX Disruptor dùng ring buffer không khoá cho độ trễ cực thấp. Hầu hết ứng dụng nghiệp vụ không cần tới.
