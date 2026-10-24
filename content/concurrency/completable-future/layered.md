## Quick

`CompletableFuture` là một `Future` có thể nối tiếp: thay vì chặn thread bằng `get()`, ta đăng ký bước tiếp theo (`thenApply`, `thenCompose`, `thenCombine`) và bước xử lý lỗi (`exceptionally`, `handle`). **Luôn truyền executor riêng cho việc IO**, vì mặc định các method `*Async` chạy trên [[common-pool|ForkJoinPool.commonPool()]] dùng chung cho cả JVM.

## Interview

`Future` cũ (Java 5) chỉ có `get()` chặn thread và không ghép được với nhau. `CompletableFuture` (Java 8) cài đặt [[completion-stage|CompletionStage]]: mỗi method trả về một stage mới, tạo thành một chuỗi xử lý không chặn thread.

Các method hay dùng:
- **Bắt đầu**: `supplyAsync(supplier, executor)` khi có kết quả, `runAsync` khi không có.
- **Biến đổi**: `thenApply(x -> y)` như `map`. `thenCompose(x -> futureOfY)` như `flatMap`, dùng khi bước sau tự trả về `CompletableFuture` (gọi service khác). Dùng `thenApply` ở đây sẽ ra kiểu `CompletableFuture<CompletableFuture<Y>>`.
- **Gộp**: `thenCombine(other, (a, b) -> ...)` cho hai việc độc lập. `allOf(f1, f2, ...)` chờ tất cả, trả `CompletableFuture<Void>`, nên sau đó phải `join()` từng future để lấy kết quả. `anyOf` lấy cái xong đầu tiên, trả `CompletableFuture<Object>`, và lỗi theo nếu future xong đầu tiên là future lỗi.
- **Lỗi**: `exceptionally(ex -> fallback)` thay lỗi bằng giá trị. `handle((value, ex) -> ...)` luôn chạy, nhận cả hai. `whenComplete` chỉ quan sát (log, metric) và giữ nguyên kết quả.
- **Hạn thời gian** (Java 9+): `orTimeout(800, MILLISECONDS)` làm stage lỗi với `TimeoutException`. `completeOnTimeout(defaultValue, ...)` trả giá trị mặc định.

Lỗi lan dọc chuỗi: một stage lỗi thì mọi stage phụ thuộc phía sau cũng lỗi, cho tới stage xử lý lỗi đầu tiên. Ở các stage phía sau, lỗi được bọc trong [[completion-exception|CompletionException]], nên lỗi thật nằm ở `ex.getCause()`. `join()` ném `CompletionException` (unchecked). `get()` ném `ExecutionException` (checked) và `InterruptedException`.

Bẫy hay gặp:
- Gọi `join()` ngay sau mỗi `supplyAsync` trong vòng lặp làm các lời gọi chạy **tuần tự**. Phải tạo hết future trước rồi mới chờ.
- Chạy việc [[io-bound|IO-bound]] blocking trên common pool. Pool này chỉ có khoảng *số core − 1* thread và được dùng chung với parallel stream, nên vài lời gọi chậm làm nghẽn cả ứng dụng.
- Quên xử lý lỗi. Không ai `join()` và không có `exceptionally` thì lỗi biến mất không dấu vết.

## Deep

- **Callback không có `Async` chạy trên thread nào?** Javadoc không cam kết, chỉ nói có thể là thread hoàn thành future hoặc thread gọi method. Theo cài đặt OpenJDK: nếu stage trước chưa xong: chạy trên thread hoàn thành stage trước. Nếu đã xong: chạy ngay trên thread gọi `thenApply`. Callback nặng nên dùng `thenApplyAsync(fn, executor)`.
- **`cancel(true)` không interrupt task đang chạy**: Javadoc ghi rõ tham số `mayInterruptIfRunning` không có tác dụng. Future chỉ chuyển sang trạng thái huỷ, còn lời gọi HTTP bên trong vẫn chạy tiếp. `orTimeout` cũng vậy: nó chỉ hoàn thành future, không dừng công việc. Timeout thật phải đặt ở HTTP client hoặc driver DB.
- **Khi common pool có parallelism < 2** (máy hoặc container 1–2 CPU), `supplyAsync` không truyền executor sẽ tạo **một thread mới cho mỗi task**. Đây là thêm một lý do để luôn truyền executor.
- **`ThreadLocal` không đi theo chuỗi**: MDC (trace id trong log), security context, transaction của Spring nằm trên thread gọi, không có trên thread của executor. Cần copy context khi nộp task, hoặc dùng executor có hỗ trợ truyền context.
- **`exceptionally` chỉ xử lý lỗi của các stage phía trên nó**. Đặt nó ở cuối chuỗi để bắt mọi lỗi, hoặc đặt ngay sau một lời gọi cụ thể để fallback riêng cho lời gọi đó.
- **`allOf` không huỷ các future còn lại khi một future lỗi**, và vẫn chờ tất cả xong rồi mới báo lỗi. Muốn "lỗi một là dừng hết" thì phải tự cancel, hoặc dùng [[structured-concurrency|Structured Concurrency]] (`StructuredTaskScope`, preview từ Java 21). API này còn đổi giữa các bản preview, ví dụ JDK 25 chuyển sang `StructuredTaskScope.open()` với `Joiner`, nên đừng chép code Java 21 sang JDK mới.
- **`completedFuture(value)`** tạo future đã xong, hữu ích để viết test hoặc trả kết quả từ cache trong API trả về `CompletableFuture`.
- **Với [[virtual-thread|virtual thread]] (Java 21)**, nhiều trường hợp có thể viết code blocking tuần tự thay cho chuỗi callback. Mỗi request chạy trên một virtual thread, và các việc song song được nộp vào `newVirtualThreadPerTaskExecutor()`. Code dễ đọc và stack trace dễ debug hơn.
