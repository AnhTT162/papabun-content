## Quick

Một [[bean]] singleton đi qua: **tạo object → inject dependency → callback `Aware` → [[bean-post-processor|BeanPostProcessor]] trước khởi tạo (chạy `@PostConstruct`) → `afterPropertiesSet` và init method → BeanPostProcessor sau khởi tạo (tạo proxy AOP) → sẵn sàng**, rồi `@PreDestroy` khi context đóng. **Proxy chỉ có sau `@PostConstruct`**, nên `@Transactional` gọi từ đó không có tác dụng. Scope mặc định là [[bean-scope|singleton]]: một object cho cả container, dùng chung mọi thread.

## Interview

**Các bước chính**:
1. Spring gọi constructor (inject qua constructor ở bước này), rồi inject field và setter.
2. Các callback `BeanNameAware`, `BeanFactoryAware`. (`ApplicationContextAware` thực ra do một BeanPostProcessor gọi ở đầu bước 3.)
3. `postProcessBeforeInitialization` của mọi BeanPostProcessor; `@PostConstruct` chạy ở đây.
4. `InitializingBean.afterPropertiesSet()`, rồi init method khai báo trong `@Bean(initMethod = ...)`.
5. `postProcessAfterInitialization`: đây là chỗ AOP thay object bằng proxy cho `@Transactional`, `@Async`, `@Cacheable`. Bean khác nhận proxy, không nhận object gốc.

Khi đóng context: `@PreDestroy`, `DisposableBean.destroy()`, destroy method, theo thứ tự ngược dependency.

**Hai loại post-processor**:
- [[bean-factory-post-processor|BeanFactoryPostProcessor]] sửa *định nghĩa* bean trước khi có object nào. Ví dụ: thay `${...}` bằng giá trị cấu hình.
- BeanPostProcessor sửa *object* sau khi tạo. Ví dụ: chạy `@PostConstruct`, bọc proxy.

**Scope**:
- `singleton` (mặc định): một object cho mỗi bean definition trong container. Không phải singleton kiểu GoF: hai `@Bean` cùng class là hai object.
- `prototype`: mỗi lần container được hỏi là một object mới. Container không gọi destroy cho prototype.
- `request`, `session`: một object cho mỗi HTTP request hoặc session.

**Bẫy hay gặp**:
- **[[prototype-in-singleton|Prototype inject vào singleton]]** chỉ được tạo một lần, lúc singleton được tạo, nên mọi request dùng chung một object. Muốn object mới mỗi lần thì lấy qua `ObjectProvider<T>.getObject()`, `@Lookup`, hoặc dùng scoped proxy.
- **Singleton có field thay đổi** (giỏ hàng, user hiện tại, `SimpleDateFormat`) là [[race-condition|race condition]] giữa các request. Bean singleton nên stateless; state theo request để trong biến cục bộ hoặc tham số.

## Deep

- **`@PostConstruct` và proxy**:
  - Trong `@PostConstruct`, `this` là object gốc và proxy chưa được tạo, nên gọi method `@Transactional` hay `@Async` của chính nó chạy như method thường (giống [[self-invocation]]).
  - Việc cần transaction lúc khởi động (nạp cache từ database) nên chạy sau khi context sẵn sàng: listener `ApplicationReadyEvent` gọi qua bean đã inject, hoặc `SmartInitializingSingleton`.
- **Thứ tự các móc khởi động**: `SmartInitializingSingleton` (mọi singleton đã tạo) → `Lifecycle.start` / `SmartLifecycle` → `ContextRefreshedEvent` → `CommandLineRunner` và `ApplicationRunner` → `ApplicationReadyEvent` (Boot). Web server bắt đầu nhận request trước các runner, nên runner chậm không chặn traffic nhưng có thể chạy song song với request đầu.
- **Circular reference và proxy sớm**: khi vòng tròn qua field được bật, bean trong vòng có thể được bọc proxy *sớm* qua `getEarlyBeanReference`, trước cả `@PostConstruct`. Boot 2.6+ chặn vòng tròn mặc định (bài IoC & Dependency Injection).
- **Việc nặng lúc khởi động**:
  - `@PostConstruct` gọi API bên ngoài mà bên đó chậm hay lỗi thì ứng dụng không khởi động được. Trên Kubernetes thành crash loop, đúng lúc đối tác đang sự cố.
  - Chỉ fail fast khi thiếu thứ đó thật sự không phục vụ được; còn lại thì nạp nền và báo qua readiness probe.
- **BeanPostProcessor được tạo sớm**:
  - BeanPostProcessor và mọi bean nó phụ thuộc được tạo trước các bean khác, nên không qua đủ các post-processor: không có proxy, `@Transactional` trên chúng âm thầm không chạy.
  - Spring ghi log "is not eligible for getting processed by all BeanPostProcessors". Thấy dòng này với bean nghiệp vụ là phải sửa dependency.
- **BeanFactoryPostProcessor khai báo bằng `@Bean`** phải là method `static`. Nếu không, class `@Configuration` chứa nó bị tạo quá sớm và `@Autowired`, `@Value` trong class đó không được xử lý; Spring có log cảnh báo đúng điều này.
- **Thứ tự init**: `@PostConstruct` → `afterPropertiesSet` → init method. Thứ tự giữa các bean không liên quan nhau thì không được đảm bảo; cần thứ tự thì khai báo dependency, hoặc `@DependsOn` khi dependency không thể hiện qua code.
- **Destroy suy luận**: `@Bean` trả về object có method `close()` hoặc `shutdown()` thì Spring tự gọi khi đóng context (`destroyMethod` mặc định là "(inferred)"), nhờ vậy `HikariDataSource` được đóng. Bean prototype giữ tài nguyên (socket, file) thì bạn phải tự đóng.
- **Thứ tự khởi động và dừng**: `SmartLifecycle` có `phase`: phase thấp start trước, stop sau. Kafka listener container và web server dùng cơ chế này để chỉ nhận việc khi mọi bean đã sẵn sàng, và ngừng nhận việc trước khi bean bị huỷ. Boot 3.4+ bật graceful shutdown mặc định cho web server (bài Graceful shutdown).
- **Request scope ngoài request**: bean `@RequestScope` được inject dưới dạng proxy; mỗi lần gọi, proxy tìm object của request hiện tại qua thread. Gọi từ thread `@Async` hay thread pool thì gặp `IllegalStateException: No thread-bound request found`. Truyền dữ liệu cần thiết qua tham số thay vì dựa vào request scope.
- **`@Lookup`**: method có `@Lookup` (thường abstract, có thể là method stub; class không được `final`) được CGLIB override để mỗi lần gọi trả bean mới từ container. Gọn hơn `ObjectProvider` nhưng không dùng được với bean tạo bằng `@Bean`.
- **Một container, một singleton**: test với nhiều cấu hình khác nhau tạo nhiều context (bài Spring Boot Test), mỗi context có singleton riêng. Cache hay scheduler giữ state static sẽ bị dùng chung giữa chúng.
- **Lazy**: `@Lazy` hoặc `spring.main.lazy-initialization=true` hoãn tạo bean tới lần dùng đầu. Khởi động nhanh hơn, nhưng lỗi cấu hình chuyển từ lúc khởi động sang request đầu tiên, và request đầu chậm.
