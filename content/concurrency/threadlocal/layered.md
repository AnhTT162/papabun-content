## Quick

[[thread-local|`ThreadLocal`]] cho mỗi thread một bản giá trị riêng: thread A `set` thì chỉ thread A `get` thấy. Spring dựa vào nó để giữ transaction hiện tại, `SecurityContext`, request hiện tại; logging dùng nó cho [[mdc|MDC]]. Hai bẫy lớn: **thread trong pool được dùng lại**, nên giá trị không `remove()` sẽ lọt sang request sau; và **giá trị không tự đi sang thread khác** (`@Async`, `CompletableFuture`, parallel stream). Từ JDK 25, [[scoped-value|`ScopedValue`]] là cách mới: liên kết bất biến (không `set` lại được), chỉ sống trong một phạm vi, tự hết khi ra khỏi đó.

## Interview

**Nằm ở đâu**: mỗi `Thread` có một `ThreadLocalMap`; key là object `ThreadLocal`, value là giá trị của thread đó. Giá trị sống chừng nào thread còn sống hoặc tới khi `remove()`.

**Rò giữa các request**: Tomcat phục vụ request bằng [[thread-pool|thread pool]]. Filter `set` tenant cho request 1 rồi không dọn; request 2 chạy trên cùng thread mà không `set` lại sẽ đọc tenant của request 1. Đây là lỗi lộ dữ liệu, không chỉ là rò bộ nhớ. Luôn dọn trong `finally` ở cùng chỗ đã `set`:
```java
try {
    TenantContext.set(tenantId);
    chain.doFilter(request, response);
} finally {
    TenantContext.clear();   // gọi remove(), không phải set(null)
}
```

**Không tự đi sang thread khác**:
- `@Async`, executor tự tạo, `CompletableFuture.supplyAsync`, parallel stream: thread mới thấy giá trị rỗng, nên log mất trace id và `SecurityContextHolder` trống.
- Cách truyền: copy giá trị lúc nộp task rồi đặt lại trong thread chạy task, thường qua `TaskDecorator` (bài @Async, @Scheduled & event) hoặc thư viện [[context-propagation|context propagation]] của Micrometer.
- [[inheritable-thread-local|`InheritableThreadLocal`]] chỉ copy lúc **tạo** thread con. Với pool, thread được tạo một lần rồi dùng lại, nên nó mang giá trị của request đã tạo ra thread, sai với mọi request sau.

**[[virtual-thread|Virtual thread]]**: `ThreadLocal` vẫn chạy đúng vì mỗi virtual thread là một thread riêng. Nhưng một triệu virtual thread là một triệu bản giá trị; đừng dùng `ThreadLocal` để cache object đắt (buffer, formatter) khi chạy virtual thread.

**`ScopedValue`** (chính thức từ JDK 25): `ScopedValue.where(TENANT, "t-42").run(() -> handle(req))`. Giá trị chỉ đọc được trong `run`, không `set` lại được, không cần dọn, và được các task con của [[structured-concurrency|`StructuredTaskScope`]] thấy mà không phải copy.

## Deep

- **Cấu trúc bên trong và rò bộ nhớ**:
  - Entry của `ThreadLocalMap` giữ key bằng [[weak-reference|weak reference]] và value bằng tham chiếu mạnh. Object `ThreadLocal` hết được dùng thì key bị GC, nhưng value còn nằm đó tới khi map tình cờ dọn entry cũ trong lúc `get`/`set` khác.
  - Trong thread pool sống suốt đời ứng dụng, value lớn (danh sách, buffer) ở lại mãi.
  - App server chạy nhiều ứng dụng (Tomcat bản cài riêng): value là object của ứng dụng giữ luôn classloader của nó sau khi undeploy. Tomcat log cảnh báo kiểu "created a ThreadLocal ... but failed to remove it when the web application was stopped".
- **`remove()` khác `set(null)`**: `set(null)` để lại entry trong map; `remove()` xoá hẳn, và lần `get()` sau gọi lại `initialValue()` (của `ThreadLocal.withInitial`).
- **Khai báo**: `private static final ThreadLocal<...>`. Tạo `ThreadLocal` mới cho mỗi object hay mỗi lần gọi làm map đầy entry rác và mất ý nghĩa dùng chung.
- **Ai đang dùng `ThreadLocal` trong Spring**:
  - `TransactionSynchronizationManager`: connection và transaction hiện tại. Đây là lý do code chạy ở thread khác không thuộc transaction.
  - `SecurityContextHolder` (mặc định `MODE_THREADLOCAL`), `RequestContextHolder`, `LocaleContextHolder`.
  - MDC của Logback và Log4j2. Logback từ 1.1.5 không còn để thread con kế thừa MDC.
- **Truyền context chi tiết**:
  - `TaskDecorator`: lấy `MDC.getCopyOfContextMap()` và `SecurityContextHolder.getContext()` ở thread nộp task, đặt lại trong `try` ở thread chạy, dọn trong `finally`.
  - Spring Security có `DelegatingSecurityContextExecutor`/`...AsyncTaskExecutor`.
  - Spring Framework 6.1+ có sẵn `ContextPropagatingTaskDecorator`; Spring Boot 3 tự gắn bean `TaskDecorator` (nếu chỉ có một) vào executor nó tự cấu hình.
  - Micrometer context-propagation đăng ký các `ThreadLocalAccessor` để copy mọi giá trị đã đăng ký một lần, dùng cho cả Reactor (bài Spring WebFlux & Netty).
  - `CompletableFuture` truyền executor đã bọc decorator; nếu không, task chạy trên `ForkJoinPool.commonPool()` không có context.
- **Parallel stream**: việc được chia cho common pool và cả thread gọi, phân bố tuỳ kích thước dữ liệu và tải (dữ liệu nhỏ có thể chạy hết trên thread gọi). Kết quả là có phần tử thấy giá trị `ThreadLocal`, có phần tử không: lỗi chập chờn rất khó đoán.
- **Ẩn dependency**: code đọc `ThreadLocal` ở tầng sâu phụ thuộc vào một giá trị không có trong tham số, khó test và khó đọc. Chỉ dùng cho context xuyên suốt (tenant, user, trace); dữ liệu nghiệp vụ nên đi qua tham số ([[thread-confinement|thread confinement]] bằng tham số là cách rõ nhất).
- **Virtual thread chi tiết**:
  - `Thread.ofVirtual().inheritInheritableThreadLocals(false)` tắt việc copy `InheritableThreadLocal` khi tạo thread.
  - Cờ `-Djdk.traceVirtualThreadLocals=true` in stack trace mỗi khi virtual thread `set` một `ThreadLocal`, để tìm thư viện đang cache theo thread.
  - Thư viện cũ cache object theo thread (như `SimpleDateFormat` mỗi thread một bản) mất tác dụng: mỗi virtual thread lại tạo một bản mới.
- **`ScopedValue` chi tiết**:
  - Incubator ở JDK 20, preview từ JDK 21 tới 24, chính thức ở JDK 25 (JEP 506). `StructuredTaskScope` vẫn là preview.
  - Bất biến là liên kết, không phải object: gắn một `List` thay đổi được thì nội dung list vẫn đổi được.
  - Gán lại trong phạm vi con được: `ScopedValue.where(KEY, v2).run(...)` lồng bên trong; ra khỏi đó giá trị cũ quay lại.
  - `KEY.get()` ngoài phạm vi ném `NoSuchElementException`; kiểm tra bằng `isBound()` hoặc dùng `orElse(...)` (ở JDK 25 không nhận `null`).
  - Không đi theo executor thường: `executor.submit` từ trong `run` vẫn không thấy giá trị; chỉ task con của `StructuredTaskScope` mới kế thừa.
  - Chưa thay được mọi chỗ: framework như Spring Security, MDC vẫn dựa trên `ThreadLocal`.
