## Quick

[[auto-configuration|Auto-configuration]] là các class `@AutoConfiguration` mà Boot nạp từ file `AutoConfiguration.imports` trong mỗi jar, mỗi class gắn [[conditional-annotation|điều kiện]] như `@ConditionalOnClass`, `@ConditionalOnMissingBean`. **Boot xét chúng sau cấu hình của bạn, nên bean bạn tự khai báo luôn thắng.** Giá trị cấu hình đến từ nhiều nguồn có thứ tự ưu tiên cố định: tham số dòng lệnh thắng biến môi trường, biến môi trường thắng `application.yml`. Gói chúng vào class [[configuration-properties|`@ConfigurationProperties`]] thay vì rải `@Value`.

## Interview

**Auto-configuration chạy thế nào**:
- `@SpringBootApplication` gồm `@EnableAutoConfiguration`. Nó đọc danh sách ứng viên từ `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` (Boot 2.7+; trước đó là `spring.factories`, và Boot 3.0 bỏ hẳn việc đọc auto-configuration từ `spring.factories`).
- Ứng viên được xử lý **sau** mọi cấu hình của bạn. Mỗi ứng viên chỉ thêm bean khi điều kiện đúng:
  - `@ConditionalOnClass(DataSource.class)`: thư viện có trên classpath.
  - `@ConditionalOnProperty(prefix = "app.audit", name = "enabled")`: có cấu hình bật.
  - `@ConditionalOnMissingBean`: bạn chưa tự khai báo bean đó.
- Muốn biết vì sao một bean có hay không có: chạy với `--debug` để in condition evaluation report, hoặc xem `/actuator/conditions`. Tắt hẳn một auto-configuration bằng `spring.autoconfigure.exclude`.

**Thứ tự nguồn cấu hình**, ưu tiên từ cao xuống:
1. Tham số dòng lệnh (`--server.port=9090`).
2. `SPRING_APPLICATION_JSON`.
3. Java system property (`-D`).
4. Biến môi trường (`SERVER_PORT`).
5. File cấu hình, từ cao xuống: `application-prod.yml` ngoài jar, `application.yml` ngoài jar, `application-prod.yml` trong jar, `application.yml` trong jar. File ngoài jar luôn thắng file trong jar, kể cả file theo profile.
6. `@PropertySource` và giá trị mặc định.

**[[spring-profile|Profile]]** chọn file và bean theo môi trường: `spring.profiles.active=prod` nạp thêm `application-prod.yml` và bật các bean `@Profile("prod")`.

**`@ConfigurationProperties`**: bind cả nhóm `order.retry.*` vào một record có kiểu, hỗ trợ [[relaxed-binding|relaxed binding]] (`ORDER_RETRY_MAXATTEMPTS` khớp `order.retry.max-attempts`), và thêm `@Validated` để sai cấu hình là không khởi động được.

**[[actuator|Actuator]]**: mặc định chỉ expose `health` qua HTTP. Mở `*` ra Internet là lộ `/env`, `/loggers` và, ở bản Boot cũ hoặc khi đã nới quyền truy cập, `/heapdump` (heap chứa password, token đang nằm trong bộ nhớ). Nên đặt Actuator ở port quản trị riêng, không mở qua ingress công khai.

## Deep

- **Bean của bạn tắt cả nhóm cấu hình**: tự khai báo `DataSource` thì `spring.datasource.hikari.*` không còn được áp vào pool, vì các property đó chỉ được bind cho bean Boot tạo. Muốn giữ binding, gắn `@ConfigurationProperties("spring.datasource.hikari")` lên method `@Bean` của bạn (xem lab).
- **`@ConditionalOnMissingBean` phụ thuộc thứ tự**: nó chỉ thấy bean đã được đăng ký *tới lúc đó*. Trong auto-configuration thì an toàn vì Boot xử lý chúng sau cùng và sắp xếp bằng `@AutoConfiguration(after = ...)`. Dùng nó trong `@Configuration` của ứng dụng thì kết quả tuỳ thứ tự scan.
- **`@ConditionalOnClass` không nạp class**: Spring đọc annotation bằng ASM, nên tham chiếu tới class không có trên classpath vẫn an toàn ở mức class. Nhưng kiểu trả về của method `@Bean` thì được nạp, nên auto-configuration của Boot tách phần phụ thuộc thư viện tuỳ chọn vào class lồng có điều kiện riêng.
- **Boot 4 chia nhỏ module**: auto-configuration nằm trong module riêng theo công nghệ (ví dụ `DataSourceProperties` chuyển sang package `org.springframework.boot.jdbc.autoconfigure`). Code import class của Boot hay `exclude` theo tên class cần sửa khi nâng cấp.
- **Tự viết starter**: một module autoconfigure (class `@AutoConfiguration`, khai báo trong file `.imports`) và một module starter chỉ chứa dependency. Mọi bean gắn `@ConditionalOnMissingBean` để người dùng ghi đè được. Không dùng component scan trong starter, vì nó quét cả package của ứng dụng dùng starter.
- **Biến môi trường**: quy tắc là đổi `.` thành `_`, bỏ `-`, viết hoa: `spring.datasource.hikari.maximum-pool-size` thành `SPRING_DATASOURCE_HIKARI_MAXIMUMPOOLSIZE`. Phần tử list dùng chỉ số: `APP_SERVERS_0_HOST`. `@Value("${...}")` chỉ có relaxed binding hạn chế; `@ConfigurationProperties` thì đầy đủ.
- **Gõ sai tên property không báo lỗi**: `@ConfigurationProperties` mặc định bỏ qua field lạ, nên `order.retry.max-attemps` âm thầm không có tác dụng. Thêm `spring-boot-configuration-processor` để IDE cảnh báo, và khi nâng Boot thì chạy tạm `spring-boot-properties-migrator` để nó in ra các property đã đổi tên.
- **Config data (Boot 2.4+)**: `spring.config.import` nạp thêm nguồn (file, `configtree:` cho secret Kubernetes mount thành file, Vault, Config Server). Trong file YAML nhiều document, `spring.config.activate.on-profile` thay cho `spring.profiles` cũ. Tiền tố `optional:` để không lỗi khi nguồn chưa có.
- **Secret**: không để trong `application.yml` commit vào git. Dùng biến môi trường, `configtree:` hoặc secret manager. Từ Boot 3.0, `/env` và `/configprops` che giá trị mặc định (`show-values: never`), nhưng `/heapdump` vẫn lộ mọi thứ trong bộ nhớ.
- **Liveness và readiness**: Boot có sẵn `/actuator/health/liveness` và `/actuator/health/readiness` (Boot 2.3–3.x chỉ tự bật khi phát hiện chạy trên Kubernetes; Boot 4 bật luôn, tắt bằng `management.endpoint.health.probes.enabled`). Mặc định readiness chỉ gồm `readinessState`; muốn thêm database thì khai báo `management.endpoint.health.group.readiness.include=readinessState,db`. Đừng đưa health của database vào liveness: database chậm làm mọi pod bị restart cùng lúc và hệ thống sập thành dây chuyền. Database thuộc về readiness, nếu có.
- **Profile**:
  - Nhóm profile (`spring.profiles.group.prod=db-postgres,metrics`) gom nhiều profile.
  - Đặt `spring.profiles.active` (hay `include`, `group`) trong file theo profile làm Boot ném `InvalidConfigDataPropertyException` lúc khởi động.
  - Dùng profile cho khác biệt hạ tầng. Đừng dùng cho logic nghiệp vụ (`if prod`), vì code chạy trên test và trên production sẽ khác nhau.
- **Xem khởi động mất thời gian ở đâu**: dùng `BufferingApplicationStartup` cùng endpoint `/actuator/startup`, hoặc JFR, để thấy bước nào chậm khi khởi động mất cả chục giây.
