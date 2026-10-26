## Quick

Reactive programming mô tả xử lý dữ liệu thành một chuỗi bước chạy khi dữ liệu tới, thay vì một thread ngồi chờ. [[reactive-streams|Reactive Streams]] định nghĩa bốn interface (`Publisher`, `Subscriber`, `Subscription`, `Processor`) và luật [[backpressure]]: subscriber nói mình nhận được bao nhiêu phần tử qua `request(n)`. Project Reactor cài đặt nó bằng [[mono|`Mono`]] (0–1 phần tử) và [[flux|`Flux`]] (0–N). **Không có gì chạy cho tới khi có `subscribe`, và không có gì tự chạy trên thread khác cho tới khi bạn chỉ định [[reactor-scheduler|scheduler]].**

## Interview

Luồng tín hiệu: subscriber gọi `subscribe`, publisher trả về một `Subscription` qua `onSubscribe`. Subscriber gọi `request(n)`; publisher được phát tối đa n lần `onNext`, rồi kết thúc bằng tối đa một `onComplete` hoặc `onError` (stream vô hạn hoặc bị `cancel` thì không có). Các tín hiệu tới tuần tự, không bao giờ đồng thời. Từ Java 9, `java.util.concurrent.Flow` có cùng bốn interface.

Mỗi operator (`map`, `filter`, `flatMap`) là một publisher bọc publisher phía trên, nên một chuỗi operator là một chuỗi subscriber lồng nhau. Lúc `subscribe`, yêu cầu đi ngược từ cuối lên nguồn; dữ liệu đi xuôi xuống.

Operator hay bị hỏi:
- `map` biến đổi đồng bộ; `flatMap` gọi bất đồng bộ cho từng phần tử, chạy đồng thời (mặc định 256), **không giữ thứ tự**. `concatMap` giữ thứ tự nhưng tuần tự; `flatMapSequential` chạy đồng thời và trả kết quả theo thứ tự gốc.
- `publishOn(scheduler)` chuyển các bước **phía sau** sang scheduler đó. `subscribeOn(scheduler)` quyết định thread chạy lúc subscribe, tức là nguồn, đặt ở đâu trong chuỗi cũng vậy, và chỉ lần gần nguồn nhất có tác dụng.
- Scheduler: `parallel()` (số core, cho việc CPU), `boundedElastic()` (cho code blocking bắt buộc phải gọi), `single()`, `immediate()`.

Lỗi là tín hiệu kết thúc: sau `onError` chuỗi dừng hẳn. Xử lý bằng `onErrorResume`, `onErrorReturn`, `retryWhen(Retry.backoff(...))`, đặt `timeout` cho từng lời gọi ngoài.

So với [[virtual-thread|virtual thread]]: cả hai giải quyết "nhiều việc chờ I/O với ít thread". Virtual thread giữ code tuần tự, stack trace và debug như thường; reactive mạnh ở backpressure qua cả chuỗi, streaming dài (SSE, Kafka), ghép nhiều luồng (`zip`, `merge`, `window`) và huỷ lan truyền. Đổi lại reactive khó đọc, khó debug, và cả chuỗi phải non-blocking.

## Deep

- **Cold và hot**: `Flux.fromIterable`, `webClient.get()...` là cold: mỗi subscriber chạy lại từ đầu (mỗi lần subscribe là một lời gọi HTTP mới). Hot publisher phát bất kể có ai nghe: `Sinks.many().multicast()`, `share()`, `publish().autoConnect(n)`. Muốn nhiều subscriber dùng chung một lần gọi mà không gọi lại thì `cache()` hoặc `replay()`.
- **Eager và lazy**: `Mono.just(loadUser())` gọi `loadUser()` **ngay lúc dựng chuỗi**, kể cả khi không ai subscribe, và chạy trên thread hiện tại. Dùng `Mono.fromCallable(() -> loadUser())` hoặc `Mono.defer(...)` để trì hoãn tới lúc subscribe. Tương tự `switchIfEmpty(Mono.just(x))` luôn tính `x`.
- **Backpressure khi nguồn không chờ được**: `Flux.interval` phát theo đồng hồ; subscriber chậm thì nó phát `onError` với `OverflowException` ("Could not emit tick ... due to lack of requests"). Nguồn kiểu đó cần chiến lược: `onBackpressureBuffer(n)` (có giới hạn), `onBackpressureDrop`, `onBackpressureLatest`. `Flux.create` mặc định buffer không giới hạn, nguồn nhanh hơn subscriber là đầy heap. `limitRate(n)` chia `request` thành từng lô để nguồn không bị hỏi một lần quá nhiều.
- **`flatMap` và downstream**: 256 lời gọi đồng thời mặc định có thể quá tải service phía sau; đặt `flatMap(f, 20)`. `prefetch` (mặc định 32) là số phần tử mỗi nguồn con được đòi trước.
- **Bẫy `subscribe()` bên trong chuỗi**: `map(order -> { auditClient.send(order).subscribe(); return order; })` biến lời gọi thành fire-and-forget: lỗi bị nuốt, không có backpressure, không bị huỷ theo request, mất `Context`. Ghép vào chuỗi bằng `flatMap` hoặc `then` thay vì `subscribe`.
- **`block()`**: hợp lệ ở biên, nơi code imperative gọi vào chuỗi; gọi trên thread non-blocking (event loop, `parallel`, `single`) thì ném `IllegalStateException`. Thông báo lỗi và cách bắt sớm bằng BlockHound xem ở bài Spring WebFlux & Netty.
- **Context thay `ThreadLocal`**: một chuỗi đổi thread nhiều lần nên `ThreadLocal` (MDC, security) không đi theo. Reactor `Context` gắn với subscription, ghi bằng `contextWrite` và truyền **ngược lên** nguồn, nên `contextWrite` phải đặt ở cuối chuỗi. Reactor 3.5.3+ có `Hooks.enableAutomaticContextPropagation()` cùng thư viện context-propagation của Micrometer để tự chép MDC, trace id sang `ThreadLocal`; cần đăng ký `ThreadLocalAccessor` cho từng giá trị (Spring Boot cùng Micrometer Tracing làm sẵn).
- **Debug**: stack trace của reactive thường chỉ có frame của Reactor. `checkpoint("tên")` thêm dấu vết rẻ ở chỗ quan trọng; `Hooks.onOperatorDebug()` ghi stack lúc dựng mọi operator, rất đắt; `ReactorDebugAgent` (reactor-tools) làm việc tương tự bằng instrument bytecode, rẻ hơn, dùng được ở production.
- **Test**: `StepVerifier.create(flux).expectNext(a, b).verifyComplete()`; với operator theo thời gian (`delayElements`, `timeout`, `retryWhen(backoff)`) dùng `StepVerifier.withVirtualTime(() -> ...)` và `thenAwait(Duration)` để không phải chờ thật; chuỗi phải được tạo **bên trong** `Supplier`, nếu không operator đã gắn với scheduler thật. Chạy cùng BlockHound để bắt lời gọi blocking.
- **Huỷ lan truyền**: client ngắt kết nối thì WebFlux `cancel` subscription, tín hiệu đi ngược và dừng mọi lời gọi đang chờ phía trên. Đây là thứ thread-per-request không tự có. `doFinally` chạy cả khi bị huỷ; `doOnComplete` thì không.
- **Khi nào không dùng**: service CRUD đồng bộ mà đội chưa quen reactive, có thư viện chỉ có API blocking (JDBC, SDK cũ), hoặc cần debug dễ. Trên Java 21+, virtual thread thường là lựa chọn đơn giản hơn; runtime Netty và WebFlux xem ở bài Spring WebFlux & Netty.
