## Quick

[[owasp-top-10|OWASP Top 10]] (bản 2025) là danh sách mười nhóm rủi ro web hay gặp nhất, đứng đầu là [[broken-access-control|Broken Access Control]]; nó là tài liệu nâng nhận thức, không phải checklist đủ. Hai quy tắc phủ phần lớn danh sách: **kiểm quyền ở server trên đúng bản ghi, từ chối mặc định**, và **không bao giờ để dữ liệu thành lệnh**: tham số hoá truy vấn, escape theo ngữ cảnh đầu ra, không deserialize hay đánh giá biểu thức từ input.

## Interview

**Danh sách 2025**: A01 Broken Access Control, A02 Security Misconfiguration, A03 Software Supply Chain Failures, A04 Cryptographic Failures, A05 [[injection|Injection]], A06 Insecure Design, A07 Authentication Failures, A08 Software or Data Integrity Failures, A09 Security Logging & Alerting Failures, A10 Mishandling of Exceptional Conditions. So với 2021: [[ssrf|SSRF]] gộp vào A01, Misconfiguration lên thứ hai, "thư viện lỗi thời" mở rộng thành chuỗi cung ứng, A10 là nhóm mới.

**Broken Access Control**: API nhận id rồi trả bản ghi mà không kiểm người gọi có quyền ([[idor|IDOR]]), endpoint admin chỉ ẩn trên giao diện, [[csrf|CSRF]], SSRF. Cách làm đúng: mỗi truy vấn lọc theo chủ sở hữu hoặc tenant, method security, từ chối mặc định, test truy cập chéo giữa hai user.

**Injection**: dữ liệu bị ghép vào một ngôn ngữ khác rồi thành cú pháp: SQL/JPQL, lệnh shell, LDAP, biểu thức SpEL, template, và [[xss|XSS]] (HTML/JavaScript). Cách chung: dùng API tách dữ liệu khỏi lệnh (`PreparedStatement`, tham số `:name`, `ProcessBuilder` với danh sách đối số), phần không tham số hoá được (tên cột, chiều sắp xếp) thì chọn từ allowlist. Với HTML là [[output-encoding|escape theo ngữ cảnh]] khi ghi ra, không phải "lọc input".

**Misconfiguration và lỗi xử lý ngoại lệ**: Actuator mở ra Internet, stack trace trong response, CORS phản chiếu mọi origin, và code [[fail-open|fail open]]: khối `catch` trả "cho qua" khi dịch vụ kiểm quyền lỗi.

**Bẫy hay gặp**: coi [[waf|WAF]] là đủ; validate input bằng blocklist; trả `String` từ `@RestController` có chèn input, mà Spring ghi thành `text/html` khi trình duyệt gọi; kiểm URL của SSRF bằng so chuỗi; một khối `catch` cho qua trong code phân quyền.

## Deep

- **Top 10 không phải tiêu chuẩn kiểm thử**: muốn yêu cầu cụ thể để kiểm thì dùng OWASP ASVS; với API có danh sách riêng là OWASP API Security Top 10 (bài Bảo mật API). Thứ hạng dựa trên tỷ lệ ứng dụng có lỗi và khảo sát, nên A06 Insecure Design (thiếu threat modeling, luồng nghiệp vụ cho phép lạm dụng) không vá được bằng thư viện (bài Bảo mật trong quy trình phát triển).
- **Bài nào sở hữu phần chi tiết**: [[sql-injection|SQL injection]] và `ORDER BY` động (bài JDBC & cách ứng dụng nói chuyện với DB), path traversal và Zip Slip (bài I/O & NIO), deserialization, XXE (bài Serialization & lỗ hổng deserialization), mass assignment (bài Request đi qua Spring MVC), [[log4shell|Log4Shell]] (bài Logging trong Java), CSRF, CORS, CSP và vì sao `HttpOnly` không chặn được XSS (bài Bảo mật phía trình duyệt), hash mật khẩu (bài AuthN & AuthZ cơ bản), mã hoá (bài Mật mã cho kỹ sư), lớp mạng chống SSRF và [[imds|IMDS]] (bài Kiến trúc bảo mật).
- **A01 trong Spring**:
  - `findById(id)` rồi trả luôn là IDOR. Lọc ngay trong truy vấn (`findByIdAndOwnerId(id, currentUserId)`) và trả `404` thay vì `403` để không lộ bản ghi tồn tại.
  - Method security `@PreAuthorize` kiểm được quyền trên bản ghi qua bean, nhưng dễ quên ở endpoint mới; thêm test "user B đọc đơn của user A phải hỏng" cho mọi endpoint có id.
  - `requestMatchers` khớp theo đường dẫn: thứ tự luật sai (luật rộng đứng trước) mở cả nhóm. Kết bằng `anyRequest().authenticated()` hoặc `denyAll()`.
  - Mô hình RBAC/ABAC và cô lập tenant: bài Mô hình phân quyền.
- **Injection ngoài SQL**:
  - JPQL/HQL ghép chuỗi trong `createQuery("... where name = '" + name + "'")` cũng là injection như SQL. Spring Data `@Query` với `:name` là an toàn. `Sort`/`Pageable` từ request thường an toàn vì Spring Data kiểm tên thuộc tính; nguy hiểm là `JpaSort.unsafe(...)`, native query, và nối chuỗi `ORDER BY` tự viết.
  - Lệnh hệ điều hành: `Runtime.exec("sh -c convert " + file)` cho phép `; rm -rf`. `new ProcessBuilder("convert", file, out)` không qua shell, nhưng vẫn có argument injection: một phần tử khớp tuỳ chọn thật của chương trình (dạng `--output=/tmp/x` với chương trình nhận `--opt=giá_trị`) được hiểu là tuỳ chọn, không phải tên file. ImageMagick còn hiểu tiền tố giả giao thức trong tên file (`msl:`, `@danh_sách`), bài học của ImageTragick. Thêm `--` trước đối số nếu chương trình hỗ trợ, kiểm định dạng, hoặc tự đặt tên file trên server. Trên Windows, chạy `.bat`/`.cmd` thì `cmd.exe` phân tích lại đối số (lớp lỗi BatBadBut).
  - SpEL (đã chạy với spring-expression 7.0.10): `parseExpression(input).getValue(new StandardEvaluationContext(...))` chạy được `T(java.lang.System).getProperty(...)`, tức gọi mọi class (tới `Runtime.exec`). `SimpleEvaluationContext.forReadOnlyDataBinding()` báo `EL1005E: Type cannot be found 'java.lang.System'` nhưng vẫn tính `total > 100`. Không bao giờ đánh giá biểu thức do người dùng gửi bằng `StandardEvaluationContext`.
  - Template injection: để người dùng sửa nội dung template (FreeMarker, Velocity, Thymeleaf) hoặc ghép input vào tên view là cho họ chạy biểu thức trên server. Template do người dùng soạn thì dùng engine không có logic (Mustache) và dữ liệu thuần.
  - LDAP: ghép `"(&(uid=" + user + ")(active=TRUE))"` thì `*` khớp mọi tài khoản, còn `)`, `(`, `|` đổi cấu trúc filter. Dùng `LdapQueryBuilder` của Spring LDAP hoặc encode giá trị filter.
- **XSS theo ngữ cảnh**:
  - Thymeleaf `th:text` escape HTML, `th:utext` thì không. Trong `th:inline="javascript"`, dạng inline hai ngoặc vuông escape theo JavaScript, dạng ngoặc vuông kèm ngoặc tròn `[(${name})]` thì không.
  - Thuộc tính URL: escape HTML không chặn `href="javascript:..."`; kiểm scheme là `https`.
  - React escape mặc định, trừ `dangerouslySetInnerHTML` và URL `javascript:`.
  - Nội dung rich text phải qua sanitizer theo allowlist (OWASP Java HTML Sanitizer), không tự viết regex xoá `<script>`.
  - API JSON vẫn có XSS khi response được trình duyệt hiểu là HTML (lab bên dưới): trả object hoặc [[problem-detail|ProblemDetail]] và khai `produces`. `X-Content-Type-Options: nosniff` chỉ cấm đoán kiểu; nó không giúp được khi chính server khai `text/html`.
  - CSP với nonce giới hạn thiệt hại khi lọt một chỗ (bài Bảo mật phía trình duyệt).
- **SSRF ở tầng ứng dụng Java** (đã chạy JDK 27):
  - Chặn theo chuỗi `"169.254.169.254"` bị vượt: `InetAddress.getByName("2852039166")` ra `169.254.169.254`; `127.1` ra `127.0.0.1`; `::ffff:169.254.169.254` ra `Inet4Address` `169.254.169.254`; `URI` của `http://shop.example.com@169.254.169.254/` có host là `169.254.169.254`.
  - Kiểm địa chỉ đã phân giải: chặn `isLoopbackAddress`, `isLinkLocalAddress`, `isSiteLocalAddress`, `isAnyLocalAddress` (`0.0.0.0` tới được dịch vụ local trên Linux). `isSiteLocalAddress` của IPv6 chỉ đúng với dải cũ `fec0::/10`: `fd00::1` (unique local `fc00::/7`) ra `false`, phải tự kiểm. Còn các dải khác: `100.64.0.0/10` (CGNAT), multicast, IMDS IPv6 của AWS `fd00:ec2::254`. Tự liệt kê dễ sót, nên ưu tiên allowlist.
  - [[dns-rebinding|DNS rebinding]]: kiểm tên miền phân giải ra IP công khai, lúc kết nối lại phân giải ra IP nội bộ. Phân giải một lần, kiểm, rồi kết nối tới đúng IP đó. Đừng thay host bằng IP trong URL (hỏng SNI và kiểm chứng chỉ theo tên); dùng resolver tuỳ biến của client, như `DnsResolver` của Apache HttpClient 5 hay `AddressResolverGroup` của Reactor Netty (`InetAddressResolverProvider` của JDK 18+ áp cho cả JVM). Hoặc đi qua egress proxy có luật chặn dải nội bộ.
  - Redirect: `HttpClient.newHttpClient()` mặc định `Redirect.NEVER`; bật `NORMAL` thì phải kiểm lại từng bước nhảy. RestTemplate/WebClient tuỳ thư viện bên dưới, cần đọc cấu hình thật.
  - Tốt nhất là allowlist tên miền đích (webhook của đối tác đã đăng ký) và mạng chặn chiều ra.
- **A02 Misconfiguration trong Spring Boot**:
  - Actuator mặc định chỉ expose `health` qua HTTP. Mở `*`: từ Boot 3, `/env` che giá trị mặc định (`management.endpoint.env.show-values=never`), nhưng `/heapdump` vẫn chứa secret nằm trong heap, `/loggers` cho đổi log level, `/mappings`, `/beans` lộ cấu trúc (bài Auto-configuration & cấu hình).
  - `server.error.include-stacktrace` và `include-message` mặc định `never`; bật lên ở production là lộ cấu trúc code và câu SQL.
  - Header bảo mật của Spring Security bị tắt cả nhóm khi ai đó gọi `headers(h -> h.disable())` để "sửa lỗi iframe"; chỉ nới đúng `frameOptions`.
  - Swagger UI, H2 console bật trên production; devtools bị đóng gói nhầm vào bản chạy (mặc định plugin Boot loại devtools khỏi jar).
- **A03 chuỗi cung ứng**: dependency có CVE (Log4Shell; Spring4Shell CVE-2022-22965, chỉ dính Spring Framework 5.3.0–5.3.17 và 5.2.0–5.2.19 trên JDK 9+ chạy WAR trong Tomcat; jar chạy độc lập của Boot không dính mặc định), dependency bị chiếm hay giả tên, pipeline build bị sửa. Chống bằng SCA trong CI, khoá phiên bản, [[sbom|SBOM]], ký artifact (bài Bảo mật trong quy trình phát triển; xung đột phiên bản: bài Maven, Gradle & quản lý dependency).
- **A07 xác thực**: credential stuffing, không giới hạn đăng nhập sai, session fixation, khôi phục mật khẩu yếu (bài AuthN & AuthZ cơ bản).
- **A08 toàn vẹn**: deserialize dữ liệu không tin cậy (kẻ tấn công ghép [[gadget-chain|gadget chain]] từ class trên classpath), nạp plugin hay bản cập nhật không kiểm chữ ký, CI dùng action của bên thứ ba không ghim commit.
- **A09 log và cảnh báo**: ghi đủ đăng nhập thất bại, `403`, thay đổi quyền, kèm user, IP, correlation id; có cảnh báo khi tăng đột biến; không ghi mật khẩu, token, dữ liệu cá nhân (bài Dữ liệu cá nhân & tuân thủ). Log không ai đọc thì không phát hiện được gì.
- **A10 xử lý ngoại lệ**:
  - Fail open: `try { return authzClient.check(user, order); } catch (Exception e) { return true; }` biến sự cố của dịch vụ phân quyền thành lỗ hổng. Kiểm tra bảo mật phải fail closed; với tính năng không bảo mật (rate limit, gợi ý) mới cân nhắc fail open.
  - Lỗi giữa chừng của luồng nhiều bước để lại trạng thái nửa vời (đã trừ tiền, chưa tạo đơn): dùng transaction hoặc bù trừ.
  - Exception không được giải phóng tài nguyên: dùng try-with-resources.
  - Thông báo lỗi khác nhau theo nhánh làm lộ thông tin (tài khoản tồn tại, câu SQL).
- **WAF** chặn được mẫu tấn công phổ biến và mua thời gian khi chờ vá CVE, nhưng không hiểu nghiệp vụ: IDOR, lỗi phân quyền, logic thanh toán đi qua WAF như request bình thường.
