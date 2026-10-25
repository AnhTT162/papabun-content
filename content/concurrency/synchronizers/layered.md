## Quick

`java.util.concurrent` có sẵn các công cụ phối hợp thread, mỗi cái cho một câu hỏi khác nhau:
- [[count-down-latch|`CountDownLatch`]]: "chờ tới khi N việc xong". Dùng một lần.
- [[semaphore|`Semaphore`]]: "tối đa N việc chạy cùng lúc".
- [[cyclic-barrier|`CyclicBarrier`]]: "N thread chờ nhau tới đủ rồi cùng đi tiếp", dùng lại được cho nhiều vòng.
- [[phaser|`Phaser`]]: như barrier nhưng số thread tham gia thay đổi được.

Chọn sai công cụ, hoặc quên trả lại (`countDown`, `release`) trong `finally`, là thread chờ mãi hoặc giới hạn bị phá.

## Interview

**`CountDownLatch(n)`**:
- `countDown()` giảm bộ đếm và không bao giờ chặn; `await()` chặn tới khi bộ đếm về 0.
- Không đặt lại được: muốn dùng nhiều vòng thì dùng `CyclicBarrier` hoặc tạo latch mới.
- Bẫy: một worker ném exception trước `countDown()` thì `await()` chờ mãi. Đặt `countDown()` trong `finally` và dùng `await(timeout, unit)`, kiểm tra giá trị `boolean` trả về.

**`Semaphore(n)`**:
- `acquire()` lấy một permit, hết thì chặn; `release()` trả permit.
- Permit không gắn với thread: `release()` khi chưa `acquire` sẽ **tăng** số permit vượt `n`. Chỉ `release` khi đã lấy được.
- Dùng giới hạn số lời gọi đồng thời tới một downstream ([[bulkhead]]), hoặc giới hạn tài nguyên khi chạy [[virtual-thread|virtual thread]]: đừng gom virtual thread vào pool, hãy giới hạn bằng semaphore.

**`CyclicBarrier(n, action)`**:
- N thread gọi `await()`; thread tới cuối cùng chạy `action` rồi cả nhóm cùng đi tiếp, và barrier tự đặt lại cho vòng sau.
- Một thread bị [[thread-interrupt|interrupt]] hoặc hết timeout thì barrier **vỡ**: thread đó nhận `InterruptedException` (hoặc `TimeoutException`), các thread khác đang chờ và mọi lần `await()` sau đó tới khi `reset()` nhận `BrokenBarrierException`.

**`Phaser`**: thread đăng ký (`register`) và rời (`arriveAndDeregister`) lúc đang chạy, qua nhiều pha đánh số; hợp khi số bên tham gia không cố định.

**Thường không cần tới chúng**: chờ một nhóm task trả kết quả thì `invokeAll` hoặc `CompletableFuture.allOf` gọn hơn latch. Giới hạn đồng thời giữa nhiều pod thì semaphore trong JVM không đủ, cần [[rate-limiting|rate limit]] dùng chung (Redis, gateway).

## Deep

- **Bên trong**:
  - `CountDownLatch` và `Semaphore` dựng trên [[aqs|AQS]] (`AbstractQueuedSynchronizer`) ở chế độ chia sẻ: state là bộ đếm, thread chờ xếp trong hàng đợi của AQS (bài Lock & AQS).
  - `CyclicBarrier` dùng `ReentrantLock` với một `Condition`.
  - `Phaser` tự quản lý state trong một `long` và không dùng AQS; tối đa 65.535 bên tham gia mỗi phaser, nhiều hơn thì ghép phaser thành cây.
- **Đảm bảo bộ nhớ**: mọi thứ một thread làm trước `countDown()` [[happens-before]] mọi thứ sau khi `await()` của thread khác trả về. Tương tự với `release()` và `acquire()` thành công. Nhờ đó kết quả worker ghi vào field thường vẫn thấy được sau `await()`.
- **Latch trong test**: một latch `start` với bộ đếm 1 giữ mọi worker ở vạch xuất phát rồi thả cùng lúc, làm race condition dễ lộ hơn; một latch `done` chờ chúng xong. Đây vẫn chưa phải cách chứng minh code đúng (bài Kiểm thử code đồng thời).
- **Semaphore chi tiết**:
  - Mẫu an toàn: `permits.acquire(); try { ... } finally { permits.release(); }`, với `acquire` nằm **ngoài** `try`. Không muốn chờ: `if (!permits.tryAcquire(200, MILLISECONDS)) throw new TooBusyException();`.
  - `acquire()` ném `InterruptedException`; `acquireUninterruptibly()` thì không, nên `shutdownNow()` không kéo được thread ra khỏi chỗ chờ (cờ interrupt vẫn được giữ lại).
  - Fair (`new Semaphore(n, true)`) cấp permit theo thứ tự chờ, chống bỏ đói nhưng chậm hơn. `tryAcquire()` không có timeout luôn lấy ngay nếu còn permit, kể cả trên semaphore fair; `tryAcquire(0, SECONDS)` thì tôn trọng thứ tự.
  - `acquire(k)` lấy nhiều permit một lúc, hợp để giới hạn theo "khối lượng" (số MB đang xử lý) thay vì số request.
  - Semaphore 1 permit trông giống lock nhưng không phải: không reentrant và thread khác `release` được.
  - Bulkhead kiểu semaphore của Resilience4j chính là cách này; bulkhead kiểu thread pool thì tách hẳn sang pool riêng.
- **Virtual thread**: JEP 444 khuyên không gom virtual thread vào pool. Pool 20 thread từng ngầm giới hạn 20 truy vấn đồng thời tới database; chuyển sang virtual thread mà không thêm `Semaphore(20)` thì giới hạn đó biến mất, và pool connection hay downstream phải gánh. `Semaphore` không ghim carrier thread.
- **`CyclicBarrier` chi tiết**:
  - `await()` trả về chỉ số thứ tự tới (0 là thread tới sau cùng).
  - Barrier action ném exception thì barrier vỡ. Sau khi vỡ phải `reset()` mới dùng lại được, và `reset()` lúc còn thread chờ làm chúng nhận `BrokenBarrierException`.
  - Phù hợp cho tính toán chia lưới, mô phỏng theo bước: mỗi vòng mọi thread tính phần mình, chờ nhau, rồi sang vòng sau.
- **`Phaser` chi tiết**: `arrive()` báo đã tới mà không chờ, `arriveAndAwaitAdvance()` báo tới và chờ cả nhóm. `onAdvance(phase, parties)` mặc định kết thúc phaser khi không còn ai đăng ký; override để kết thúc sớm hơn, ví dụ sau đủ số vòng.
- **`Exchanger`**: hai thread trao đổi object tại một điểm hẹn, như đổi bộ đệm đầy lấy bộ đệm rỗng. Hiếm gặp trong code nghiệp vụ.
- **Thay thế hiện đại**:
  - `ExecutorService.invokeAll(tasks)` trả danh sách `Future` khi mọi task xong.
  - `CompletableFuture.allOf(...)` ghép kết quả không chặn thread (bài CompletableFuture).
  - [[structured-concurrency|Structured concurrency]] (`StructuredTaskScope`, vẫn là preview ở JDK 25, JEP 505) chạy các task con trong một phạm vi: một task lỗi thì huỷ các task còn lại, và không task nào sống lâu hơn phạm vi.
- **Chỉ trong một JVM**: mọi công cụ ở đây chỉ phối hợp thread trong một tiến trình. Ba pod mỗi pod `Semaphore(10)` là 30 lời gọi đồng thời tới đối tác. Giới hạn chung phải đặt ở chỗ dùng chung: rate limiter ở gateway, counter trong Redis, hoặc chia hạn mức theo số pod.
- **Semaphore không phải rate limiter**: semaphore giới hạn số lời gọi **đang chạy cùng lúc**, rate limiter (`RateLimiter` của Resilience4j hay Guava) giới hạn số lời gọi **mỗi giây**. Đối tác trả 429 thường là vượt tốc độ; 20 lời gọi đồng thời mỗi cái 50ms vẫn là 400 lời gọi mỗi giây.
