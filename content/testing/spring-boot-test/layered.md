## Quick

Spring Boot Test có `@SpringBootTest` (nạp cả ứng dụng) và các [[test-slice|test slice]] như `@WebMvcTest`, `@DataJpaTest` (chỉ nạp một tầng). Spring TestContext **cache `ApplicationContext` theo cấu hình**: các test cùng cấu hình dùng chung một context, mỗi khác biệt (`@MockitoBean`, profile, property) sinh một context mới. **Suite chậm thường vì có quá nhiều context khác nhau, không phải vì từng test chậm**, và transaction của test chỉ rollback được code chạy trên cùng thread với test.

## Interview

**`@SpringBootTest`** dùng cho [[integration-test|integration test]], nạp toàn bộ context như production. `webEnvironment` mặc định là `MOCK`: không có server thật, gọi controller qua MockMvc trên cùng thread với test. `RANDOM_PORT` và `DEFINED_PORT` chạy Tomcat thật; `NONE` không có web.

**Slice**: `@WebMvcTest(OrderController.class)` chỉ nạp controller, `@ControllerAdvice`, filter, converter, Jackson; service phải thay bằng [[test-double|test double]] qua `@MockitoBean`. `@DataJpaTest` nạp JPA và repository, mỗi test chạy trong transaction rồi rollback. Slice nhanh và kiểm đúng một tầng, nhưng không thấy lỗi nối giữa các tầng.

**[[context-caching|Context caching]]**: khoá cache gồm class cấu hình, profile, property, initializer và danh sách bean bị thay. Cache giữ tối đa 32 context (`spring.test.context.cache.maxSize`), khi đầy thì bỏ context lâu nhất chưa được dùng (LRU). `@DirtiesContext` đóng context và bỏ nó khỏi cache.

**Vì sao suite chậm và hết tài nguyên**: mỗi class có tổ hợp `@MockitoBean` riêng là một context mới, mất nhiều giây khởi động. Context nằm trong cache vẫn giữ connection pool, nên 32 context giữ hàng trăm connection tới database test.

**Cách làm đúng**: gom mock vào vài class cha hoặc cấu hình dùng chung; slice cho test một tầng, ít `@SpringBootTest` cho luồng chính; bật log `org.springframework.test.context.cache` mức `DEBUG` để đếm context.

**Bẫy hay gặp**: `@Transactional` trên test với `RANDOM_PORT` không rollback được, vì request chạy trên thread của Tomcat, còn transaction của test gắn với thread test qua [[thread-local|ThreadLocal]]. Dữ liệu được commit thật và rò sang test sau.

## Deep

- **Spring Boot 4 tách test theo công nghệ**: `@DataJpaTest` nằm trong `spring-boot-data-jpa-test` (package `org.springframework.boot.data.jpa.test.autoconfigure`), `@WebMvcTest` và `@AutoConfigureMockMvc` trong `spring-boot-webmvc-test`, `@JdbcTest` và `@AutoConfigureTestDatabase` trong `spring-boot-jdbc-test`; dùng các starter như `spring-boot-starter-webmvc-test`, `spring-boot-starter-data-jpa-test`. Nâng từ Boot 3 phải đổi cả dependency lẫn import.
- **`@MockitoBean` thay `@MockBean`**: `@MockBean` và `@SpyBean` deprecated từ Boot 3.4 và bị gỡ ở Boot 4.0 (đã kiểm: `spring-boot-test` 4.0.0 không còn class này). Thay bằng `@MockitoBean`, `@MockitoSpyBean` của Spring Framework 6.2+. Danh sách bean bị thay là một phần khoá cache, nên đặt chúng ở class cha dùng chung thay vì rải mỗi class một kiểu.
- **Đo được**: Spring Boot 4.1.2, bốn class `@SpringBootTest` mỗi class một `@MockitoBean` khác nhau, log cache cuối suite là `size = 4, ... missCount = 4`: bốn lần dựng context cho bốn class.
- **Context pausing** (Spring Framework 7.0, chọn chế độ từ 7.0.3): context trong cache không được dùng sẽ bị `pause()`, tức dừng các bean `Lifecycle` (như listener container), chỉnh bằng `spring.test.context.cache.pause` (`ALWAYS`, `ON_CONTEXT_SWITCH` là mặc định, `NEVER`). Ở bản cũ hơn, context cũ trong cache vẫn chạy ngầm, ví dụ consumer Kafka của nó tranh message với test hiện tại. Connection pool thì vẫn được giữ.
- **`@DataJpaTest` và datasource**: từ Boot 3.4, mặc định `Replace.NON_TEST` thay datasource tự cấu hình bằng database nhúng, nhưng giữ datasource từ `@ServiceConnection`, `@DynamicPropertySource` hay URL `jdbc:tc:` (Boot 3.3 chỉ có `ANY`, `AUTO_CONFIGURED`, `NONE`). Muốn chạy trên database thật đã cấu hình khác thì `@AutoConfigureTestDatabase(replace = NONE)`.
- **Transaction của test giấu lỗi**: dữ liệu chưa flush thì constraint của database chưa được kiểm, nên test có thể xanh dù commit thật sẽ lỗi; gọi `TestEntityManager.flush()` trước khi assert. Session mở suốt test cũng giấu `LazyInitializationException` mà production gặp sau khi transaction đóng. Một vài test luồng chính nên chạy không có `@Transactional` và tự dọn dữ liệu.
- **`@WebMvcTest` và security**: slice này không quét class `@Configuration`, nên `SecurityFilterChain` của bạn không được nạp; auto-configuration bảo mật mặc định của Boot được dùng thay. Test có thể xanh với luật khác production; thêm `@Import(SecurityConfig.class)`.
- **Client để gọi API trong test**: MockMvc chạy cùng thread (rollback được, không có server thật); `RestTestClient` (mới ở Spring Framework 7) gọi được cả MockMvc lẫn server thật; `WebTestClient` cho WebFlux. Với `RANDOM_PORT`, dọn dữ liệu bằng `@BeforeEach`/`@AfterEach` thay vì dựa vào rollback.
- **`@TestConfiguration` thay vì `@Configuration` trong test**: với `@SpringBootTest`, class `@Configuration` trong `src/test` bị component scan nhặt, lặng lẽ áp vào mọi test cùng package gốc. `@TestConfiguration` chỉ có hiệu lực khi được `@Import` hoặc là class lồng trong test.
- **Mỗi giá trị property là một context**: `@SpringBootTest(properties = "feature.x=true")`, `@TestPropertySource`, `@ActiveProfiles` khác nhau đều sinh context mới. Gom theo vài cấu hình chuẩn.
- **Khởi động nhanh hơn**: `spring.main.lazy-initialization=true` trong test giảm thời gian dựng context, nhưng che lỗi wiring chỉ lộ khi bean được dùng; giữ ít nhất một test nạp context đầy đủ không lazy.
- **Kiểm cấu hình properties**: `@ConfigurationProperties` có `@Validated` nên được test bằng `ApplicationContextRunner`, chạy mili giây mà không cần cả ứng dụng; cũng là cách test auto-configuration tự viết.
