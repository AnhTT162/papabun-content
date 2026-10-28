## Quick

Một service Java khởi động chậm vì ba việc: nạp và liên kết hàng nghìn class, framework dựng context (quét, đánh giá điều kiện, tạo proxy), rồi [[jit-warmup|warmup]] của JIT. **Mỗi kỹ thuật dời một phần việc sang lúc build: [[class-data-sharing|CDS]] và [[aot-cache|AOT cache]] lưu class đã nạp (và profile), [[spring-aot|Spring AOT]] sinh sẵn bean definition, [[crac|CRaC]] chụp lại cả JVM đã chạy, [[native-image|native image]] biên dịch trước toàn bộ. Dời càng nhiều thì khởi động càng nhanh nhưng build càng phức tạp và càng mất tính động lúc chạy.** Đo trước khi chọn, vì nhiều service chậm do chờ database chứ không do JVM.

## Interview

**Đo trước**: thời gian khởi động gồm JVM nạp class, Spring dựng context, và kết nối ra ngoài (pool database, migration, Kafka). [[actuator|Actuator]] `/actuator/startup` (cần đăng ký `BufferingApplicationStartup`) cho thời gian từng bước của Spring; `-Xlog:class+load` cho số class. Nếu phần lớn thời gian là chờ migration thì không kỹ thuật JVM nào giúp được.

**CDS và AOT cache** (giữ nguyên JVM): một [[training-run|training run]] ghi lại class đã nạp và liên kết vào một file; lần sau JVM map file đó thay vì đọc và kiểm tra lại từng class. CDS có từ lâu và dùng được trên JDK 21; từ JDK 25, AOT cache lưu thêm profile để JIT biên dịch sớm hơn. Trên một app Spring Boot 4.1 nhỏ (JDK 27): 0,70 giây xuống 0,34 giây. Cache gần như vô ích với fat jar nên phải giải nén, và chỉ được dùng khi cùng bản JDK, cùng chế độ compressed oops và đúng các file jar lúc tạo cache.

**Spring AOT**: sinh code đăng ký bean lúc build. Đổi lại, `@Profile` và `@ConditionalOnProperty` bị chốt lúc build.

**CRaC**: chụp tiến trình JVM đã khởi động (cả mã JIT đã biên dịch) rồi restore trong vài chục mili giây. Chỉ có trên Linux, cần bản JDK có CRaC và quyền của CRIU. File chụp chứa mọi thứ trong bộ nhớ, kể cả secret.

**Native image (GraalVM)**: biên dịch trước thành file chạy với giả định [[closed-world-assumption|closed world]]. Khởi động vài chục mili giây và [[rss|RSS]] nhỏ, nhưng build mất vài phút, reflection và proxy phải khai báo trước ([[reachability-metadata|reachability metadata]]), không có JIT nên tốc độ đỉnh thường thấp hơn, và không gắn được `-javaagent`.

**Chọn**: service chạy lâu trên Kubernetes thì dùng AOT cache (hoặc CDS trên JDK 21) cộng warmup trước khi báo ready. Cần [[cold-start|cold start]] dưới một giây cho function hay CLI thì xét native image hoặc snapshot (CRaC, Lambda SnapStart).

## Deep

- **Số đo** (Spring Boot 4.1.2, webmvc + actuator, JDK 27, Apple M4; giây là dòng `Started ... in`, RSS đo trên macOS sau 200 request, chỉ để so tương đối; trên container Linux số tuyệt đối sẽ khác):

  | Cách chạy | Khởi động | RSS |
  |---|---|---|
  | Fat jar `java -jar` | 0,80 s | khoảng 335 MB |
  | Jar đã giải nén | 0,70 s | khoảng 265 MB |
  | Giải nén + CDS động | 0,48 s | khoảng 215 MB |
  | Giải nén + AOT cache | 0,34 s | khoảng 210 MB |
  | Giải nén + Spring AOT | 0,53 s | khoảng 235 MB |
  | Spring AOT + AOT cache | 0,23 s | khoảng 200 MB |

  Không có cache, 1.448 class nạp từ CDS mặc định của JDK và 6.187 class nạp thường. Với CDS động là 7.193/307, với AOT cache 7.640/302 (từ archive/nạp thường; tổng mỗi lần lệch nhau vì một số class được sinh lúc chạy).
- **Lịch sử CDS**: [[class-data-sharing|CDS]] cho class của JDK có từ lâu. AppCDS (class của ứng dụng) mở cho OpenJDK từ JDK 10 (JEP 310). JDK 12 bật sẵn archive mặc định (JEP 341); đo trên JDK 27, M4: Hello World mất 23 ms, với `-Xshare:off` mất 35 ms. JDK 13 thêm archive động `-XX:ArchiveClassesAtExit` (JEP 350), JDK 19 thêm `-XX:+AutoCreateSharedArchive`.
- **AOT cache (Project Leyden)**:
  - JDK 24 (JEP 483) lưu class đã nạp và liên kết, tạo bằng hai bước `-XX:AOTMode=record` rồi `-XX:AOTMode=create`.
  - JDK 25 (JEP 514) gộp thành một bước `-XX:AOTCacheOutput=app.aot`: JVM chạy app, rồi khi thoát tự gọi một tiến trình con để ghi cache, nên training lâu hơn: đã đo 2,6 giây, so với 1,3 giây khi tạo archive CDS động.
  - JDK 25 (JEP 515) lưu thêm profile của method. JDK 26 (JEP 516) thêm định dạng cache object không phụ thuộc GC, nhưng định dạng này chỉ được tạo khi training chạy với ZGC, `-XX:-UseCompressedOops` hoặc heap trên khoảng 32 GB. Cache tạo với G1 và compressed oops vẫn gắn với chế độ đó (xem dưới).
  - JDK 27 chưa lưu mã máy đã biên dịch của method ứng dụng (không có cờ product cho việc này trên bản đã thử; có thể đổi ở bản sau).
- **Training ở đâu**: Spring Boot hướng dẫn `-Dspring.context.exit=onRefresh`: Spring dựng xong bean rồi thoát, chưa nhận request. Cách này nhanh nhưng profile chỉ có phần khởi động.
  - Đã thử chạy training với 3.000 request thật rồi tắt bằng SIGTERM. Cache lên 71 MB thay vì 61 MB. Request POST đầu tiên còn 5 ms thay vì 14 ms (không cache: 17 ms). Thời gian khởi động không đổi.
  - Cache 61–71 MB nằm trong image, làm image to hơn và phải tạo lại mỗi lần build.
  - Bean tạo kết nối ngay khi khởi tạo (Flyway, `EntityManagerFactory` kiểm schema, client Kafka) sẽ cần database và broker ngay trong lúc build image. Phải tắt chúng trong profile training hoặc cấp môi trường giả.
- **Cache bị bỏ lặng lẽ**: JVM kiểm kích thước và thời gian sửa của từng jar trên classpath. Đã thử:
  - Copy thư mục mà không giữ timestamp: `This file is not the one used while building the AOT cache: ..., timestamp has changed` rồi `Unable to map shared spaces`. App vẫn chạy, chỉ chậm như không có cache.
  - Cache tạo với [[g1-gc|G1]] (có [[compressed-oops|compressed oops]]) mà chạy với [[zgc|ZGC]]: `The saved state of UseCompressedOops (1) is different from runtime (0), CDS will be disabled`. Khởi động 0,74 giây. Chạy Serial GC với cùng cache thì vẫn dùng được (0,35 giây). Tăng heap lên trên khoảng 32 GB cũng tắt compressed oops nên cũng làm cache bị bỏ.
  - Java agent chỉ có lúc chạy mà không có lúc training: `Mismatched values for property jdk.module.addmods: java.instrument specified during runtime but not during dump time`, khởi động 0,71–0,85 giây. Thêm cùng agent (agent thử không đổi class nào) vào cả training thì cache dùng được, 0,35 giây. Agent thật biến đổi class (OpenTelemetry) thì class bị đổi không vào được cache; phải đo với đúng agent.
  - Khác bản JDK cũng bị từ chối, nên cache phải tạo bằng đúng image JDK chạy production: tạo ngay trong Dockerfile ở stage cuối.
  - `-XX:AOTMode=required` (JDK 27 đổi tên từ `on`, `on` vẫn được nhận) biến các lỗi này thành `unrecoverable error` và JVM không khởi động. Hữu ích cho bài test khởi động trong CI, rủi ro nếu đặt ở production.
- **[[fat-jar|Fat jar]]**: class trong jar lồng nhau được launcher của Spring Boot nạp bằng [[classloader|classloader]] riêng, cache không chứa được (bài ClassLoader). Đã đo: AOT cache tạo từ fat jar chỉ nạp được 2.648 class từ cache, 5.169 nạp thường, khởi động 0,73 giây. Giải nén bằng `java -Djarmode=tools -jar app.jar extract` (Boot 3.3+) trước khi training và khi chạy.
- **Spring AOT trên JVM**: bật plugin `process-aot`, chạy với `-Dspring.aot.enabled=true` (log ghi `Starting AOT-processed`). Điều kiện được đánh giá lúc build: đã thử bean `@ConditionalOnProperty(name = "audit.enabled")`, build khi chưa đặt thuộc tính, lúc chạy đặt `audit.enabled=true` thì bean vẫn không được tạo. Muốn bật tắt lúc chạy thì kiểm tra cờ bên trong bean, hoặc build riêng cho từng cấu hình.
- **[[crac|CRaC]]**:
  - **Cơ chế**: dùng CRIU để lưu toàn bộ tiến trình xuống file. Spring hỗ trợ từ Framework 6.1 / Boot 3.2: trước khi chụp, bean `Lifecycle` được `stop` (đóng pool, socket); sau khi restore thì `start` lại. Thư viện không dùng Spring cài `org.crac.Resource`.
  - **Hai cách chụp**: `-Dspring.context.checkpoint=onRefresh` chụp lúc khởi động, chưa có mã JIT nóng. `jcmd <pid> JDK.checkpoint` chụp app đã warmup, restore là chạy ở tốc độ đỉnh ngay.
  - **Bẫy**:
    - Socket hay file còn mở thì không chụp được.
    - Mọi bản restore bắt đầu từ cùng một bộ nhớ: ID instance, seed ngẫu nhiên, token, cache đã nạp đều giống nhau.
    - `@Scheduled(fixedRate)` chạy bù các lần lỡ giữa lúc chụp và lúc restore (tài liệu Spring khuyên dùng `fixedDelay`).
    - File chụp chứa secret, phải bảo vệ như secret.
    - CPU lúc restore phải có các tính năng mà CPU lúc chụp có.
    - Pod cần quyền mà nhiều cluster không cấp.
  - **Lambda SnapStart**: chụp microVM sau khi init và gọi các hook `org.crac`. Ý tưởng giống CRaC nhưng nền tảng lo phần chụp, và có cùng bẫy về trạng thái dùng chung.
- **[[native-image|Native image]]**:
  - **Build**: phân tích tĩnh từ `main` để giữ lại phần dùng tới, chạy một phần static initializer lúc build và lưu heap ban đầu vào file chạy.
  - **Reflection, proxy, resource** cần [[reachability-metadata|metadata]] (định dạng gộp mới `reachability-metadata.json` trong `META-INF/native-image/`; bản GraalVM cũ dùng các file `reflect-config.json`, `proxy-config.json`, `resource-config.json`). Spring AOT sinh phần của Spring. Thư viện thì lấy từ GraalVM Reachability Metadata Repository hoặc ghi bằng tracing agent `-agentlib:native-image-agent`.
  - **Thiếu metadata** lộ ra lúc chạy, ở nhánh ít chạy. Phải chạy test trên bản native (`nativeTest`), không chỉ trên JVM.
  - **GC**: mặc định Serial GC. G1 chỉ có ở Oracle GraalVM trên Linux x64 và AArch64; Community Edition không có.
  - **Tốc độ đỉnh**: không có JIT theo profile nên thường thấp hơn C2 với service chạy lâu. PGO của Oracle GraalVM (`--pgo-instrument`, `--pgo`) thu hẹp khoảng cách.
  - **Build**: mất vài phút và vài GB RAM, build cho từng hệ điều hành và kiến trúc (máy Mac không build ra binary Linux).
  - **Chẩn đoán**: heap dump, [[jfr|JFR]], NMT và `jcmd` phải bật lúc build (`--enable-monitoring`). Agent `-javaagent` (ví dụ OpenTelemetry Java agent) không gắn được lúc chạy.
- **Đừng nhầm các mẹo**: `-XX:TieredStopAtLevel=1` (bài JIT compiler) khởi động nhanh hơn chút nhưng mất C2; `-Xshare:off` (hay gặp trong cấu hình cũ) bỏ cả CDS mặc định; lazy initialization của Spring chỉ dời lỗi cấu hình sang request đầu (bài Spring, Spring Boot & hệ sinh thái).
- **Kubernetes**: khởi động nhanh không thay được warmup và [[startup-probe|startup probe]] (`startupProbe`). CPU limit lúc khởi động, `startupProbe` ở bài JVM trong container. Slow start ở load balancer và [[hpa|HPA]] ở bài Capacity planning & autoscaling.
