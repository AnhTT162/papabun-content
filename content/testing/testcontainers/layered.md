## Quick

[[testcontainers|Testcontainers]] cho [[integration-test|integration test]] chạy với phụ thuộc thật: nó khởi động (PostgreSQL, Kafka, Redis) trong container Docker ngay từ code test, map cổng ngẫu nhiên và tự dọn khi JVM test kết thúc. **Test chạy trên đúng engine và phiên bản như production** thay vì cơ sở dữ liệu nhúng giả lập như H2. Giá phải trả là cần Docker và vài giây khởi động, nên **khởi động một lần cho cả suite và cô lập dữ liệu giữa các test**.

## Interview

**Vì sao không dùng H2**: H2, kể cả ở `MODE=PostgreSQL`, vẫn khác PostgreSQL ở nhiều chỗ: thứ tự `NULL` khi sắp xếp, collation khi `ORDER BY` chuỗi, `jsonb`, `SKIP LOCKED`, partial index, cách khoá. Test xanh trên H2 không chứng minh query chạy đúng trên PostgreSQL. Migration Flyway hay Liquibase cũng chỉ được kiểm thật khi chạy trên engine thật.

**Chạy thế nào**: thư viện gọi Docker API, kéo image, start container với cổng ngẫu nhiên trên máy, chờ theo [[wait-strategy|wait strategy]] (dòng log "ready to accept connections", cổng mở, health check), rồi đưa JDBC URL cho test. Container phụ [[ryuk|Ryuk]] xoá các container khi JVM test kết thúc, kể cả khi JVM bị kill.

**Vòng đời**: với `@Testcontainers`, field `@Container` `static` dùng một container cho cả class, field thường thì mỗi method một container (chậm). Mẫu [[singleton-container|singleton container]]: start trong khối `static` của class cha, mọi class test dùng chung, Ryuk dọn khi suite xong.

**Với Spring Boot**: `@ServiceConnection` (từ 3.1, trong `spring-boot-testcontainers`) tự cấu hình datasource, Kafka, Redis từ container, thay cho `@DynamicPropertySource` viết tay.

**Cô lập dữ liệu**: container dùng chung thì test không được dẫm lên nhau. Ba cách: rollback transaction cuối mỗi test, xoá dữ liệu trong `@BeforeEach`, hoặc mỗi test dùng dữ liệu riêng (id, tenant ngẫu nhiên).

**Bẫy hay gặp**: image khác phiên bản production (hay dùng `latest`); container theo class trong khi Spring cache context trỏ vào container đã dừng; bật reuse trên CI; chạy song song với extension `@Testcontainers` (tài liệu ghi chưa hỗ trợ).

## Deep

- **Testcontainers 2.0** (Spring Boot 4.0 quản lý 2.0.2, Spring Boot 3.5 quản lý 1.21.0): bỏ phụ thuộc JUnit 4 (`GenericContainer` không còn implements `TestRule`); artifact module đổi tên có tiền tố (`testcontainers-postgresql`, `testcontainers-junit-jupiter`); class mới nằm trong package theo module (`org.testcontainers.postgresql.PostgreSQLContainer`, không còn generic), class cũ `org.testcontainers.containers.PostgreSQLContainer` vẫn còn nhưng deprecated. Constructor mới bắt buộc truyền image.
- **Ghim image**: dùng `postgres:17.6` cùng phiên bản production, không `latest`. Hằng `DEFAULT_TAG` của `PostgreSQLContainer` vẫn là `9.6.12`; đừng dựng image từ nó. CI hay gặp giới hạn lượt kéo của Docker Hub: đặt `hub.image.name.prefix` trong `~/.testcontainers.properties` để kéo qua registry nội bộ.
- **Container theo class và cache context của Spring**: `@Container static` bị dừng sau class đầu tiên, nhưng `ApplicationContext` được cache vẫn giữ URL cũ, nên class sau dùng lại context gặp "Connection refused". Dùng singleton container, hoặc khai báo container là `@Bean @ServiceConnection` trong `@TestConfiguration` để vòng đời của nó gắn với context.
- **Reuse** (thử nghiệm): `withReuse(true)` cộng `testcontainers.reuse.enable=true` trong `~/.testcontainers.properties` hoặc biến môi trường `TESTCONTAINERS_REUSE_ENABLE` (không đặt trong file trên classpath được). Container không bị dừng sau khi test xong, lần chạy sau có cùng cấu hình dùng lại nó. Tiết kiệm thời gian trên máy dev, nhưng dữ liệu còn từ lần trước và tài liệu ghi rõ không hợp với CI.
- **Nhanh hơn**: cache image trên runner CI; cho PostgreSQL chạy dữ liệu trên tmpfs và tắt `fsync` (`withCommand("postgres", "-c", "fsync=off")`), vì test không cần bền khi mất điện; chạy migration một lần cho cả suite. Migration Flyway hay Liquibase chạy trên container chính là test cho migration.
- **Cô lập dữ liệu, cái giá của từng cách**: rollback nhanh nhưng giấu lỗi chỉ lộ khi flush hoặc commit (constraint trì hoãn, trigger lúc commit); xoá bảng thì giống thật hơn nhưng chậm hơn; dữ liệu riêng mỗi test chạy song song được nhưng phải viết assert chỉ nhìn dữ liệu của mình. Chi tiết về transaction trong test ở bài Spring Boot Test.
- **Docker trên CI**: runner Ubuntu của GitHub Actions có sẵn Docker; GitLab dùng service `docker:dind` với `DOCKER_HOST=tcp://docker:2375`; runner trên Kubernetes cần DinD sidecar chạy privileged hoặc Docker từ xa (Testcontainers Cloud). Trên máy dev có thể dùng Docker Desktop, Colima, hoặc Podman qua socket tương thích Docker.
- **Ryuk**: một số môi trường không cho chạy container privileged; tắt bằng `TESTCONTAINERS_RYUK_DISABLED=true` chỉ khi môi trường tự xoá mọi thứ sau mỗi job, nếu không container sẽ tồn đọng.
- **JDBC URL đặc biệt**: `jdbc:tc:postgresql:17.6:///shop` để driver của Testcontainers tự start container lúc mở kết nối đầu, không cần code; tiện cho cấu hình sẵn, nhưng khó điều khiển vòng đời hơn.
- **Ngoài database**: `org.testcontainers.kafka.KafkaContainer` (image `apache/kafka`, chế độ KRaft), Redis, LocalStack cho dịch vụ AWS, Keycloak, module Docker Compose. Với HTTP downstream, thường WireMock (bài Test HTTP client với WireMock) nhẹ hơn chạy service thật.
- **Song song**: mỗi JVM fork của Surefire (`forkCount`) có singleton riêng, nên N fork là N container PostgreSQL. Muốn chạy song song trong một container thì cô lập theo schema hoặc database cho mỗi fork.
- **Chạy app cục bộ với container**: Spring Boot 3.1+ cho `SpringApplication.from(ShopApplication::main).with(ContainersConfig.class).run(args)` trong `src/test`, để dev chạy app với cùng PostgreSQL, Kafka như trong test mà không cài gì.
