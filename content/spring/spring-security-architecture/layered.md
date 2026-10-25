## Quick

Spring Security là một **chuỗi [[servlet-filter|servlet filter]]** đứng trước `DispatcherServlet`. [[security-filter-chain|`SecurityFilterChain`]] đầu tiên khớp với request sẽ xử lý nó. Filter xác thực lấy thông tin đăng nhập (session, form, bearer token) và nhờ [[authentication-manager|`AuthenticationManager`]] kiểm tra. Kết quả là một `Authentication` có danh sách authority, đặt vào [[security-context|`SecurityContext`]] gắn với thread. `AuthorizationFilter` ở cuối chuỗi quyết định cho đi tiếp hay không. Lỗi thành 401 (chưa xác thực) hoặc 403 (không đủ quyền).

## Interview

**Đường đi của request**:
1. Servlet container gọi `DelegatingFilterProxy`; nó chuyển sang bean `FilterChainProxy` (tên `springSecurityFilterChain`).
2. `FilterChainProxy` chọn **một** `SecurityFilterChain` đầu tiên có `securityMatcher` khớp, theo `@Order`. Chain không khai báo matcher khớp mọi request.
3. Các filter chạy theo thứ tự cố định: CORS, CSRF, logout, các filter xác thực (`UsernamePasswordAuthenticationFilter`, `BearerTokenAuthenticationFilter`...), `ExceptionTranslationFilter`, cuối cùng là `AuthorizationFilter`.

**Xác thực**: `AuthenticationManager` (thường là `ProviderManager`) hỏi lần lượt các `AuthenticationProvider`. Đăng nhập bằng mật khẩu dùng `DaoAuthenticationProvider` (`UserDetailsService` + `PasswordEncoder`). [[resource-server|Resource server]] dùng `JwtAuthenticationProvider`: kiểm tra chữ ký bằng khoá công khai lấy từ JWKS của issuer, rồi `exp`/`nbf`, và `iss` khi cấu hình `issuer-uri`.

**Phân quyền**:
- Theo URL: `authorizeHttpRequests` với `requestMatchers`, rule đầu tiên khớp thắng, `anyRequest()` đặt cuối.
- Theo method: [[method-security|`@PreAuthorize`]] (bật bằng `@EnableMethodSecurity`) chạy qua proxy, nên chịu mọi giới hạn của proxy (bài AOP & proxy).
- `hasRole("ADMIN")` kiểm tra authority `ROLE_ADMIN`. JWT mặc định chỉ sinh authority `SCOPE_xxx` từ claim `scope`/`scp`; role của identity provider phải tự ánh xạ.

**401 và 403**: `ExceptionTranslationFilter` bắt `AuthenticationException` thì gọi `AuthenticationEntryPoint` (401 hoặc chuyển tới trang đăng nhập). Bắt `AccessDeniedException` thì trả 403; nếu người dùng còn ẩn danh thì coi như chưa đăng nhập, trả 401.

**Session hay stateless**: ứng dụng web dùng session và cookie, phải giữ [[csrf|CSRF]] protection. API nhận bearer token, không dùng cookie, thì `SessionCreationPolicy.STATELESS` và tắt CSRF là hợp lý.

## Deep

- **Spring Security 6 (Boot 3)**:
  - `WebSecurityConfigurerAdapter` bị bỏ; cấu hình bằng bean `SecurityFilterChain`.
  - `authorizeRequests` thành `authorizeHttpRequests`, dùng `AuthorizationManager`.
  - `antMatchers`/`mvcMatchers` thành `requestMatchers`.
  - `@EnableGlobalMethodSecurity` thành `@EnableMethodSecurity`, bật `prePostEnabled` sẵn.
- **Spring Security 7 (Boot 4)**: chỉ còn kiểu cấu hình lambda (`.and()` đã bị bỏ); `authorizeRequests`, `AntPathRequestMatcher` và `MvcRequestMatcher` cũng bị xoá. `PathPatternRequestMatcher` (có từ 6.5) là matcher mặc định, khớp đường dẫn giống Spring MVC.
- **`SecurityContext` không tự lưu nữa**: từ 6.0, `SecurityContextHolderFilter` chỉ đọc context từ session. Code đăng nhập tự viết phải gọi `securityContextRepository.saveContext(...)`, nếu không request sau lại là ẩn danh. Bản 5 tự lưu ở cuối request bằng `SecurityContextPersistenceFilter`.
- **Mọi dispatcher type đều bị phân quyền** (từ 6.0): khi controller ném lỗi, Boot forward sang `/error`. Nếu `/error` không được `permitAll`, người dùng ẩn danh nhận 401 thay cho lỗi thật: lỗi bị che trong response. Thêm `.requestMatchers("/error").permitAll()` hoặc `.dispatcherTypeMatchers(DispatcherType.ERROR).permitAll()`.
- **Nhiều chain**:
  - Chain cho API (`securityMatcher("/api/**")`, bearer token, stateless) và chain cho trang web (form login, session) phải có `@Order` khác nhau.
  - Chain không có matcher đặt lên trước: trước 6.4 nó âm thầm nuốt mọi request; từ 6.4 (Boot 3.4) ứng dụng không khởi động, báo `UnreachableFilterChainException`. Hai chain có matcher giống hệt nhau cũng bị báo lỗi này.
  - Actuator nên có chain riêng với `EndpointRequest.toAnyEndpoint()`.
- **Ánh xạ role từ JWT**: dùng `JwtAuthenticationConverter` với `JwtGrantedAuthoritiesConverter`, đặt `authoritiesClaimName` (ví dụ `roles`) và `authorityPrefix` là `ROLE_`. Role nằm trong claim lồng nhau (như `realm_access.roles` của Keycloak) thì phải viết converter riêng.
- **Kiểm tra token**:
  - Mặc định không kiểm tra `aud`. Token cấp cho service khác cùng issuer cũng được chấp nhận nếu không khai báo `spring.security.oauth2.resourceserver.jwt.audiences` (Boot 2.7+) hoặc validator riêng.
  - `NimbusJwtDecoder` cache JWK set và tải lại khi gặp `kid` lạ, nên identity provider xoay khoá không làm service lỗi.
  - Token còn hạn thì vẫn được chấp nhận sau khi người dùng bị khoá; thu hồi tức thời cần token ngắn hạn hoặc introspection (bài JWT chuyên sâu).
- **Method security chi tiết**:
  - Biểu thức gọi được bean: `@PreAuthorize("@orderAuthz.canView(#orderId, authentication)")`, cách quen thuộc để chặn IDOR (người dùng đổi id trong URL để xem dữ liệu người khác).
  - `@PostAuthorize` chạy method rồi mới kiểm tra, nên tác dụng phụ đã xảy ra. `@PostFilter` tải hết rồi lọc trong bộ nhớ, không dùng cho danh sách lớn.
  - Self-invocation bỏ qua kiểm tra; gắn `@PreAuthorize` ở bean được gọi từ controller.
- **`SecurityContext` và thread**: mặc định là [[thread-local|`ThreadLocal`]]. Code chạy ở `@Async` hay `CompletableFuture` thấy context rỗng; bọc executor bằng `DelegatingSecurityContextAsyncTaskExecutor` (cách truyền context qua `TaskDecorator`: bài @Async, @Scheduled & event). Không dùng `MODE_INHERITABLETHREADLOCAL` với thread pool, vì thread được dùng lại sẽ mang danh tính của request cũ.
- **CORS**: request preflight `OPTIONS` không mang token. Bật `.cors(withDefaults())` để `CorsFilter` trả lời trước khi tới filter xác thực, thay vì `permitAll` cho mọi `OPTIONS`.
- **Gỡ lỗi**: `logging.level.org.springframework.security=TRACE` in chain nào được chọn, từng filter đã chạy và lý do từ chối. Đây là cách nhanh nhất để giải thích một lỗi 401 hay 403 khó hiểu.
