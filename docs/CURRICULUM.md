# Curriculum PapaBun

Danh sách bài cho cả 15 track, đi từ nền tảng tới nâng cao, kèm tiêu chuẩn "chuyên sâu" mà mọi bài phải đạt. Đây là nguồn chính để chọn bài tiếp theo, trên cả máy cá nhân lẫn máy công ty.

- ✅ đã phát hành hoặc đã merge · ⬜ chưa viết.
- `id` là đề xuất. Được đổi trước khi bài phát hành; **phát hành rồi thì không đổi**.
- Viết xong một bài: đổi ⬜ thành ✅ trong cùng commit với bài đó. `scripts/validate` kiểm tra điều này.

## 1. Tiêu chuẩn chuyên sâu

Một bài chỉ được coi là xong khi trả lời được cả câu hỏi gốc lẫn các câu hỏi nối tiếp mà người phỏng vấn cấp senior/SA sẽ hỏi. Ví dụ, bài Index không dừng ở "B-tree tìm O(log n)": người phỏng vấn sẽ hỏi tiếp về composite index, covering index, cách đọc plan, rồi tới bảng partition và global/local index.

Checklist cho mỗi bài:

1. **Cơ chế bên trong**: không chỉ "là gì" mà "chạy thế nào", tới mức giải thích được hành vi lạ (ví dụ vì sao `==` lúc đúng lúc sai, vì sao EAGER vẫn N+1).
2. **Khác biệt giữa các hệ và phiên bản**: PostgreSQL và MySQL (và Oracle khi liên quan), Java 8/17/21, Spring Boot 2/3, Hibernate 5/6. Ghi rõ phiên bản khi hành vi phụ thuộc phiên bản.
3. **Bẫy production**: lỗi hay gặp, triệu chứng nhìn thấy (log, metric, plan), cách phát hiện sớm (test, cảnh báo).
4. **Trade-off và khi nào không dùng**: mỗi giải pháp có giá; nêu khi nào nó là lựa chọn sai.
5. **Câu hỏi nối tiếp**: ít nhất một callout `interview` cho câu hỏi đào sâu hay gặp.
6. **Thực hành**: ít nhất một block tương tác (breakLab, scenario, troubleshoot, simulation hoặc diagram) dựa trên tình huống như thật.
7. **Liên kết**: `prerequisites` tới bài nền, và nhắc tới bài liên quan khi chạm chủ đề của nó.

**Bài nền (foundation/junior) cũng phải sâu**, nhưng theo kiểu khác: ngắn hơn (8–12 phút), giải thích tận gốc khái niệm mà người đi làm lâu năm hay dùng theo thói quen nhưng chưa hiểu kỹ (ví dụ `Integer` cache, `NULL` trong SQL, CIDR). Bài nền không được lướt qua chỉ vì "ai cũng biết".

**Quá dài thì tách bài.** Phần Interview giới hạn 200–350 từ. Khi một chủ đề không vừa (như Index → Partitioning & Global/Local Index), tách thành bài riêng thay vì nhồi vào Deep, và thêm bài mới vào danh sách dưới đây.

## 2. Ba tầng kiến thức

Mỗi track đi qua ba tầng. Cột `#` trong bảng đã xếp theo thứ tự này.

| Tầng | Level | Mục tiêu |
|---|---|---|
| **Nền** | foundation, junior | Khái niệm gốc, thuật ngữ, cách mọi thứ hoạt động ở mức cơ bản. Vá lỗ hổng "dùng mà chưa hiểu". |
| **Vững** | mid | Cơ chế bên trong, bẫy thường gặp, dùng đúng trong dự án thật. Mức kỳ vọng của senior engineer. |
| **Sâu** | senior, architect | Hệ thống lớn, sự cố production, trade-off, thiết kế. Mức kỳ vọng của tech lead và SA. |

## 3. Lộ trình học để vá lỗ hổng

Thứ tự **học** khác thứ tự **viết** (mục 4): học theo tầng xuyên các track, để kiến thức nền có trước khi bài sâu cần tới nó.

1. **Tìm lỗ hổng trước**: chạy "Kiểm tra lỗ hổng" của từng track trong app. Track nào nhiều 🔴 thì học tầng Nền của track đó trước.
2. **Tầng Nền của mọi track**: ưu tiên Nền tảng CS, Core Java, Database, Spring, Security, Distributed (các bài foundation/junior). Mỗi bài ngắn, có thể học 2–3 bài một ngày.
3. **Tầng Vững theo trọng tâm SA khuyên**: Database → Performance & Troubleshooting → Security → Spring → Testing → Cloud & DevOps.
4. **Tầng Sâu + System Design**: Distributed, Caching & Messaging, JVM, rồi luyện các bài System Design bằng Interview Mode.
5. **Solution Architect + dự án của bạn**: các bài SA, và luyện kể dự án thật với tính năng "Dự án của tôi" (lời khuyên "hiểu rõ dự án đã làm").

### Đối chiếu với lời khuyên của SA

| Lời khuyên | Bài chính |
|---|---|
| System design | Toàn bộ track System Design, cùng Distributed Systems |
| Database | Track Database (24 bài, từ SQL cơ bản tới partitioning, replication) |
| Troubleshooting | Bài có block troubleshoot ở Performance, JVM, Database, Kubernetes, Kafka |
| Performance (DB, client, server, cache, Redis) | `db-performance`, `client-performance`, `server-tuning`, `cache-patterns`, `redis-internals` |
| Security AuthN/AuthZ | Track Security, cùng `spring-security-architecture` |
| Cloud infra | Track Cloud & DevOps (`cloud-fundamentals` tới `cloud-security-iam`) |
| CI/CD | `ci-cd-pipeline`, `deployment-strategies`, `infrastructure-as-code` |
| Ngôn ngữ chính (Java) | Core Java, Concurrency, JVM |
| Unit test framework | Track Testing |
| Vai trò Tech Lead | `tech-lead-role` |
| Hiểu rõ dự án đã làm | `project-storytelling` + tính năng "Dự án của tôi" |

## 4. Thứ tự viết

Thứ tự do người học chốt ngày 2026-10-24 (thay thứ tự cũ theo spec của app); ngày 2026-10-27 đưa Nền tảng CS, Core Java, JVM, System Design và Solution Architect lên trước Security, Testing, Cloud & DevOps. Trong mỗi track, viết bài Nền trước rồi tới bài Vững và Sâu, để bài sau dùng được bài trước làm `prerequisites`.

| Đợt | Track |
|---|---|
| 1 | Database (phần còn lại) → Caching & Messaging → Spring → Concurrency (phần còn lại) |
| 2 | Design → Distributed Systems → Performance & Troubleshooting |
| 3 | Nền tảng CS, Core Java, JVM (phần còn lại) → System Design → Solution Architect |
| 4 | Security → Testing → Cloud & DevOps |
| Xen kẽ | Bài ở track khác khi một bài đang viết cần nó làm bài nền |

## 5. Khái niệm dùng chung: bài nào giải thích chính

Nhiều khái niệm xuất hiện ở nhiều bài. Bài **sở hữu** giải thích đầy đủ; bài khác chỉ nhắc ngắn và trỏ tới nó (qua `prerequisites` hoặc một câu "xem bài ..."), để không viết lặp.

| Khái niệm | Bài sở hữu | Bài chỉ nhắc |
|---|---|---|
| Latency numbers, ước lượng | `computer-architecture` (con số), `back-of-envelope` (cách ước lượng) | `capacity-planning`, các bài System Design |
| Thread pool: tham số, sizing | `executor-thread-pool` | `server-tuning`, `thread-pool-exhaustion` |
| Thread dump, heap dump, JFR | `jvm-diagnostic-tools` (công cụ) | `java-high-cpu`, `memory-leak`, `profiling` |
| OOM, OOMKilled | `jvm-memory-areas` (loại OOM), `jvm-containers` (OOMKilled) | `memory-growth-oom` (điều tra end-to-end) |
| Xung đột dependency | `maven-gradle` | `classpath-modules`, `classloading` |
| JPA/Hibernate | `jpa-hibernate-basics` | `n-plus-one`, `spring-data-jpa`, `transactional-deep` |
| Lost update, khoá | `transaction-isolation` (hiện tượng), `optimistic-pessimistic-locking` (cách khoá) | `locking-deadlock-db`, `idempotency` |
| RPO/RTO | `high-availability-dr` | `backup-restore`, `replication-ha` |
| SLI/SLO | `observability` | `incident-management`, `reliability-sre` |
| Rate limiting | `rate-limiting` (thuật toán) | `design-rate-limiter` (thiết kế hệ thống), `redis-use-cases`, `api-security` |
| Distributed lock, Redlock | `distributed-locks` | `redis-use-cases` |
| Sinh ID | `clocks-ids` | `design-id-generator`, `partitioning-index` |
| Choreography và orchestration | `saga` | `event-driven-architecture`, `data-consistency-services` |
| Chọn kiến trúc tổng thể | `architecture-styles` | `microservices-tradeoffs`, `modular-monolith` |
| Cô lập tenant | `multi-tenancy` | `authorization-models` |
| Reactive | `reactive` (khái niệm, Reactor) | `spring-webflux` (runtime, Netty) |
| Load test | `load-testing` | `capacity-planning`, `perf-methodology` |

## 6. Danh sách bài

Cột **Block**: A analogy · L layered · D diagram · S simulation · B breakLab · Sc scenario · T troubleshoot. Bài có dấu ✚ là bài mới thêm sau lần rà soát độ phủ.

### 1. Nền tảng CS (`cs-fundamentals`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `network-basics` | ✚ Mạng máy tính cơ bản | foundation | Mô hình TCP/IP và OSI, IP, subnet và CIDR, port, NAT, routing; vì sao service "không gọi được nhau" | A L D | ✅ |
| 2 | `http-request-lifecycle` | HTTP request đi qua những gì | foundation | DNS → TCP → TLS → LB → app; connection pool, keep-alive | A L D | ✅ |
| 3 | `computer-architecture` | ✚ CPU, bộ nhớ & các con số latency | foundation | Cache L1/L2/L3, cache line, RAM và SSD và mạng, latency numbers; nền cho false sharing và hiệu năng | A L D | ✅ |
| 4 | `proxy-nginx` | ✚ Forward proxy, reverse proxy & Nginx | junior | Reverse proxy, TLS termination, load balancing cơ bản, timeout và buffer, header `X-Forwarded-*` | A L D | ✅ |
| 5 | `os-process-memory` | Process, thread & bộ nhớ của hệ điều hành | junior | Context switch, virtual memory, page cache, file descriptor, `ulimit`, OOM killer | A L D | ✅ |
| 6 | `data-structures` | Cấu trúc dữ liệu cơ bản & Big-O | junior | Mảng, linked list, hash table, cây, heap, graph; Big-O; chọn cấu trúc theo thao tác | L D | ✅ |
| 7 | `time-encoding` | Thời gian, múi giờ & encoding | junior | UTC, DST, lệch đồng hồ, NTP, Unicode/UTF-8, collation | L B | ✅ |
| 8 | `dns-cdn` | DNS & CDN | mid | Phân giải, TTL, cache DNS của JVM, anycast, CDN cache key/invalidation | A L D | ✅ |
| 9 | `tcp-deep` | TCP chuyên sâu | mid | Handshake, flow/congestion control, `TIME_WAIT`, backlog, Nagle, RST; cạn port vì `TIME_WAIT` | L D T | ✅ |
| 10 | `tls-https` | TLS & HTTPS | mid | TLS 1.2 và 1.3, chuỗi chứng chỉ, SNI, mTLS, sự cố chứng chỉ hết hạn | L D T | ⬜ |
| 11 | `http2-http3` | ✚ HTTP/1.1, HTTP/2 & HTTP/3 | mid | Keep-alive, multiplexing, head-of-line blocking, QUIC; ảnh hưởng tới connection pool | L D | ⬜ |
| 12 | `realtime-rpc-protocols` | ✚ gRPC, WebSocket, SSE & long polling | mid | gRPC qua HTTP/2, streaming, WebSocket và SSE, chọn cho realtime và giao tiếp nội bộ | L D Sc | ⬜ |
| 13 | `rest-api-design` | Thiết kế REST API | mid | Method idempotent, status code, phân trang, versioning và tương thích ngược, ETag, lỗi theo RFC 9457 | L B Sc | ⬜ |
| 14 | `algorithms-interview` | Thuật toán hay gặp khi phỏng vấn | mid | Hai con trỏ, sliding window, BFS/DFS, binary search, DP cơ bản | L B | ⬜ |
| 15 | `linux-troubleshooting` | Lệnh Linux để điều tra sự cố | mid | `top`, `vmstat`, `iostat`, `ss`, `lsof`, `strace`, `tcpdump` | L T | ⬜ |
| 16 | `advanced-data-structures` | ✚ Cấu trúc dữ liệu trong hệ thống lớn | senior | Skip list, Bloom filter, LSM tree, HyperLogLog, Count-Min Sketch, trie; Redis, Cassandra, Kafka dùng chúng ở đâu | L D | ⬜ |
| 17 | `io-models` | Mô hình I/O | senior | Blocking/non-blocking, epoll, reactor, Netty, zero-copy | L D | ⬜ |

### 2. Core Java (`core-java`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `java-basics-types` | ✚ Kiểu dữ liệu, autoboxing & pass-by-value | foundation | Primitive và reference, `Integer` cache (-128..127), unboxing ném NPE, Java luôn pass-by-value, `static` và `final` | A L B | ⬜ |
| 2 | `oop-java` | OOP trong Java | junior | Kế thừa và composition, dynamic dispatch, interface và abstract class, inner/nested class, enum (EnumMap, enum singleton), sealed | A L B | ⬜ |
| 3 | `string-pool` | String & String Pool | junior | Immutable, intern, compact strings, ghép chuỗi | L D B | ✅ |
| 4 | `equals-hashcode` | equals & hashCode | junior | Contract, record | A L B | ✅ |
| 5 | `comparable-comparator` | ✚ Comparable, Comparator & Iterator | junior | Contract của `compareTo`, nhất quán với `equals`, comparator kết hợp, `Iterator` và fail-fast | L B | ⬜ |
| 6 | `optional-null` | ✚ Null, Optional & xử lý vắng giá trị | junior | NPE và helpful NPE, `Optional` dùng đúng/sai, `@Nullable`, null trong collection và JSON | L B | ⬜ |
| 7 | `collections-overview` | Collections Overview | junior | Chọn cài đặt theo Big-O, bất biến và view, đa luồng | A L Sc | ✅ |
| 8 | `date-time-api` | java.time | junior | `Instant`, `ZonedDateTime`, DST, lưu thời gian đúng cách | L B | ⬜ |
| 9 | `bigdecimal-money` | Số thực & tiền tệ | junior | Sai số `double`, `BigDecimal` equals và compareTo, rounding | L B | ⬜ |
| 10 | `maven-gradle` | ✚ Maven, Gradle & quản lý dependency | junior | Lifecycle, scope, BOM, semantic versioning, dependency trung gian và xung đột phiên bản, build tái lập | L B T | ⬜ |
| 11 | `java-logging` | ✚ Logging trong Java | junior | SLF4J và Logback/Log4j2, log level, chi phí logging, async appender, MDC, bài học Log4Shell | L B | ⬜ |
| 12 | `hashmap-internals` | HashMap Internals | mid | Hash spreading, resize, treeify | A L S B | ✅ |
| 13 | `exceptions` | Exceptions | mid | Checked/unchecked, cause, try-with-resources, fast throw | L B | ✅ |
| 14 | `generics` | Generics & type erasure | mid | Erasure, wildcard và PECS, bridge method, heap pollution | L B | ⬜ |
| 15 | `immutability-records` | Immutability & record | mid | Defensive copy, record, value-based class, an toàn đa luồng | L B | ⬜ |
| 16 | `java-8-11-features` | ✚ Java 8 → 11: lambda, stream, Optional, var | mid | Lambda và capture, method reference, functional interface, default method, `var`, HTTP Client | L B | ⬜ |
| 17 | `java-17-21-features` | ✚ Java 17 → 21: record, sealed, pattern matching | mid | Record, sealed, pattern matching cho `instanceof` và `switch`, text block, sequenced collection; nâng cấp từ 8/11 lên 17/21 | L B | ⬜ |
| 18 | `stream-api` | Stream API chuyên sâu | mid | Lazy evaluation, stateful op, collector, parallel stream và common pool | L D B | ⬜ |
| 19 | `json-jackson` | ✚ JSON & Jackson | mid | Unknown property, ngày giờ và `BigDecimal`, polymorphic type, record, cấu hình `ObjectMapper` dùng chung | L B | ⬜ |
| 20 | `sorted-collections-internals` | TreeMap, LinkedHashMap, PriorityQueue bên trong | mid | Cây đỏ đen, LRU, binary heap | L S | ⬜ |
| 21 | `java-io-nio` | I/O & NIO | mid | Stream và channel, buffer, file, đọc file lớn, `Files` API, đóng resource | L B | ⬜ |
| 22 | `reflection-proxy` | Reflection, annotation & dynamic proxy | senior | JDK proxy và CGLIB/ByteBuddy, annotation processing; nền của Spring AOP | L D B | ⬜ |
| 23 | `serialization-security` | ✚ Serialization & lỗ hổng deserialization | senior | Java serialization, gadget chain, Jackson default typing, cách phòng tránh | L B | ⬜ |
| 24 | `classpath-modules` | Classpath, JPMS & xung đột dependency | senior | Dependency hell, shading, JPMS, `NoSuchMethodError` lúc chạy | L T | ⬜ |

### 3. Concurrency (`concurrency`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `concurrency-basics` | ✚ Race condition, atomicity & thread-safe | foundation | Critical section, atomicity và visibility, "thread-safe" nghĩa là gì, vì sao bean singleton phải stateless | A L S | ✅ |
| 2 | `thread-lifecycle` | Thread Lifecycle | junior | Trạng thái, interrupt | L S | ✅ |
| 3 | `synchronized-volatile` | synchronized & volatile | mid | Monitor, visibility, lost update | A L S B | ✅ |
| 4 | `deadlock` | Deadlock | mid | Coffman, lock ordering, phát hiện | A L S B | ✅ |
| 5 | `producer-consumer` | ✚ Producer–consumer & BlockingQueue | mid | `wait/notify` và `BlockingQueue`, bounded queue, backpressure, poison pill | A L S | ✅ |
| 6 | `executor-thread-pool` | ExecutorService & Thread Pool | mid | Tham số, sizing, virtual thread | A L D Sc | ✅ |
| 7 | `synchronizers` | CountDownLatch, Semaphore, CyclicBarrier, Phaser | mid | Chọn đúng công cụ, giới hạn đồng thời | L S | ✅ |
| 8 | `threadlocal` | ThreadLocal & ScopedValue | mid | Rò rỉ trong thread pool, MDC, context propagation | L B | ✅ |
| 9 | `completable-future` | CompletableFuture | senior | Nối chuỗi, lỗi, executor | L D B | ✅ |
| 10 | `java-memory-model` | Java Memory Model | senior | Happens-before, safe publication, final field, reordering, DCL | L S B | ✅ |
| 11 | `locks-aqs` | Lock & AQS | senior | ReentrantLock, ReadWriteLock, StampedLock, Condition, fairness, AQS | L S B | ✅ |
| 12 | `atomic-cas` | Atomic, CAS & LongAdder | senior | CAS, ABA, `VarHandle`, false sharing | L S B | ✅ |
| 13 | `concurrent-hashmap` | ConcurrentHashMap bên trong | senior | CAS + khoá theo bin, resize đồng thời, `compute` | L S B | ✅ |
| 14 | `virtual-threads` | Virtual Threads chuyên sâu | senior | Continuation, carrier, pinning, structured concurrency, khi nào không dùng | L D B | ✅ |
| 15 | `forkjoin` | ForkJoinPool & work stealing | senior | Common pool, parallel stream, khi nào chậm hơn | L D | ✅ |
| 16 | `reactive` | Reactive programming & Project Reactor | senior | Publisher/Subscriber, backpressure, operator, scheduler; so với virtual thread | L D Sc | ✅ |
| 17 | `testing-concurrency` | Kiểm thử code đồng thời | senior | jcstress, test flaky, tái hiện race condition | L B | ✅ |

### 4. JVM (`jvm`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `jvm-architecture` | ✚ JDK, JRE, JVM & bytecode | foundation | Từ `.java` tới bytecode, class file, interpreter và JIT, các bản JDK (Temurin, Corretto...), LTS | A L D | ⬜ |
| 2 | `jvm-memory-areas` | Vùng nhớ của JVM | junior | Heap, metaspace, stack, direct memory, code cache; các loại OOM | A L D | ⬜ |
| 3 | `gc-fundamentals` | GC hoạt động thế nào | mid | Reachability, strong/soft/weak/phantom reference, generational, mark-sweep-compact, safepoint, `Cleaner` thay `finalize` | A L S | ⬜ |
| 4 | `jvm-diagnostic-tools` | Bộ công cụ chẩn đoán JVM | mid | `jcmd`, `jstack`, `jmap`, `jstat`, JFR cơ bản: lấy bằng chứng từ JVM đang chạy | L T | ⬜ |
| 5 | `gc-algorithms` | G1, ZGC, Shenandoah, Parallel | senior | Pause và throughput, chọn GC, generational ZGC | L D Sc | ⬜ |
| 6 | `gc-logs-tuning` | Đọc GC log & tuning | senior | `-Xlog:gc`, sizing heap, các dấu hiệu bất thường | L T | ⬜ |
| 7 | `memory-leak` | Memory leak & heap dump | senior | Phân tích heap dump bằng MAT, dominator tree, leak hay gặp trong Spring và ThreadLocal | L T | ⬜ |
| 8 | `classloading` | ClassLoader | senior | Delegation, fat jar của Spring Boot, metaspace leak | L D B | ⬜ |
| 9 | `jit` | JIT compiler | senior | Tiered C1/C2, inlining, escape analysis, deopt, warmup, JMH | L D B | ⬜ |
| 10 | `jvm-containers` | JVM trong container | senior | cgroup, `MaxRAMPercentage`, CPU limit, OOMKilled và OutOfMemoryError, NMT | L T | ⬜ |
| 11 | `startup-native` | Khởi động nhanh: CDS, CRaC, GraalVM native | senior | Trade-off giữa startup, peak và độ phức tạp build | L Sc | ⬜ |

### 5. Spring (`spring`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `spring-overview` | ✚ Spring, Spring Boot & hệ sinh thái | foundation | Spring Framework và Boot khác gì, starter, embedded server, các project chính (Data, Security, Cloud, Batch) | A L D | ✅ |
| 2 | `ioc-di` | IoC & Dependency Injection | junior | Container, bean definition, kiểu inject, circular dependency | A L D | ✅ |
| 3 | `bean-lifecycle-scopes` | Bean lifecycle & scope | mid | Callback, `BeanPostProcessor`, prototype trong singleton | L S B | ✅ |
| 4 | `spring-boot-autoconfig` | Auto-configuration & cấu hình | mid | Condition, starter, `@ConfigurationProperties`, thứ tự nguồn cấu hình, profile, Actuator | L D B | ✅ |
| 5 | `spring-mvc-flow` | Request đi qua Spring MVC | mid | DispatcherServlet, filter và interceptor, `@ControllerAdvice`, validation, Jackson | L D B | ✅ |
| 6 | `jpa-hibernate-basics` | ✚ JPA & Hibernate cơ bản | mid | Entity và trạng thái (transient, managed, detached), persistence context, mapping quan hệ, LAZY/EAGER, entity và DTO | A L D B | ✅ |
| 7 | `transactional-basics` | ✚ @Transactional cơ bản | mid | Proxy mở và commit transaction thế nào, rollback mặc định chỉ với unchecked, đặt ranh giới transaction ở đâu | L B | ✅ |
| 8 | `spring-aop-proxy` | AOP & proxy | mid | JDK và CGLIB proxy, self-invocation, thứ tự advice | L D B | ✅ |
| 9 | `spring-async-events` | @Async, @Scheduled & event | mid | Thread pool mặc định, `@Scheduled` một thread, event đồng bộ và bất đồng bộ | L B | ✅ |
| 10 | `spring-cache` | ✚ Spring Cache | mid | `@Cacheable` và self-invocation, cache key, TTL, cache đúng chỗ | L B | ✅ |
| 11 | `spring-observability` | Micrometer & tracing | mid | Metric, tracing, log correlation | L T | ✅ |
| 12 | `transactional-deep` | @Transactional chuyên sâu | senior | Propagation, rollback rule, `readOnly`, self-invocation, `@TransactionalEventListener` | L S B T | ✅ |
| 13 | `spring-data-jpa` | Spring Data JPA & Hibernate chuyên sâu | senior | Dirty checking, flush mode, persistence context, bulk op, count query, `equals` của entity | L B T | ✅ |
| 14 | `spring-security-architecture` | Kiến trúc Spring Security | senior | Filter chain, `AuthenticationManager`, SecurityContext, method security, resource server | L D B | ✅ |
| 15 | `spring-cloud` | ✚ Spring Cloud cho microservices | senior | Gateway, OpenFeign, Config, Resilience4j, service discovery; khi nào không cần | L D Sc | ✅ |
| 16 | `spring-batch` | ✚ Spring Batch & xử lý lô | senior | Chunk, restart, skip/retry, partition, chạy song song an toàn | L D Sc | ✅ |
| 17 | `spring-webflux` | Spring WebFlux & Netty | senior | Event loop của Netty, block trong reactive và cách phát hiện (BlockHound), WebClient, khi nào nên dùng | L D B | ✅ |

### 6. Testing (`testing`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `test-strategy` | Test pyramid & chiến lược test | foundation | Unit, integration, e2e; testing trophy; test gì, không test gì | A L Sc | ⬜ |
| 2 | `junit5` | JUnit 5 chuyên sâu | junior | Lifecycle, parameterized, extension, chạy song song | L B | ⬜ |
| 3 | `mockito` | Mockito & test double | mid | Mock, stub, spy, fake; strict stubbing; khi nào không nên mock | L B | ⬜ |
| 4 | `test-design` | Thiết kế test tốt | mid | AAA, test smell, mutation testing (PIT), mức coverage | L B | ⬜ |
| 5 | `testcontainers` | Testcontainers | mid | DB thật, singleton container, reuse, chạy trên CI | L B | ⬜ |
| 6 | `spring-boot-test` | Spring Boot Test | mid | Test slice, context caching, `@MockBean` làm chậm suite | L B T | ⬜ |
| 7 | `http-stubbing` | ✚ Test HTTP client với WireMock | mid | Stub downstream, test timeout và retry, lỗi mạng giả lập | L B | ⬜ |
| 8 | `flaky-tests` | Test chập chờn | mid | Thời gian, thứ tự, đồng thời, `Clock`, Awaitility | L T | ⬜ |
| 9 | `contract-testing` | Contract testing | senior | Consumer-driven, Pact, Spring Cloud Contract | L D Sc | ⬜ |

### 7. Database (`database`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `sql-fundamentals` | ✚ SQL cốt lõi | foundation | Thứ tự thực thi logic của `SELECT`, `GROUP BY`/`HAVING`, các loại JOIN, `NULL` và logic ba giá trị, `NOT IN` với NULL | A L B | ✅ |
| 2 | `relational-keys-normalization` | ✚ Khoá, ràng buộc & chuẩn hoá | foundation | Primary/foreign/unique key, constraint, 1NF–3NF, surrogate và natural key | A L B | ✅ |
| 3 | `acid-transactions-basics` | ✚ ACID & transaction cơ bản | foundation | Commit/rollback, atomicity, durability, autocommit, vì sao transaction dài nguy hiểm | A L B | ✅ |
| 4 | `jdbc-basics` | ✚ JDBC & cách ứng dụng nói chuyện với DB | junior | Connection, `PreparedStatement` và SQL injection, batch, fetch size, auto-commit; ORM đứng ở đâu | L D B | ✅ |
| 5 | `index-execution-plan` | Index & Execution Plan | mid | B-tree, composite, covering, EXPLAIN, các loại index | A L D B | ✅ |
| 6 | `transaction-isolation` | Transaction & Isolation Level | mid | Hiện tượng, PostgreSQL và MySQL, lost update | A L S B | ✅ |
| 7 | `optimistic-pessimistic-locking` | ✚ Optimistic & pessimistic locking | mid | `@Version`, `SELECT ... FOR UPDATE`, `NOWAIT`/`SKIP LOCKED`, retry khi xung đột, chọn cách nào | L S B | ✅ |
| 8 | `n-plus-one` | N+1 Query | mid | Lazy loading, fetch join, batch fetching (nền: `jpa-hibernate-basics`) | A L B T | ✅ |
| 9 | `connection-pool` | Connection pool | mid | Sizing HikariCP, timeout, leak, `max_connections`, PgBouncer | A L Sc T | ✅ |
| 10 | `sql-joins-deep` | JOIN & tối ưu query | mid | Nested loop, hash, merge join; thứ tự join; subquery, CTE, window function | L D B | ✅ |
| 11 | `query-patterns` | Các mẫu query hiệu năng | mid | Keyset pagination, `count(*)`, batch insert/upsert, `OR` và `UNION` | L B | ✅ |
| 12 | `storage-engine` | Storage engine: B+tree, LSM, WAL | mid | Buffer pool, WAL, checkpoint, fsync, write amplification | A L D B | ✅ |
| 13 | `views-procedures-triggers` | ✚ View, stored procedure & trigger | mid | Khi nào dùng, materialized view, logic trong DB và trong app, rủi ro khi bảo trì | L Sc | ✅ |
| 14 | `data-modeling` | Mô hình hoá dữ liệu nâng cao | mid | Phi chuẩn hoá có chủ đích, UUID v7, soft delete, audit, lịch sử thay đổi, JSON column | L Sc | ✅ |
| 15 | `nosql-overview` | NoSQL: chọn loại nào | mid | Document, key-value, wide-column, graph; mô hình theo access pattern | L Sc | ✅ |
| 16 | `backup-restore` | Backup, restore & PITR | mid | Logical và physical backup, PITR dựa trên WAL/binlog, diễn tập restore (RPO/RTO: xem `high-availability-dr`) | L Sc | ✅ |
| 17 | `locking-deadlock-db` | Lock & deadlock trong database | senior | Row và table lock, gap lock, đọc deadlock log, lock timeout, advisory lock | L D T | ✅ |
| 18 | `mvcc-vacuum` | MVCC, VACUUM & undo log | senior | Phiên bản dòng PostgreSQL và InnoDB, autovacuum, bloat, XID wraparound | L D T | ✅ |
| 19 | `partitioning-index` | Partitioning & Global/Local Index | senior | Pruning, local và global, unique key, DynamoDB GSI/LSI | A L D Sc | ✅ |
| 20 | `replication-ha` | Replication & high availability | senior | Sync và async, replica lag, read-your-writes, failover, split brain | L D T | ✅ |
| 21 | `sharding-strategies` | Sharding | senior | Hash, range, directory; resharding; query xuyên shard; Vitess, Citus | L D Sc | ✅ |
| 22 | `schema-migration` | Migration không downtime | senior | Flyway/Liquibase, expand-contract, online DDL, backfill lớn | L B Sc | ✅ |
| 23 | `search-elasticsearch` | ✚ Search engine & Elasticsearch | senior | Inverted index, analyzer, relevance, đồng bộ từ DB, khi nào không cần | L D Sc | ✅ |
| 24 | `postgres-vs-mysql` | ✚ PostgreSQL và MySQL: khác nhau ở đâu | senior | Lưu trữ (heap và clustered), MVCC, replication, index, tính năng; chọn cho dự án mới | L Sc | ✅ |

### 8. Caching & Messaging (`caching-messaging`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `caching-basics` | ✚ Cache là gì & cache ở đâu | foundation | Hit ratio, TTL, eviction (LRU, LFU), các tầng cache: browser, CDN, gateway, app, DB | A L D | ✅ |
| 2 | `messaging-fundamentals` | Messaging cơ bản | foundation | Đồng bộ và bất đồng bộ, queue và pub/sub, at-most/at-least/exactly-once, DLQ; SQS/SNS | A L D | ✅ |
| 3 | `cache-patterns` | Cache patterns | mid | Cache-aside, read/write-through, write-behind, invalidation, consistency | A L D | ✅ |
| 4 | `local-cache` | Local & multi-level cache | mid | Caffeine, near cache, invalidation giữa các node | L Sc | ✅ |
| 5 | `redis-internals` | Redis bên trong | mid | Kiểu dữ liệu, single thread và I/O thread, RDB/AOF, eviction, bộ nhớ | L D T | ✅ |
| 6 | `kafka-architecture` | Kiến trúc Kafka | mid | Partition, replication, ISR, `acks`, leader election, KRaft | L D | ✅ |
| 7 | `rabbitmq` | RabbitMQ & so sánh với Kafka | mid | Exchange, ack, prefetch, quorum queue; chọn công cụ | L D Sc | ✅ |
| 8 | `cache-failures` | Stampede, penetration, avalanche, hot key | senior | Lock, refresh sớm theo xác suất, Bloom filter, jitter TTL | L S T | ✅ |
| 9 | `redis-ha-cluster` | Redis Sentinel & Cluster | senior | Replication, hash slot, failover mất dữ liệu | L D | ✅ |
| 10 | `redis-use-cases` | Redis cho lock, rate limit, leaderboard | senior | Lua script, sorted set cho leaderboard, đếm và rate limit bằng Redis, lock đơn giản (Redlock: xem `distributed-locks`) | L B Sc | ✅ |
| 11 | `kafka-producer-consumer` | Kafka producer & consumer chuyên sâu | senior | Idempotent producer, transaction, consumer group, rebalance, commit offset | L S B | ✅ |
| 12 | `event-schema-evolution` | ✚ Thiết kế event & schema evolution | senior | Event và command, event mang đủ dữ liệu hay chỉ báo hiệu, Avro/Protobuf, schema registry, tương thích ngược | L B Sc | ✅ |
| 13 | `kafka-troubleshooting` | Vận hành & sự cố Kafka | senior | Consumer lag, rebalance storm, poison message, số partition | L T | ✅ |

### 9. Security (`security`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `authn-authz-basics` | AuthN & AuthZ cơ bản | foundation | Session và token, hash mật khẩu (bcrypt/argon2), MFA | A L D | ⬜ |
| 2 | `cryptography-basics` | Mật mã cho kỹ sư | junior | Hash, mã hoá, encoding; đối xứng và bất đối xứng; chữ ký số; envelope encryption, KMS | A L D | ⬜ |
| 3 | `browser-security-basics` | ✚ Bảo mật phía trình duyệt | junior | Same-origin policy, cookie (`HttpOnly`, `Secure`, `SameSite`), CORS, CSP | A L B | ⬜ |
| 4 | `owasp-top10` | OWASP Top 10 với Java/Spring | mid | Injection, broken access control, SSRF, XSS, CSRF, deserialization | L B | ⬜ |
| 5 | `jwt-deep` | JWT chuyên sâu | mid | Cấu trúc, thuật toán ký, validate, hết hạn/refresh, thu hồi, nơi lưu | L B T | ⬜ |
| 6 | `secret-management` | Quản lý secret | mid | Vault, KMS, xoay vòng, secret lọt vào git | L T | ⬜ |
| 7 | `data-privacy-pii` | ✚ Dữ liệu cá nhân & tuân thủ | mid | PII, che dữ liệu trong log, mã hoá at rest/in transit, audit log, nguyên tắc GDPR/Nghị định 13 | L B Sc | ⬜ |
| 8 | `oauth2-oidc` | OAuth2 & OpenID Connect | mid | Authorization code + PKCE, client credentials, scope, ID token và access token | L D Sc | ⬜ |
| 9 | `sso-saml` | ✚ SSO doanh nghiệp & SAML | senior | SAML và OIDC, IdP, federation, đăng xuất tập trung | L D Sc | ⬜ |
| 10 | `authorization-models` | Mô hình phân quyền | senior | RBAC, ABAC, ReBAC, policy engine (OPA), cô lập multi-tenant, IDOR | L B Sc | ⬜ |
| 11 | `api-security` | Bảo mật API | senior | Rate limit, mTLS giữa service, API gateway, validate input, service-to-service auth | L Sc | ⬜ |
| 12 | `secure-sdlc` | Bảo mật trong quy trình phát triển | senior | Threat modeling (STRIDE), SAST/DAST/SCA, supply chain, SBOM | L Sc | ⬜ |

### 10. Performance & Troubleshooting (`performance`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `perf-methodology` | Phương pháp phân tích hiệu năng | foundation | Latency và throughput, percentile, USE/RED, Little's law, Amdahl | A L D | ✅ |
| 2 | `troubleshooting-mindset` | ✚ Quy trình điều tra sự cố | junior | Giữ hiện trường, khoanh vùng, giả thuyết và bằng chứng, cầm máu trước rồi tìm nguyên nhân | A L T | ✅ |
| 3 | `observability` | Metrics, tracing & SLO | mid | RED/USE trên dashboard, OpenTelemetry, distributed tracing, SLI/SLO (bài sở hữu khái niệm SLO) | L D Sc | ✅ |
| 4 | `production-logging` | ✚ Log cho production | mid | Structured log, correlation id, mức log theo môi trường, chi phí, tập trung log (ELK, Loki) | L B T | ✅ |
| 5 | `server-tuning` | ✚ Tuning server & HTTP client | mid | Thread pool của Tomcat/Undertow, timeout, keep-alive, nén, pool của HTTP client | L B T | ✅ |
| 6 | `client-performance` | Hiệu năng phía client | mid | Payload, nén, HTTP cache header, CDN, Core Web Vitals | L Sc | ✅ |
| 7 | `java-high-cpu` | Ứng dụng Java CPU 100% | senior | `top -H`, thread dump, regex backtracking | L T | ✅ |
| 8 | `slow-api` | Điều tra API chậm | senior | Lần theo từng tầng: DB, downstream, GC, thread pool, mạng | L T | ✅ |
| 9 | `thread-pool-exhaustion` | Request treo vì cạn thread | senior | Thread dump toàn WAITING, timeout thiếu, bulkhead | L T | ✅ |
| 10 | `memory-growth-oom` | Bộ nhớ tăng dần & OOM | senior | Điều tra end-to-end: heap hay native, OOMKilled hay OutOfMemoryError; dẫn sang `memory-leak`, `jvm-containers` | L T | ✅ |
| 11 | `db-performance` | Database chậm trên production | senior | `pg_stat_statements`, lock wait, cạn connection pool, replica lag | L T | ✅ |
| 12 | `profiling` | Profiling | senior | async-profiler, flame graph CPU/allocation/lock, đọc JFR recording | L D T | ✅ |
| 13 | `tail-latency` | Tail latency, timeout & retry | senior | Retry khuếch đại tải, timeout budget, hedging | L S Sc | ✅ |
| 14 | `capacity-planning` | Capacity planning & autoscaling | senior | Ước lượng tải, headroom, autoscale theo metric nào | L Sc | ✅ |
| 15 | `load-testing` | Load & performance testing | senior | Mô hình tải, k6/Gatling, coordinated omission, đọc kết quả | L Sc | ✅ |

### 11. Design (`design`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `design-principles` | ✚ Coupling, cohesion & các nguyên tắc nền | foundation | Coupling và cohesion, composition, DRY/KISS/YAGNI, Law of Demeter | A L B | ✅ |
| 2 | `solid` | SOLID | junior | Từng nguyên tắc với ví dụ vi phạm và cách sửa | A L B | ✅ |
| 3 | `layered-architecture` | ✚ Kiến trúc phân lớp & tổ chức package | junior | Controller/service/repository, package-by-feature và package-by-layer, mapping DTO | A L B | ✅ |
| 4 | `creational-patterns` | Creational patterns | mid | Factory, Builder, Singleton (và vì sao nên tránh) | L B | ✅ |
| 5 | `structural-patterns` | Structural patterns | mid | Adapter, Decorator, Proxy, Facade; ví dụ trong JDK và Spring | L D B | ✅ |
| 6 | `behavioral-patterns` | Behavioral patterns | mid | Strategy, Template Method, Observer, Chain of Responsibility, State | L B | ✅ |
| 7 | `lld-ood-interview` | ✚ Low-level design (OOD) khi phỏng vấn | mid | Parking lot, LRU cache, elevator: mô hình lớp, áp dụng pattern, xử lý đồng thời | L B Sc | ✅ |
| 8 | `refactoring-tech-debt` | Refactoring & nợ kỹ thuật | mid | Code smell, refactor an toàn, đo và trả nợ | L B | ✅ |
| 9 | `clean-hexagonal` | Clean & Hexagonal Architecture | senior | Port/adapter, quy tắc phụ thuộc, khi nào quá tay | A L D Sc | ✅ |
| 10 | `ddd-strategic` | DDD chiến lược | senior | Bounded context, context map, ubiquitous language | A L D Sc | ✅ |
| 11 | `ddd-tactical` | DDD chiến thuật | senior | Aggregate, entity, value object, domain event, kích thước aggregate | L B Sc | ✅ |
| 12 | `modular-monolith` | Modular monolith | senior | Ranh giới module, kiểm tra kiến trúc (ArchUnit), tách dần | L Sc | ✅ |

### 12. Distributed Systems (`distributed`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `distributed-fundamentals` | ✚ Vì sao hệ phân tán khó | foundation | Partial failure, mạng không tin cậy, 8 ngộ nhận về hệ phân tán, timeout không phân biệt được chậm và chết | A L D | ✅ |
| 2 | `service-communication` | Giao tiếp giữa service | junior | REST, gRPC, GraphQL, async; đồng bộ và bất đồng bộ; service discovery | L D Sc | ✅ |
| 3 | `load-balancing` | ✚ Load balancing | mid | Thuật toán (round robin, least connections, consistent hashing), L4 và L7, health check, sticky session | A L D | ✅ |
| 4 | `consistency-cap` | Consistency, CAP & PACELC | mid | Linearizable, causal, eventual; CAP và PACELC thật sự nói gì | A L D | ✅ |
| 5 | `idempotency` | Idempotency | mid | Idempotency key, dedup, exactly-once là gì thật sự | A L B Sc | ✅ |
| 6 | `data-consistency-services` | ✚ Nhất quán dữ liệu giữa các service | mid | Không có transaction chung, eventual consistency, dual write; tổng quan saga, outbox, đối soát | A L D | ✅ |
| 7 | `resilience-patterns` | Timeout, retry, circuit breaker, bulkhead | mid | Timeout, retry với backoff + jitter, circuit breaker, bulkhead, fallback, load shedding và backpressure | L S B | ✅ |
| 8 | `microservices-tradeoffs` | Microservices: khi nào và chia thế nào | senior | Chia theo domain, chi phí phân tán, khi nào giữ monolith | L Sc | ✅ |
| 9 | `api-gateway-service-mesh` | ✚ API gateway, BFF & service mesh | senior | Trách nhiệm của gateway, BFF, sidecar (Istio/Linkerd), khi nào thừa | L D Sc | ✅ |
| 10 | `event-driven-architecture` | ✚ Event-driven architecture | senior | Event notification và event-carried state, broker, eventual consistency, thứ tự, consumer idempotent | L D Sc | ✅ |
| 11 | `saga` | Saga | senior | Orchestration và choreography, compensation | L S Sc | ✅ |
| 12 | `outbox-cdc` | Transactional outbox & CDC | senior | Vấn đề dual write, Debezium, thứ tự và trùng lặp | L D B | ✅ |
| 13 | `cqrs-event-sourcing` | CQRS & Event Sourcing | senior | Read model, projection, snapshot, khi nào không dùng | L D Sc | ✅ |
| 14 | `distributed-transactions` | 2PC & giao dịch phân tán | senior | 2PC, XA, vì sao tránh, các lựa chọn thay thế | L S | ✅ |
| 15 | `consistent-hashing` | ✚ Consistent hashing & phân phối dữ liệu | senior | Vòng hash, virtual node, rebalance, replication theo quorum (N, R, W) | L S D | ✅ |
| 16 | `rate-limiting` | Rate limiting | senior | Token bucket, leaky bucket, sliding window; phân tán | L S Sc | ✅ |
| 17 | `distributed-locks` | Distributed lock & fencing token | senior | Lease, fencing, vì sao lock dựa trên thời gian nguy hiểm | L S B | ✅ |
| 18 | `clocks-ids` | Đồng hồ, thứ tự & sinh ID | senior | Lệch đồng hồ, Lamport/vector clock, snowflake, UUID v7 | L D | ✅ |
| 19 | `consensus` | Consensus & leader election | architect | Raft, quorum, split brain, etcd/ZooKeeper | L S D | ✅ |
| 20 | `multi-region-active-active` | ✚ Multi-region & active-active | architect | Replication giữa region, giải quyết xung đột (LWW, CRDT), định tuyến người dùng, chi phí | L D Sc | ✅ |

### 13. Cloud & DevOps (`cloud-devops`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `cloud-fundamentals` | ✚ Cloud cơ bản | foundation | IaaS/PaaS/SaaS, region và AZ, shared responsibility, mô hình tính tiền | A L D | ⬜ |
| 2 | `twelve-factor` | ✚ Twelve-Factor App | junior | Cấu hình qua môi trường, stateless, log ra stdout, dev/prod giống nhau | L B | ⬜ |
| 3 | `git-workflow` | Git bên trong & quy trình nhánh | junior | Object model, merge và rebase, bisect, trunk-based và Git Flow | A L | ⬜ |
| 4 | `docker` | Docker & container | junior | Namespace và cgroup, image và layer, multi-stage, image cho JVM, bảo mật image | A L D B | ⬜ |
| 5 | `kubernetes-core` | Kubernetes cơ bản | mid | Pod, Deployment, Service, Ingress, ConfigMap/Secret | A L D | ⬜ |
| 6 | `k8s-packaging` | ✚ Helm, Kustomize & cấu hình nhiều môi trường | mid | Template và overlay, quản lý giá trị theo môi trường, secret | L B | ⬜ |
| 7 | `aws-core` | AWS cho kỹ sư backend | mid | VPC, EC2, ALB/NLB, RDS, IAM: dựng một ứng dụng web cơ bản | L D Sc | ⬜ |
| 8 | `aws-managed-services` | ✚ Dịch vụ managed của AWS | mid | SQS/SNS, DynamoDB, ElastiCache, Lambda, chọn managed hay tự vận hành | L Sc | ⬜ |
| 9 | `aws-edge-storage` | ✚ Route 53, CloudFront & lưu trữ trên AWS | mid | Routing policy, CDN, EBS/EFS/S3 và lớp lưu trữ, chọn loại storage | L D Sc | ⬜ |
| 10 | `ci-cd-pipeline` | CI/CD pipeline | mid | Các stage, artifact, trunk-based, feature flag | A L D | ⬜ |
| 11 | `graceful-shutdown` | ✚ Graceful shutdown & vòng đời process | mid | SIGTERM và SIGKILL, graceful shutdown của Spring Boot, `preStop` của Kubernetes, rút connection và consumer | L B T | ⬜ |
| 12 | `infrastructure-as-code` | Infrastructure as Code & GitOps | mid | Terraform state, module, drift, Argo CD | L B | ⬜ |
| 13 | `incident-management` | Alerting, on-call & postmortem | mid | Alert theo SLO, runbook, postmortem không đổ lỗi | L T | ⬜ |
| 14 | `serverless` | Serverless | mid | Lambda, cold start, giới hạn, khi nào phù hợp | L Sc | ⬜ |
| 15 | `deployment-strategies` | Rolling, blue-green, canary | mid | Rollback, tương thích schema và API khi deploy | L S Sc | ⬜ |
| 16 | `kubernetes-operations` | Vận hành ứng dụng trên Kubernetes | senior | Probe, requests/limits, HPA, rolling update, PDB, CrashLoopBackOff, OOMKilled | L T | ⬜ |
| 17 | `cloud-networking` | Network trên cloud | senior | Subnet, NAT, security group, PrivateLink, DNS nội bộ, LB L4 và L7, VPN/Direct Connect/Transit Gateway | L D T | ⬜ |
| 18 | `cloud-security-iam` | ✚ Bảo mật trên cloud & IAM | senior | Least privilege, role và policy, phân tách tài khoản, network segmentation, KMS | L B Sc | ⬜ |
| 19 | `high-availability-dr` | High availability & disaster recovery | senior | Multi-AZ, multi-region, RPO/RTO, diễn tập | L D Sc | ⬜ |

### 14. System Design (`system-design`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `sd-building-blocks` | ✚ Các khối xây dựng | foundation | LB, cache, CDN, queue, các loại DB, object storage, search: mỗi khối giải bài toán gì | A L D | ⬜ |
| 2 | `sd-framework` | Khung trả lời System Design | junior | Yêu cầu, ước lượng, high-level, deep dive, trade-off, quản lý thời gian | A L D | ⬜ |
| 3 | `back-of-envelope` | Ước lượng nhanh | junior | Các con số cần nhớ, QPS, dung lượng, băng thông | L B | ⬜ |
| 4 | `design-url-shortener` | Thiết kế URL shortener | mid | Sinh mã, redirect, cache, analytics | L D Sc | ⬜ |
| 5 | `design-rate-limiter` | Thiết kế rate limiter | mid | Thuật toán, phân tán, nơi đặt | L D Sc | ⬜ |
| 6 | `design-id-generator` | Thiết kế bộ sinh ID phân tán | mid | Snowflake, sequence theo khối, thứ tự | L D Sc | ⬜ |
| 7 | `design-notification` | Thiết kế hệ thống thông báo | senior | Nhiều kênh, retry, dedup, tuỳ chọn của người dùng | L D Sc | ⬜ |
| 8 | `design-ecommerce-order` | ✚ Thiết kế đơn hàng & tồn kho | senior | Trạng thái đơn, giữ hàng, thanh toán, huỷ và hoàn, tính nhất quán giữa các service | L D Sc | ⬜ |
| 9 | `design-news-feed` | Thiết kế news feed | senior | Fan-out on write và on read, người dùng nổi tiếng, xếp hạng | L D Sc | ⬜ |
| 10 | `design-chat` | Thiết kế ứng dụng chat | senior | WebSocket, presence, thứ tự tin nhắn, đồng bộ nhiều thiết bị | L D Sc | ⬜ |
| 11 | `design-search-autocomplete` | Thiết kế autocomplete | senior | Trie, top-k, cập nhật, cache | L D Sc | ⬜ |
| 12 | `design-job-scheduler` | ✚ Thiết kế job scheduler phân tán | senior | Cron phân tán, chạy đúng một lần, retry, phân phối việc, theo dõi | L D Sc | ⬜ |
| 13 | `design-web-crawler` | ✚ Thiết kế web crawler | senior | Frontier, politeness, dedup URL và nội dung, mở rộng | L D Sc | ⬜ |
| 14 | `design-file-storage` | Thiết kế lưu trữ file / video | senior | Upload theo phần, CDN, transcoding, metadata | L D Sc | ⬜ |
| 15 | `design-key-value-store` | ✚ Thiết kế key-value store phân tán | architect | Consistent hashing, replication, quorum, xử lý conflict, như Dynamo | L D Sc | ⬜ |
| 16 | `design-message-queue` | ✚ Thiết kế distributed message queue | architect | Log phân vùng, replication, thứ tự, giữ dữ liệu, consumer group | L D Sc | ⬜ |
| 17 | `design-payment` | Thiết kế hệ thống thanh toán | architect | Idempotency, sổ cái kép, đối soát, trạng thái | L D Sc | ⬜ |
| 18 | `design-flash-sale` | Thiết kế flash sale / bán vé | architect | Chống bán vượt tồn kho, hàng đợi, giữ chỗ có thời hạn | L D Sc | ⬜ |
| 19 | `design-ride-hailing` | Thiết kế ứng dụng gọi xe | architect | Geo index (geohash, quadtree), ghép cặp, cập nhật vị trí | L D Sc | ⬜ |
| 20 | `design-metrics-logging` | Thiết kế hệ thống metric/log | architect | Time-series, ingestion, downsampling, chi phí lưu trữ | L D Sc | ⬜ |

### 15. Solution Architect (`solution-architect`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `sa-role` | Vai trò Solution Architect | foundation | Khác tech lead và enterprise architect, công việc hằng ngày, làm việc với stakeholder | A L | ⬜ |
| 2 | `project-storytelling` | ✚ Kể về dự án & câu hỏi hành vi | junior | Kể dự án theo bối cảnh → vai trò → quyết định → kết quả, STAR, câu hỏi về xung đột và thất bại | L Sc | ⬜ |
| 3 | `tech-lead-role` | ✚ Vai trò Tech Lead | mid | Code review, mentoring, ước lượng, giao việc, dẫn dắt sự cố, ưu tiên nợ kỹ thuật | A L Sc | ⬜ |
| 4 | `adr-c4` | ADR, C4 model & tài liệu kiến trúc | mid | Viết ADR, các mức C4, arc42, sequence diagram | L D B | ⬜ |
| 5 | `nfr-quality-attributes` | NFR & quality attribute | mid | Định lượng NFR, quality attribute scenario, utility tree | L Sc | ⬜ |
| 6 | `well-architected` | ✚ AWS Well-Architected & 6 trụ cột | senior | Operational excellence, security, reliability, performance, cost, sustainability; dùng để review | L Sc | ⬜ |
| 7 | `architecture-tradeoffs` | Ra quyết định & trade-off | senior | Quyết định một chiều và hai chiều, ma trận đánh giá, rủi ro | L Sc | ⬜ |
| 8 | `requirements-estimation` | ✚ Khai thác yêu cầu & ước lượng | senior | Discovery workshop, chốt phạm vi, ước lượng công sức, roadmap | L Sc | ⬜ |
| 9 | `architecture-styles` | Chọn kiểu kiến trúc | architect | Layered, microservices, event-driven, serverless, space-based | L D Sc | ⬜ |
| 10 | `integration-patterns` | Integration patterns | architect | EIP, API-led, ESB, file và event, tích hợp hệ thống cũ | L D Sc | ⬜ |
| 11 | `data-architecture` | ✚ Kiến trúc dữ liệu | architect | OLTP và OLAP, data warehouse/lake/lakehouse, ETL/ELT, CDC, báo cáo không đè lên DB chính | L D Sc | ⬜ |
| 12 | `security-architecture` | ✚ Kiến trúc bảo mật | architect | Defense in depth, zero trust, phân vùng mạng, quản lý danh tính tập trung | L D Sc | ⬜ |
| 13 | `reliability-sre` | ✚ Độ tin cậy & SRE | architect | SLO và error budget, chaos engineering, game day, thiết kế cho lỗi | L Sc | ⬜ |
| 14 | `migration-modernization` | Migration & hiện đại hoá | architect | Strangler fig, 6R khi lên cloud, migrate dữ liệu | L D Sc | ⬜ |
| 15 | `cost-finops` | Ước tính chi phí & FinOps | architect | Mô hình chi phí cloud, tối ưu, đánh đổi chi phí và độ tin cậy | L Sc | ⬜ |
| 16 | `multi-tenancy` | Kiến trúc multi-tenant | architect | Mức cô lập, noisy neighbor, dữ liệu theo tenant | L D Sc | ⬜ |
| 17 | `build-vs-buy` | Build hay buy & chọn vendor | architect | Tiêu chí, PoC, lock-in, tổng chi phí sở hữu (TCO) | L Sc | ⬜ |
| 18 | `team-topologies` | ✚ Conway's law & cấu trúc team | architect | Kiến trúc theo team, Team Topologies, ranh giới sở hữu | L Sc | ⬜ |
| 19 | `enterprise-architecture` | ✚ Enterprise architecture & governance | architect | TOGAF ở mức đủ dùng, tech radar, chuẩn hoá công nghệ, review board | L Sc | ⬜ |
| 20 | `evolutionary-architecture` | ✚ Kiến trúc tiến hoá & fitness function | architect | Fitness function, kiểm tra kiến trúc tự động, thay đổi dần thay vì viết lại | L Sc | ⬜ |
| 21 | `architecture-review` | Review một kiến trúc | architect | Risk storming, ATAM rút gọn, câu hỏi cần hỏi | L Sc | ⬜ |
| 22 | `communicating-architecture` | Trình bày kiến trúc cho stakeholder | architect | Sơ đồ theo người nghe, xử lý phản biện, viết đề xuất | L Sc | ⬜ |

## 7. Tổng quan

| Track | Nền | Vững | Sâu | Đã có | Tổng |
|---|---|---|---|---|---|
| Nền tảng CS | 7 | 8 | 2 | 1 | 17 |
| Core Java | 11 | 10 | 3 | 5 | 24 |
| Concurrency | 2 | 6 | 9 | 5 | 17 |
| JVM | 2 | 2 | 7 | 0 | 11 |
| Spring | 2 | 9 | 6 | 0 | 17 |
| Testing | 2 | 6 | 1 | 0 | 9 |
| Database | 4 | 12 | 8 | 18 | 24 |
| Caching & Messaging | 2 | 5 | 6 | 0 | 13 |
| Security | 3 | 5 | 4 | 0 | 12 |
| Performance & Troubleshooting | 2 | 4 | 9 | 1 | 15 |
| Design | 3 | 5 | 4 | 0 | 12 |
| Distributed Systems | 2 | 5 | 13 | 0 | 20 |
| Cloud & DevOps | 4 | 11 | 4 | 0 | 19 |
| System Design | 3 | 3 | 14 | 0 | 20 |
| Solution Architect | 2 | 3 | 17 | 0 | 22 |
| **Tổng** | **51** | **94** | **107** | **30** | **252** |
