## Quick

Spring AOP thêm hành vi (transaction, cache, bảo mật, retry) quanh method bằng cách **thay bean bằng [[aop-proxy|proxy]]**: [[jdk-dynamic-proxy|JDK dynamic proxy]] nếu proxy theo interface, [[cglib|CGLIB]] (lớp con) nếu proxy theo class; Spring Boot mặc định dùng CGLIB. **Chỉ lời gọi đi qua proxy mới có advice**: gọi qua `this`, method `private`, `final` hay `static` đều bỏ qua mọi annotation như `@Transactional`.

## Interview

**Thuật ngữ**:
- **Aspect**: class gom hành vi dùng chung, ví dụ đo thời gian.
- **Pointcut**: biểu thức chọn method, như `execution(* com.shop..*Service.*(..))` hoặc `@annotation(Audited)`.
- **Advice**: code chạy `@Before`, `@AfterReturning`, `@AfterThrowing`, `@After` hay `@Around` quanh method.
- Spring AOP chỉ có join point là **lời gọi method trên bean**.

**Proxy được tạo thế nào**: một [[bean-post-processor|BeanPostProcessor]] tạo proxy ở `postProcessAfterInitialization` nếu có advisor khớp bean (bài Bean lifecycle & scope). Bean khác được inject proxy. Proxy giữ một chuỗi interceptor; mỗi interceptor làm việc của nó rồi gọi `proceed()` sang cái tiếp theo, cuối cùng tới object gốc.

**JDK và CGLIB**:
- JDK proxy implement các interface của bean. Inject theo class cụ thể thì lỗi `BeanNotOfRequiredTypeException` (hoặc `NoSuchBeanDefinitionException`, tuỳ thứ tự tạo bean).
- CGLIB tạo lớp con lúc chạy, nên không proxy được class hay method `final`.
- Boot đặt `spring.aop.proxy-target-class=true` từ 2.0, nên mặc định là CGLIB kể cả khi có interface.

**[[self-invocation|Self-invocation]]**: `placeOrder()` gọi `this.audit()` thì lời gọi đi thẳng trong object gốc, không qua proxy. Cách sửa:
- Tốt nhất là tách method sang bean khác.
- Hoặc inject chính proxy của mình (`@Lazy` hay `ObjectProvider`).
- Hoặc dùng `TransactionTemplate` thay annotation.
- `AopContext.currentProxy()` cũng được, nhưng phải bật `exposeProxy` và làm code dính vào Spring.

**Thứ tự advice**: nhiều aspect trên cùng method chạy theo `@Order`, số nhỏ ở **ngoài cùng**. Thứ tự này quan trọng: retry phải nằm ngoài transaction để mỗi lần thử có transaction mới; nằm trong thì thử lại trên một transaction đã hỏng.

**Khi cần hơn Spring AOP**: AspectJ weaving lúc biên dịch hoặc lúc nạp class chặn được cả self-invocation, method `private` và constructor. Đổi lại build và vận hành phức tạp hơn, nên hiếm khi đáng.

## Deep

- **Method `final` trên proxy CGLIB**: không bị override nên chạy thẳng trên instance proxy. Từ Spring 4, Objenesis tạo proxy mà không gọi constructor, nên mọi field của instance proxy là `null`; method `final` đọc field là `NullPointerException` (xem lab). Kotlin: class và method mặc định `final`, cần plugin `kotlin-spring` (all-open). Dấu hiệu lúc khởi động: Spring 7 log WARN "Public final method ... cannot get proxied via CGLIB"; Spring 6 chỉ WARN khi method đó implement interface, còn lại ở DEBUG của `org.springframework.aop.framework.CglibAopProxy`.
- **Method `protected` và package-private**: từ Spring 6.0, CGLIB proxy cả chúng, và `@Transactional` áp được; chỉ `private`, `final`, `static` là không.
- **`getClass()` của bean** trả lớp proxy (`OrderService$$SpringCGLIB$$0` ở Spring 6). Code so sánh class, đọc annotation qua `getClass()` hay serialize bean sẽ sai; dùng `AopUtils.getTargetClass()` hoặc `ClassUtils.getUserClass()`.
- **Thứ tự advice trong một aspect**: từ Spring 5.2.7, các advice cùng aspect được gán độ ưu tiên theo thứ tự `@Around`, `@Before`, `@After`, `@AfterReturning`, `@AfterThrowing`; nhưng `@After` có nghĩa như `finally` nên thực tế chạy sau `@AfterReturning` hay `@AfterThrowing`. Hai advice cùng loại trong một aspect thì không có thứ tự xác định; tách thành hai aspect có `@Order`.
- **Thứ tự của advisor có sẵn**: transaction và cache có `order` mặc định thấp nhất (`Ordered.LOWEST_PRECEDENCE`), nên aspect tự viết có `@Order` nhỏ hơn sẽ bọc ngoài chúng; giữa transaction và cache thì thứ tự không xác định nếu không đặt `order`. Chỉnh bằng `@EnableTransactionManagement(order = ...)`, `@EnableCaching(order = ...)`. `@EnableMethodSecurity` (Spring Security 6+) dùng order cố định trong khoảng 100–600, nên nằm ngoài transaction.
- **Retry có sẵn trong Spring 7**: `@Retryable` và `@ConcurrencyLimit` của Spring Framework 7 (bật bằng `@EnableResilientMethods`) được đặt trước các advisor có sẵn, nên nằm ngoài `@Transactional` mà không cần chỉnh `order`. Spring Retry (`@EnableRetry`) nay ở chế độ bảo trì; với nó, kiểm tra `order` để chắc retry nằm ngoài transaction.
- **`@Around` phải gọi `proceed()` và trả kết quả**: quên `return pjp.proceed()` là method luôn trả `null`. Bắt exception trong `@Around` mà không ném lại là nuốt exception, và transaction bên trong sẽ commit.
- **Pointcut rộng là chi phí ẩn**: `execution(* *(..))` làm mọi bean bị proxy, kể cả bean hạ tầng, khởi động chậm, và đôi khi gây lỗi với bean `final` của thư viện. Giới hạn theo package hoặc annotation.
- **Proxy và `equals`, `toString`**: lời gọi `toString()` qua proxy được chuyển sang object gốc, nhưng log in `this` từ bên trong và bên ngoài có thể cho kết quả khác nhau khi debug. Đặt breakpoint trong advice chain (`ReflectiveMethodInvocation.proceed`) để xem có những interceptor nào.
- **Tự viết annotation có hành vi**: annotation chỉ là metadata, cần một aspect `@Around("@annotation(audited)")` hoặc một `MethodInterceptor` đăng ký qua advisor. Pointcut `@annotation` của AspectJ khớp theo method của class đích, nên annotation tự viết đặt trên interface method không được tìm thấy với proxy CGLIB; đặt trên class. Khác với `@Transactional` và `@Cacheable`, vốn được Spring tìm cả trên interface từ 5.0.
- **Chi phí**: một lời gọi qua vài interceptor tốn cỡ micro giây. Đáng kể chỉ khi method rất nhỏ bị gọi hàng triệu lần trong vòng lặp; còn với method có IO thì không đáng kể.
- **Native image**: proxy CGLIB phải được tạo lúc build (Spring AOT làm việc này). Proxy tạo động bằng code tự viết lúc chạy sẽ không hoạt động trong native image.
