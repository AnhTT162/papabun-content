## Quick

Một thread Java ở đúng một trong sáu trạng thái của `Thread.State`: `NEW`, `RUNNABLE`, `BLOCKED`, `WAITING`, `TIMED_WAITING`, `TERMINATED`. **`BLOCKED` chỉ là chờ [[monitor]] của `synchronized`; chờ `wait()`, `join()` hay `ReentrantLock` là `WAITING`/`TIMED_WAITING`.**

## Interview

`Thread.getState()` trả về một trong sáu giá trị:

- **NEW**: đã `new Thread(...)` nhưng chưa `start()`.
- **RUNNABLE**: đang chạy hoặc sẵn sàng chạy, chờ CPU. Java không phân biệt hai trường hợp này. Thread đang đọc socket chặn cũng thường hiện RUNNABLE.
- **BLOCKED**: chờ monitor để vào khối `synchronized`, hoặc để vào lại sau khi `wait()` được đánh thức.
- **WAITING**: chờ vô thời hạn: `Object.wait()`, `Thread.join()`, `LockSupport.park()`.
- **TIMED_WAITING**: như trên nhưng có thời hạn, cộng thêm `Thread.sleep(ms)`.
- **TERMINATED**: `run()` đã kết thúc.

Chuyển trạng thái quan trọng nhất là cặp `wait`/`notify`. `wait()` phải gọi trong `synchronized` trên cùng object, nó **nhả monitor** rồi chuyển sang WAITING. Thread khác gọi `notify()` (cũng trong `synchronized`) thì thread chờ được đánh thức, nhưng monitor vẫn đang bị người gọi `notify()` giữ, nên nó sang **BLOCKED**, lấy lại được monitor mới thành RUNNABLE và `wait()` mới trả về.

Bẫy hay gặp:
- `sleep()` **không nhả monitor**. Ngủ trong `synchronized` làm các thread khác BLOCKED.
- Thread chờ `ReentrantLock.lock()` hiện **WAITING** chứ không phải BLOCKED, vì lock trong `java.util.concurrent` dùng `LockSupport.park`. Đọc [[thread-dump|thread dump]] cần nhớ điều này.
- `wait()` có thể thức dậy mà không ai `notify` ([[spurious-wakeup|spurious wakeup]]), nên luôn gọi trong vòng `while (!condition)`, không dùng `if`.
- Gọi `run()` thay vì `start()` thì code chạy trên thread hiện tại. Gọi `start()` lần hai ném `IllegalThreadStateException`.

Muốn dừng một thread đang WAITING/TIMED_WAITING, dùng [[thread-interrupt|interrupt]]: `sleep`, `wait`, `join` thức dậy và ném `InterruptedException` (riêng `wait()` phải lấy lại monitor trước khi ném).

## Deep

- **RUNNABLE gộp nhiều thứ**: đang chạy, chờ CPU, và cả chờ IO trong native code. CPU cao nhưng thread dump toàn RUNNABLE ở `socketRead` thì chưa chắc là thread đang tính toán.
- **`getState()` chỉ để giám sát**: Javadoc nói rõ không dùng nó để đồng bộ, vì trạng thái có thể đổi ngay sau khi đọc.
- **`notify()` đánh thức một thread bất kỳ** trong số các thread đang `wait()` trên object đó, `notifyAll()` đánh thức tất cả; mọi thread được đánh thức phải tranh lại monitor. Dùng `notify()` khi các thread chờ những điều kiện khác nhau dễ đánh thức nhầm người và treo.
- **Interrupt**: `interrupt()` đặt cờ ngắt. Thread đang `sleep`/`wait`/`join` nhận `InterruptedException` và cờ bị xoá; bắt exception rồi nuốt mất là làm mất tín hiệu, nên gọi lại `Thread.currentThread().interrupt()`. Thread đang BLOCKED ở `synchronized` **không** phản hồi interrupt.
- **`wait(ms)` hết giờ** vẫn phải lấy lại monitor, nên có thể đi qua BLOCKED trước khi chạy tiếp. `sleep(ms)` hết giờ thì về RUNNABLE ngay.
- **Exception chưa bắt** trong `run()` làm thread TERMINATED và gọi `UncaughtExceptionHandler`, không ảnh hưởng thread khác.
- **[[virtual-thread|Virtual thread]] (Java 21+)** dùng cùng `Thread.State`. Một virtual thread đang chờ IO socket thường hiện WAITING thay vì RUNNABLE, vì nó được `park` và nhả carrier thread.
