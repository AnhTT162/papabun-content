## Quick

[[spring-framework|Spring Framework]] là nền: một container ([[application-context|ApplicationContext]]) tạo và nối các object (gọi là [[bean]]), cộng các module transaction, web, data, test. [[spring-boot|Spring Boot]] **không phải framework khác** mà là lớp cấu hình sẵn đặt trên Spring Framework: [[spring-boot-starter|starter]] gom dependency đúng phiên bản, [[auto-configuration]] tạo bean mặc định khi bạn chưa tự khai báo, [[embedded-server|server nhúng]] và [[fat-jar|executable jar]] để chạy bằng `java -jar`. **Mọi thứ Boot làm, bạn đều ghi đè được.**

## Interview

**Spring Framework** giải quyết việc ghép các thành phần: thay vì `new` và tự nối object, bạn khai báo bean, container tạo và inject dependency (bài IoC & Dependency Injection). Trên nền đó là các module: AOP và proxy (nền của `@Transactional`, `@Async`, `@Cacheable`), transaction abstraction, Spring MVC và WebFlux, JDBC, test.

**Spring Boot** giải quyết việc cấu hình:
- **Starter**: `spring-boot-starter-web` (Boot 4 đổi tên thành `spring-boot-starter-webmvc`, tên cũ vẫn dùng được nhưng bị deprecated) kéo Spring MVC, Jackson, Tomcat. Phiên bản do [[bom|BOM]] `spring-boot-dependencies` quản lý, nên bạn không ghi version cho từng thư viện.
- **Auto-configuration**: có `spring-jdbc` và [[hikaricp|HikariCP]] trên classpath (nhờ starter JDBC) cùng `spring.datasource.url` thì Boot tạo connection pool; bạn tự khai báo bean `DataSource` thì Boot lùi lại (bài Auto-configuration & cấu hình).
- **Server nhúng**: Tomcat chạy bên trong process của ứng dụng, không deploy WAR vào server có sẵn.
- **Cấu hình ngoài và vận hành**: `application.yml`, profile, biến môi trường; [[actuator|Actuator]] cho health check và metric.

**Phiên bản đi theo cặp**:
- Boot 2.x chạy trên Framework 5.x, Java 8+, package `javax.*`.
- Boot 3.x chạy trên Framework 6.x, cần Java 17+, chuyển sang [[jakarta-namespace|`jakarta.*`]].
- Boot 4.x chạy trên Framework 7.x, vẫn Java 17+, lên Jakarta EE 11 và Jackson 3.

Nâng từ 2 lên 3 khó nhất vì đổi namespace: mọi thư viện còn dùng `javax.servlet` hay `javax.persistence` đều phải có bản mới.

**Bẫy hay gặp**: tự ghi đè version của một module Spring, hoặc dùng Spring Cloud không khớp Boot. Ứng dụng vẫn build được nhưng chết lúc khởi động với `NoSuchMethodError` hay `ClassNotFoundException`. Cách làm đúng là để BOM quản lý version, và chọn bản Spring Cloud theo bảng tương thích của nó.

## Deep

- **Starter chỉ là `pom` gom dependency**, gần như không có code. Logic nằm ở module autoconfigure. Boot 4 chia autoconfigure thành nhiều module nhỏ theo công nghệ, nên dependency của bạn quyết định chính xác những gì được cấu hình. Khi nâng từ Boot 3, có thể dùng tạm các starter "classic" (như `spring-boot-starter-classic`) để có classpath gần giống Boot 3, rồi chuyển dần sang starter theo từng công nghệ.
- **Ghi đè version đúng cách**: với `spring-boot-starter-parent`, đặt property như `<jackson-bom.version>`; dùng Gradle thì `platform(...)` hoặc plugin `io.spring.dependency-management`. Không khai báo version trực tiếp cho thư viện mà BOM đã quản lý, trừ khi biết rõ tương thích.
- **Không dùng được parent pom** (công ty đã có parent riêng): import `spring-boot-dependencies` với `<scope>import</scope>` trong `dependencyManagement`. Khi đó mất phần cấu hình plugin của parent, phải tự khai báo `spring-boot-maven-plugin`.
- **Executable jar**: `spring-boot-maven-plugin` đóng gói thành jar có `BOOT-INF/classes`, `BOOT-INF/lib` chứa jar khác lồng bên trong, và một launcher đọc các jar lồng đó. Java bình thường không đọc được jar lồng jar; launcher của Boot làm việc này (từ 3.2 dùng `org.springframework.boot.loader.launch.JarLauncher`). Classloader riêng này là nguồn của một số lỗi chỉ xuất hiện khi chạy jar mà không xuất hiện trong IDE (bài ClassLoader).
- **Docker**: copy nguyên fat jar làm mỗi lần đổi một dòng code là phải đẩy lại cả trăm MB. Jar của Boot chia được thành 4 layer mặc định (`dependencies`, `spring-boot-loader`, `snapshot-dependencies`, `application`) qua `java -Djarmode=tools -jar app.jar extract --layers` (Boot 3.3+; bản cũ dùng `jarmode=layertools`), để layer thư viện được cache.
- **Server nhúng**: mặc định Tomcat; đổi sang Jetty bằng cách loại Tomcat khỏi starter và thêm starter Jetty. Boot 4 bỏ hỗ trợ Undertow. Tomcat mặc định tối đa 200 thread xử lý request (`server.tomcat.threads.max`); từ Boot 3.2 với Java 21 có thể bật `spring.threads.virtual.enabled=true` để xử lý request bằng [[virtual-thread|virtual thread]].
- **Vẫn deploy WAR được**: kế thừa `SpringBootServletInitializer`, đổi packaging sang `war`, đánh dấu starter Tomcat là `provided`. Hay gặp ở hệ thống bắt buộc chạy trên application server có sẵn.
- **Khởi động chậm**: ứng dụng Boot trung bình mất vài giây vì quét classpath, đánh giá điều kiện và tạo proxy lúc chạy. Các hướng giảm: lazy initialization (`spring.main.lazy-initialization`, nhưng lỗi cấu hình chỉ lộ ra ở request đầu), CDS (Boot 3.3+), và [[native-image|GraalVM native image]] với AOT của Spring 6+ (khởi động trong vài chục mili giây, đổi lại build lâu, reflection và proxy phải biết trước lúc build).
- **Lịch phát hành**: Boot ra minor mới vào khoảng tháng 5 và tháng 11 mỗi năm; mỗi minor được hỗ trợ miễn phí ít nhất 12 tháng, sau đó chỉ còn hỗ trợ thương mại. 3.5 là bản 3.x cuối và đã hết hỗ trợ miễn phí, nên hệ thống còn ở 3.x cần lên kế hoạch nâng lên 4.x. Một hệ thống không nâng Boot trong hai năm là đang chạy bản không còn bản vá bảo mật miễn phí.
- **Hệ sinh thái**: Spring Data (JPA, JDBC, Redis, MongoDB), Spring Security, Spring Cloud (Gateway, OpenFeign, Config), Spring Batch, Spring for Apache Kafka, Spring AMQP, Spring Modulith, Spring AI. Mỗi project có version riêng nhưng Boot quản lý phần lớn qua BOM; Spring Cloud là ngoại lệ, có BOM riêng theo release train.
- **So với Quarkus và Micronaut**: hai framework này làm nhiều việc của DI lúc build thay vì lúc chạy, nên khởi động nhanh và tốn ít bộ nhớ hơn Spring chạy trên JVM. Spring thu hẹp khoảng cách bằng AOT và native image, và vẫn có hệ sinh thái lớn nhất.
