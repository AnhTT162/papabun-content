## Quick

`ForkJoinPool` chạy các task tự chia nhỏ đệ quy. Mỗi worker có một deque riêng: tự lấy việc ở đầu deque của mình, hết việc thì sang lấy ([[work-stealing|steal]]) từ đáy deque của worker khác. [[parallel-stream|Parallel stream]] và `CompletableFuture.*Async` không truyền executor đều chạy trên [[common-pool|common pool]], dùng chung cho cả JVM. **Đừng block trong common pool, và parallel stream chỉ nhanh hơn khi dữ liệu lớn, chia đều được, và mỗi phần tử tốn đủ CPU.**

## Interview

Mẫu fork/join: một `RecursiveTask` nhỏ hơn ngưỡng thì tính thẳng; lớn hơn thì chia đôi, `fork()` một nửa (đẩy vào deque của worker hiện tại), tự `compute()` nửa kia, rồi `join()` nửa đã fork. `join()` không chặn ngay: nếu task chưa xong, worker tìm việc để làm trong lúc chờ (chạy chính task đó nếu chưa ai lấy, hoặc giúp worker đã steal nó); chỉ khi không giúp được mới chặn, và pool có thể thêm thread bù.

Work stealing: chủ deque đẩy và lấy ở đầu (LIFO), nên làm tiếp task con nhỏ, dữ liệu còn nóng trong cache. Worker rảnh lấy ở đáy (FIFO), tức là task cũ nhất và thường lớn nhất, nên một lần steal mang về nhiều việc và hai bên ít khi đụng nhau.

Common pool có số worker bằng số core trừ một, vì thread gọi cũng tham gia: parallel stream chạy một phần trên chính thread gọi nó. Ngoài parallel stream, nó còn chạy `CompletableFuture.supplyAsync` không truyền executor, `Arrays.parallelSort` và bulk operation của `ConcurrentHashMap`.

Parallel stream dùng [[spliterator]] để chia nguồn. Mảng, `ArrayList`, `IntStream.range` chia đôi chính xác; `LinkedList`, `Stream.iterate`, `BufferedReader.lines()` chia kém. Thao tác cần giữ thứ tự (`limit` hay `distinct` trên stream có thứ tự, `forEachOrdered`) và boxing làm mất phần lợi. Quy tắc ước lượng: số phần tử N nhân chi phí mỗi phần tử Q phải lớn (cỡ vài chục nghìn phép tính đơn giản trở lên) mới đáng chia.

Bẫy hay gặp:
- Gọi HTTP hay database trong parallel stream: worker của common pool ngồi chờ I/O, và mọi parallel stream, mọi `CompletableFuture` mặc định của cả JVM chậm theo.
- Ghi vào biến dùng chung (`list.add` vào `ArrayList`) trong `forEach`: mất phần tử. Dùng `collect`.
- Mất context theo thread (`ThreadLocal`, MDC, `SecurityContext`) trên các worker.

Cách làm đúng: parallel stream cho việc CPU thuần trên dữ liệu trong bộ nhớ, thường trong batch job; I/O thì executor riêng hoặc [[virtual-thread|virtual thread]].

## Deep

- **Thứ tự fork/join**: `left.fork(); long r = right.compute(); return left.join() + r;`. Fork cả hai rồi join cả hai thì thread hiện tại chỉ ngồi chờ thay vì làm một nửa. Fork nhiều task thì join theo thứ tự ngược (task fork sau cùng nằm ở đầu deque); `invokeAll(t1, t2)` làm sẵn việc này.
- **Ngưỡng chia**: Javadoc của `ForkJoinTask` gợi ý mỗi task làm khoảng 100 đến 10.000 bước tính cơ bản. Nhỏ quá thì chi phí tạo task và đẩy vào deque lớn hơn việc thật; lớn quá thì worker khác không có gì để steal, một worker gánh phần dư. Chia theo `n / (parallelism × 4)` cũng là cách hay gặp.
- **`join` và `get`**: `join()` ném lại exception của task mà không bọc (exception từ thread khác được tạo lại cùng kiểu, giữ cause để thấy cả hai stack trace), `get()` bọc mọi lỗi trong `ExecutionException` và phản hồi interrupt. Trong parallel stream, một phần tử lỗi thì exception bay ra ở thread gọi; task đang chạy vẫn chạy nốt, một số task chưa bắt đầu bị bỏ, và side effect đã làm không được huỷ.
- **Chỉnh common pool**: `-Djava.util.concurrent.ForkJoinPool.common.parallelism=N` (Javadoc từ JDK 25 khuyên dùng `ForkJoinPool.commonPool().setParallelism(N)`, có từ Java 19; method này ném `UnsupportedOperationException` nếu đã đặt property). Trong container, số core lấy theo CPU limit của cgroup (từ JDK 19, chỉ tính quota/limit, không tính CPU `request`); pod giới hạn 1 hoặc 2 CPU thì common pool chỉ có 1 worker, và parallel stream gần như chạy tuần tự. `CompletableFuture.*Async` trên pod như vậy đổi hành vi theo phiên bản: Java 21–24 tạo **một thread mới cho mỗi task**, từ JDK 25 dồn hết vào 1 worker của common pool, tức là chạy tuần tự. Nâng JDK trên pod nhỏ có thể làm chậm hẳn code dùng `*Async` không truyền executor. `-XX:ActiveProcessorCount` ép giá trị khác.
- **Chạy parallel stream trên pool riêng**: `ForkJoinPool pool = new ForkJoinPool(4); pool.submit(() -> list.parallelStream().map(...).toList()).get();` cho các task của stream chạy trong `pool` thay vì common pool (thread tên `ForkJoinPool-1-worker-*`). Đây là hành vi của cài đặt hiện tại, không phải hợp đồng trong spec; nhớ `shutdown()` pool. Cần cô lập lâu dài thì tách hẳn sang executor riêng.
- **Block và bù thread**: `ForkJoinPool.managedBlock(ManagedBlocker)` báo trước cho pool là sắp chặn, pool tạo thêm worker dự phòng (common pool tối đa 256, `common.maximumSpares`). `CompletableFuture.join()` gọi trong worker dùng cơ chế này; `Thread.sleep`, I/O socket, `synchronized` thì không, nên worker bị chặn thật.
- **Mode FIFO**: `new ForkJoinPool(n, factory, handler, true)` (`asyncMode`) lấy task theo FIFO, hợp cho task kiểu sự kiện không bao giờ `join`. Scheduler của virtual thread là một `ForkJoinPool` chạy mode này.
- **Thao tác làm hỏng song song**: `findFirst` buộc giữ thứ tự, `findAny` thì không; `.unordered()` trước `distinct()` hoặc `limit()` giúp chúng song song được. `Collectors.groupingByConcurrent` tránh gộp nhiều map khi không cần thứ tự. `collect(toList())` phải ghép các mảnh con, tốn thêm bộ nhớ.
- **Parallel stream trong web server**: dưới tải, các request đã dùng hết core; thêm parallel stream trong từng request không tăng throughput mà thêm tranh chấp, và một request chậm có thể làm nghẽn common pool của request khác. Lợi ích rõ nhất là ở job chạy riêng, máy rảnh core.
- **Đo trước khi chọn**: so tuần tự với song song bằng JMH trên dữ liệu và số core giống production. Stream tuần tự với vòng lặp đơn giản thường đã đủ nhanh, và dễ hiểu hơn.
- **Lớp khác trong gia đình**: `RecursiveAction` cho task không trả kết quả; `CountedCompleter` (stream dùng bên trong) không cần `join`, task cha hoàn thành khi đếm đủ số task con xong; `Arrays.parallelSort` chỉ chia khi mảng object lớn hơn 8.192 phần tử, mảng nguyên thủy lớn hơn 4.096, và common pool có hơn 1 worker.
