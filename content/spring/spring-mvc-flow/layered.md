## Quick

Một request đi qua: **thread của Tomcat → [[servlet-filter|filter]] → [[dispatcher-servlet|DispatcherServlet]] → HandlerMapping tìm method controller → [[handler-interceptor|interceptor]] `preHandle` → bind tham số (Jackson, validation) → controller → ghi response bằng `HttpMessageConverter`**. Exception từ controller được `@ControllerAdvice` xử lý; **exception ném trong filter thì không**, vì filter nằm ngoài DispatcherServlet.

## Interview

**Hai tầng**:
- **Servlet**: Tomcat lấy một thread trong [[thread-pool|pool]] (mặc định tối đa 200) và chạy chuỗi filter. Spring Security, CORS, ghi log request, đặt correlation id đều là filter. Filter thấy mọi request, kể cả request không tới controller.
- **Spring MVC**: filter cuối gọi `DispatcherServlet`, servlet duy nhất của ứng dụng.

**Trong DispatcherServlet**:
1. `HandlerMapping` khớp URL và method HTTP với `@GetMapping`, `@PostMapping`.
2. `preHandle` của các interceptor chạy. Interceptor biết method controller nào sắp chạy, nên hợp với kiểm tra theo annotation.
3. `HandlerAdapter` resolve từng tham số: `@PathVariable`, `@RequestParam`, `@RequestBody` (Jackson đọc JSON qua `HttpMessageConverter`). Có `@Valid` thì validate; sai thì `MethodArgumentNotValidException`, trả 400.
4. Controller chạy, giá trị trả về được ghi thành JSON.
5. `postHandle` rồi `afterCompletion` của interceptor.

**Xử lý lỗi**: `@RestControllerAdvice` cùng `@ExceptionHandler` biến exception thành response. Spring 6 có [[problem-detail|ProblemDetail]] theo RFC 9457 cho body lỗi chuẩn; Boot không bật mặc định, cần `spring.mvc.problemdetails.enabled=true` hoặc advice kế thừa `ResponseEntityExceptionHandler`. Exception không ai xử lý tới `/error` của Boot.

**Filter hay interceptor**:
- Cần sửa request hoặc response, hay áp cho mọi request (bảo mật, nén, log): **filter**.
- Cần biết handler hay annotation trên method: **interceptor**.

**Bẫy hay gặp**:
- Bind thẳng entity từ `@RequestBody` cho phép client gửi field không được phép sửa, như `role` hay `id` ([[mass-assignment|mass assignment]]). Dùng DTO record riêng cho mỗi API.
- Gọi dịch vụ chậm trong controller giữ thread Tomcat suốt thời gian chờ. Đủ request như vậy là hết 200 thread và ứng dụng ngừng trả lời mọi API.

## Deep

- **`postHandle` với `@ResponseBody`**: body đã được ghi và response có thể đã commit trước khi `postHandle` chạy, nên thêm header ở đó không có tác dụng. Dùng `ResponseBodyAdvice` hoặc filter.
- **Lỗi trong filter**: exception ném từ filter không đi qua `@ControllerAdvice`. Spring Security trả 401 và 403 qua `AuthenticationEntryPoint` và `AccessDeniedHandler` của nó; muốn body lỗi giống phần còn lại thì cấu hình ở đó.
- **Body chỉ đọc được một lần**: `InputStream` của request là stream. Filter đọc body để log thì controller nhận body rỗng (xem lab). `ContentCachingRequestWrapper` chỉ giữ lại phần đã được đọc, nên phải log sau `chain.doFilter`.
- **Validation**:
  - `@Valid @RequestBody` báo `MethodArgumentNotValidException`.
  - Ràng buộc trên `@RequestParam` hay `@PathVariable` (`@Min(1) int page`): từ Spring 6.1 MVC tự validate khi method có annotation ràng buộc, lỗi là `HandlerMethodValidationException`. Bản cũ cần `@Validated` trên class, và lỗi là `ConstraintViolationException` (mặc định thành 500 nếu không xử lý).
  - Khi method có ràng buộc trực tiếp trên tham số, method validation thay cho validation từng tham số: lúc đó cả `@Valid @RequestBody` sai cũng báo `HandlerMethodValidationException` (mặc định 400), không phải `MethodArgumentNotValidException`.
  - Nâng lên 6.1 thì bỏ `@Validated` ở class controller; giữ lại thì AOP vẫn validate song song và ném `ConstraintViolationException`.
  - Handler lỗi phải xử lý đủ các loại này.
- **Trailing slash**: Spring 6 (Boot 3) bỏ khớp dấu `/` cuối mặc định: `/orders/` không còn khớp `@GetMapping("/orders")`, và client cũ nhận 404 sau khi nâng cấp. Thêm mapping rõ ràng, chuyển hướng ở gateway, hoặc dùng `UrlHandlerFilter` (Spring 6.2+) để redirect hay bỏ dấu `/` cuối.
- **Jackson**:
  - Boot cấu hình `ObjectMapper` (Jackson 3 ở Boot 4 là `JsonMapper`) qua `spring.jackson.*`. Tự khai báo bean mapper thì thay hẳn bản của Boot và mất các tuỳ chỉnh đó; muốn thêm cấu hình thì dùng bean customizer: `Jackson2ObjectMapperBuilderCustomizer` ở Boot 3 (Jackson 2), `JsonMapperBuilderCustomizer` ở Boot 4 (Jackson 3, package `tools.jackson`).
  - Jackson 2 mặc định báo lỗi khi gặp field lạ, nhưng Boot 3 tắt điều đó; Jackson 3 (Boot 4) tắt sẵn. Ngày giờ ra dạng ISO-8601 thay vì số.
- **Thứ tự filter**: Spring Security đứng ở order khoảng -100. Filter tự viết cần thấy user đã xác thực thì phải đứng sau nó; filter đặt MDC correlation id thì nên đứng trước để log của Security cũng có id. Luôn xoá MDC trong `finally`, vì thread của Tomcat được dùng lại cho request khác.
- **Giải phóng thread**:
  - Trả `Callable`, `DeferredResult` hoặc `CompletableFuture` để trả thread Tomcat về pool trong lúc chờ. Filter và interceptor phải hiểu async dispatch: thread ban đầu chỉ gọi `afterConcurrentHandlingStarted` của `AsyncHandlerInterceptor`, `postHandle` và `afterCompletion` chạy sau ở lần dispatch khác, và MDC không tự sang thread mới.
  - Với Java 21 và Boot 3.2+, `spring.threads.virtual.enabled=true` cho mỗi request một [[virtual-thread|virtual thread]], nên code blocking không còn giữ thread nền.
  - Virtual thread bỏ mất giới hạn 200 thread, nên áp lực dồn xuống connection pool của database và HTTP client; cần giới hạn đồng thời (semaphore, bulkhead) ở các chỗ đó.
  - Cả hai cách đều không làm dịch vụ phía sau nhanh hơn, và vẫn cần timeout.
- **Tìm handler**: từ Boot 2.6, mặc định khớp URL bằng `PathPatternParser`, nhanh hơn `AntPathMatcher` cũ. Tới Spring 6.x, `**` chỉ được đứng cuối pattern; từ Spring 7 được đứng đầu hoặc cuối (không ở giữa, mỗi pattern một lần), và `AntPathMatcher` cho MVC đã deprecated.
- **`@ResponseStatus` và `ResponseStatusException`**: cho lỗi đơn giản. Hệ thống lớn thường có một `@RestControllerAdvice` chung map exception nghiệp vụ sang mã HTTP và `ProblemDetail`, để mọi service trả lỗi cùng một dạng.
- **Request bị huỷ**: client đóng kết nối giữa chừng thì ghi response báo `ClientAbortException` hoặc broken pipe. Đây không phải lỗi server; lọc riêng để không làm nhiễu cảnh báo.
