# Curriculum PapaBun

Danh sách bài cho cả 15 track, kèm tiêu chuẩn "chuyên sâu" mà mọi bài phải đạt. Đây là nguồn chính để chọn bài tiếp theo, trên cả máy cá nhân lẫn máy công ty.

- ✅ đã phát hành hoặc đã merge · ⬜ chưa viết.
- `id` là đề xuất. Được đổi trước khi bài phát hành; **phát hành rồi thì không đổi**.
- Viết xong một bài: đổi ⬜ thành ✅ trong cùng commit với bài đó.

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

**Quá dài thì tách bài.** Phần Interview giới hạn 200–350 từ. Khi một chủ đề không vừa (như Index → Partitioning & Global/Local Index), tách thành bài riêng thay vì nhồi vào Deep, và thêm bài mới vào danh sách dưới đây.

## 2. Thứ tự viết

Theo thứ tự đã chốt trong spec của app (mục 9, "Sau MVP"), ưu tiên theo lời khuyên của SA (database, troubleshooting, performance, security, cloud, CI/CD, ngôn ngữ chính, unit test, hiểu rõ dự án đã làm):

| Đợt | Track |
|---|---|
| 1 | Database (phần còn lại) → Performance & Troubleshooting → Security |
| 2 | Spring → Testing → System Design |
| 3 | Caching & Messaging → Cloud & DevOps → Nền tảng CS (phần còn lại) |
| 4 | JVM → Distributed Systems → Design → Solution Architect |
| Xen kẽ | Core Java và Concurrency (phần còn lại), khi bài ở đợt khác cần chúng làm bài nền |

Trong mỗi track, viết theo cột `#`: bài nền trước, bài nâng cao sau.

## 3. Danh sách bài

Cột **Block**: A analogy · L layered · D diagram · S simulation · B breakLab · Sc scenario · T troubleshoot.

### 1. Nền tảng CS (`cs-fundamentals`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `http-request-lifecycle` | HTTP request đi qua những gì | foundation | DNS → TCP → TLS → LB → app; connection pool, keep-alive | A L D | ✅ |
| 2 | `tcp-deep` | TCP chuyên sâu | mid | Handshake, flow/congestion control, `TIME_WAIT`, backlog, Nagle, RST; cạn port vì `TIME_WAIT` | L D T | ⬜ |
| 3 | `dns-cdn` | DNS & CDN | mid | Phân giải, TTL, cache DNS của JVM, anycast, CDN cache key/invalidation | A L D | ⬜ |
| 4 | `tls-https` | TLS & HTTPS | mid | TLS 1.2 và 1.3, chuỗi chứng chỉ, SNI, mTLS, sự cố chứng chỉ hết hạn | L D T | ⬜ |
| 5 | `http-versions-protocols` | HTTP/1.1, HTTP/2, HTTP/3, gRPC, WebSocket | mid | Multiplexing, head-of-line blocking, gRPC qua HTTP/2, SSE và WebSocket | L D Sc | ⬜ |
| 6 | `rest-api-design` | Thiết kế REST API | mid | Method idempotent, status code, phân trang, versioning, ETag, lỗi theo RFC 9457 | L B Sc | ⬜ |
| 7 | `os-process-memory` | Process, thread & bộ nhớ của hệ điều hành | mid | Context switch, virtual memory, page cache, file descriptor, `ulimit`, OOM killer | A L D | ⬜ |
| 8 | `io-models` | Mô hình I/O | senior | Blocking/non-blocking, epoll, reactor, Netty, zero-copy | L D | ⬜ |
| 9 | `data-structures` | Cấu trúc dữ liệu trong hệ thống thật | mid | Hash, cây cân bằng, heap, trie, skip list, Bloom filter, LSM; dùng ở đâu | L D | ⬜ |
| 10 | `algorithms-interview` | Thuật toán hay gặp khi phỏng vấn | mid | Hai con trỏ, sliding window, BFS/DFS, binary search, DP cơ bản; Big-O | L B | ⬜ |
| 11 | `linux-troubleshooting` | Lệnh Linux để điều tra sự cố | mid | `top`, `vmstat`, `iostat`, `ss`, `lsof`, `strace`, `tcpdump` | L T | ⬜ |
| 12 | `git-workflow` | Git bên trong & quy trình nhánh | junior | Object model, merge và rebase, bisect, trunk-based và Git Flow | A L | ⬜ |
| 13 | `time-encoding` | Thời gian, múi giờ & encoding | mid | UTC, DST, lệch đồng hồ, NTP, Unicode/UTF-8, collation | L B | ⬜ |

### 2. Core Java (`core-java`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `string-pool` | String & String Pool | junior | Immutable, intern, compact strings, ghép chuỗi | L D B | ✅ |
| 2 | `equals-hashcode` | equals & hashCode | junior | Contract, record | A L B | ✅ |
| 3 | `collections-overview` | Collections Overview | junior | Chọn cài đặt theo Big-O, bất biến và view, đa luồng | A L Sc | ✅ |
| 4 | `hashmap-internals` | HashMap Internals | mid | Hash spreading, resize, treeify | A L S B | ✅ |
| 5 | `exceptions` | Exceptions | mid | Checked/unchecked, cause, try-with-resources, fast throw | L B | ✅ |
| 6 | `oop-java` | OOP trong Java | junior | Kế thừa và composition, dynamic dispatch, interface default, abstract, sealed | A L B | ⬜ |
| 7 | `generics` | Generics & type erasure | mid | Erasure, wildcard và PECS, bridge method, heap pollution | L B | ⬜ |
| 8 | `immutability-records` | Immutability & record | mid | Defensive copy, record, value-based class, an toàn đa luồng | L B | ⬜ |
| 9 | `stream-api` | Stream API chuyên sâu | mid | Lazy evaluation, stateful op, collector, parallel stream và common pool | L D B | ⬜ |
| 10 | `modern-java` | Java 8 → 21: những gì thay đổi | mid | Lambda, `var`, switch expression, pattern matching, text block, sealed, virtual thread | L B | ⬜ |
| 11 | `sorted-collections-internals` | TreeMap, LinkedHashMap, PriorityQueue bên trong | mid | Cây đỏ đen, LRU, binary heap | L S | ⬜ |
| 12 | `reflection-proxy` | Reflection, annotation & dynamic proxy | senior | JDK proxy và CGLIB/ByteBuddy, annotation processing; nền của Spring AOP | L D B | ⬜ |
| 13 | `java-io-nio` | I/O, NIO & serialization | mid | Stream và channel, buffer, file; lỗ hổng deserialization | L B | ⬜ |
| 14 | `date-time-api` | java.time | junior | `Instant`, `ZonedDateTime`, DST, lưu thời gian đúng cách | L B | ⬜ |
| 15 | `bigdecimal-money` | Số thực & tiền tệ | junior | Sai số `double`, `BigDecimal` equals và compareTo, rounding | L B | ⬜ |
| 16 | `classpath-modules` | Classpath, JPMS & xung đột dependency | senior | Dependency hell, shading, JPMS, `NoSuchMethodError` | L T | ⬜ |

### 3. Concurrency (`concurrency`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `thread-lifecycle` | Thread Lifecycle | junior | Trạng thái, interrupt | L S | ✅ |
| 2 | `synchronized-volatile` | synchronized & volatile | mid | Monitor, visibility, lost update | A L S B | ✅ |
| 3 | `deadlock` | Deadlock | mid | Coffman, lock ordering, phát hiện | A L S B | ✅ |
| 4 | `java-memory-model` | Java Memory Model | senior | Happens-before, safe publication, final field, reordering, DCL | L S B | ⬜ |
| 5 | `executor-thread-pool` | ExecutorService & Thread Pool | mid | Tham số, sizing, virtual thread | A L D Sc | ✅ |
| 6 | `completable-future` | CompletableFuture | senior | Nối chuỗi, lỗi, executor | L D B | ✅ |
| 7 | `locks-aqs` | Lock & AQS | senior | ReentrantLock, ReadWriteLock, StampedLock, Condition, fairness, AQS | L S B | ⬜ |
| 8 | `atomic-cas` | Atomic, CAS & LongAdder | senior | CAS, ABA, `VarHandle`, false sharing | L S B | ⬜ |
| 9 | `synchronizers` | CountDownLatch, Semaphore, CyclicBarrier, Phaser | mid | Chọn đúng công cụ, giới hạn đồng thời | L S | ⬜ |
| 10 | `threadlocal` | ThreadLocal & ScopedValue | mid | Rò rỉ trong thread pool, MDC, context propagation | L B | ⬜ |
| 11 | `concurrent-hashmap` | ConcurrentHashMap bên trong | senior | CAS + khoá theo bin, resize đồng thời, `compute` | L S | ⬜ |
| 12 | `virtual-threads` | Virtual Threads chuyên sâu | senior | Continuation, carrier, pinning, structured concurrency, khi nào không dùng | L D B | ⬜ |
| 13 | `forkjoin` | ForkJoinPool & work stealing | senior | Common pool, parallel stream, khi nào chậm hơn | L D | ⬜ |
| 14 | `reactive` | Reactive & WebFlux | senior | Backpressure, scheduler, so với virtual thread | L D Sc | ⬜ |
| 15 | `testing-concurrency` | Kiểm thử code đồng thời | senior | jcstress, test flaky, race detector | L B | ⬜ |

### 4. JVM (`jvm`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `jvm-memory-areas` | Vùng nhớ của JVM | mid | Heap, metaspace, stack, direct memory, code cache; các loại OOM | A L D | ⬜ |
| 2 | `gc-fundamentals` | GC hoạt động thế nào | mid | Reachability, generational, mark-sweep-compact, safepoint | A L S | ⬜ |
| 3 | `gc-algorithms` | G1, ZGC, Shenandoah, Parallel | senior | Pause và throughput, chọn GC, generational ZGC | L D Sc | ⬜ |
| 4 | `gc-logs-tuning` | Đọc GC log & tuning | senior | `-Xlog:gc`, sizing heap, các dấu hiệu bất thường | L T | ⬜ |
| 5 | `memory-leak` | Memory leak & heap dump | senior | MAT, dominator tree, leak hay gặp trong Spring | L T | ⬜ |
| 6 | `classloading` | ClassLoader | senior | Delegation, fat jar của Spring Boot, metaspace leak | L D B | ⬜ |
| 7 | `jit` | JIT compiler | senior | Tiered C1/C2, inlining, escape analysis, deopt, warmup, JMH | L D B | ⬜ |
| 8 | `jvm-containers` | JVM trong container | senior | cgroup, `MaxRAMPercentage`, CPU limit, OOMKilled và OutOfMemoryError, NMT | L T | ⬜ |
| 9 | `jvm-diagnostic-tools` | Bộ công cụ chẩn đoán JVM | mid | `jcmd`, `jstack`, `jmap`, JFR, async-profiler | L T | ⬜ |
| 10 | `startup-native` | Khởi động nhanh: CDS, CRaC, GraalVM native | senior | Trade-off giữa startup, peak và độ phức tạp build | L Sc | ⬜ |

### 5. Spring (`spring`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `ioc-di` | IoC & Dependency Injection | junior | Container, bean definition, kiểu inject, circular dependency | A L D | ⬜ |
| 2 | `bean-lifecycle-scopes` | Bean lifecycle & scope | mid | Callback, `BeanPostProcessor`, prototype trong singleton | L S B | ⬜ |
| 3 | `spring-aop-proxy` | AOP & proxy | mid | JDK và CGLIB proxy, self-invocation, thứ tự advice | L D B | ⬜ |
| 4 | `transactional-deep` | @Transactional chuyên sâu | senior | Propagation, rollback rule, `readOnly`, self-invocation, `@TransactionalEventListener` | L S B T | ⬜ |
| 5 | `spring-boot-autoconfig` | Spring Boot auto-configuration | mid | Condition, starter, binding property, profile, Actuator | L D B | ⬜ |
| 6 | `spring-mvc-flow` | Request đi qua Spring MVC | mid | DispatcherServlet, filter và interceptor, `@ControllerAdvice`, validation | L D B | ⬜ |
| 7 | `spring-data-jpa` | Spring Data JPA & Hibernate | senior | Dirty checking, flush mode, persistence context, bulk op, count query | L B T | ⬜ |
| 8 | `spring-security-architecture` | Kiến trúc Spring Security | senior | Filter chain, `AuthenticationManager`, SecurityContext, method security, resource server | L D B | ⬜ |
| 9 | `spring-async-events` | @Async, @Scheduled & event | mid | Thread pool mặc định, `@Scheduled` một thread, event đồng bộ và bất đồng bộ | L B | ⬜ |
| 10 | `spring-webflux` | Spring WebFlux | senior | Event loop, block trong reactive, khi nào nên dùng | L D B | ⬜ |
| 11 | `spring-observability` | Micrometer & tracing | mid | Metric, tracing, log correlation | L T | ⬜ |

### 6. Testing (`testing`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `test-strategy` | Test pyramid & chiến lược test | junior | Unit, integration, e2e; testing trophy; test gì, không test gì | A L Sc | ⬜ |
| 2 | `junit5` | JUnit 5 chuyên sâu | mid | Lifecycle, parameterized, extension, chạy song song | L B | ⬜ |
| 3 | `mockito` | Mockito & test double | mid | Mock, stub, spy, fake; strict stubbing; khi nào không nên mock | L B | ⬜ |
| 4 | `testcontainers` | Testcontainers | mid | DB thật, singleton container, reuse, chạy trên CI | L B | ⬜ |
| 5 | `spring-boot-test` | Spring Boot Test | mid | Test slice, context caching, `@MockBean` làm chậm suite | L B T | ⬜ |
| 6 | `test-design` | Thiết kế test tốt | mid | AAA, test smell, mutation testing (PIT), mức coverage | L B | ⬜ |
| 7 | `flaky-tests` | Test chập chờn | mid | Thời gian, thứ tự, đồng thời, `Clock`, Awaitility | L T | ⬜ |
| 8 | `contract-testing` | Contract testing | senior | Consumer-driven, Pact, Spring Cloud Contract | L D Sc | ⬜ |
| 9 | `load-testing` | Load & performance testing | senior | Mô hình tải, k6/Gatling, coordinated omission, đọc kết quả | L Sc | ⬜ |

### 7. Database (`database`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `index-execution-plan` | Index & Execution Plan | mid | B-tree, composite, covering, EXPLAIN, các loại index | A L D B | ✅ |
| 2 | `transaction-isolation` | Transaction & Isolation Level | mid | Hiện tượng, PostgreSQL và MySQL, lost update | A L S B | ✅ |
| 3 | `n-plus-one` | N+1 Query | mid | Lazy loading, fetch join, batch fetching | A L B T | ✅ |
| 4 | `partitioning-index` | Partitioning & Global/Local Index | senior | Pruning, local và global, unique key, DynamoDB GSI/LSI | A L D Sc | ✅ |
| 5 | `sql-joins-deep` | JOIN & tối ưu query | mid | Nested loop, hash, merge join; thứ tự join; subquery, CTE, window function | L D B | ⬜ |
| 6 | `locking-deadlock-db` | Lock & deadlock trong database | senior | Row và table lock, gap lock, đọc deadlock log, lock timeout, advisory lock | L S T | ⬜ |
| 7 | `mvcc-vacuum` | MVCC, VACUUM & undo log | senior | Phiên bản dòng PostgreSQL và InnoDB, autovacuum, bloat, XID wraparound | L D T | ⬜ |
| 8 | `connection-pool` | Connection pool | mid | Sizing HikariCP, timeout, leak, `max_connections`, PgBouncer | A L Sc T | ⬜ |
| 9 | `replication-ha` | Replication & high availability | senior | Sync và async, replica lag, read-your-writes, failover, split brain | L D T | ⬜ |
| 10 | `sharding-strategies` | Sharding | senior | Hash, range, directory; resharding; query xuyên shard; Vitess, Citus | L D Sc | ⬜ |
| 11 | `schema-migration` | Migration không downtime | senior | Flyway/Liquibase, expand-contract, online DDL, backfill lớn | L B Sc | ⬜ |
| 12 | `data-modeling` | Mô hình hoá dữ liệu | mid | Chuẩn hoá và phi chuẩn hoá, khoá (UUID v7), soft delete, audit | L Sc | ⬜ |
| 13 | `storage-engine` | Storage engine: B+tree, LSM, WAL | senior | Buffer pool, WAL, checkpoint, fsync, write amplification | L D | ⬜ |
| 14 | `nosql-overview` | NoSQL: chọn loại nào | mid | Document, key-value, wide-column, graph; mô hình theo access pattern | L Sc | ⬜ |
| 15 | `query-patterns` | Các mẫu query hiệu năng | mid | Keyset pagination, `count(*)`, batch insert/upsert, `OR` và `UNION` | L B | ⬜ |
| 16 | `backup-restore` | Backup, restore & PITR | mid | Logical và physical, PITR, RPO/RTO, diễn tập restore | L Sc | ⬜ |

### 8. Caching & Messaging (`caching-messaging`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `cache-patterns` | Cache patterns | mid | Cache-aside, read/write-through, write-behind, invalidation, consistency | A L D | ⬜ |
| 2 | `cache-failures` | Stampede, penetration, avalanche, hot key | senior | Lock, refresh sớm theo xác suất, Bloom filter, jitter TTL | L S T | ⬜ |
| 3 | `local-cache` | Local & multi-level cache | mid | Caffeine, near cache, invalidation giữa các node | L Sc | ⬜ |
| 4 | `redis-internals` | Redis bên trong | senior | Kiểu dữ liệu, single thread và I/O thread, RDB/AOF, eviction, bộ nhớ | L D T | ⬜ |
| 5 | `redis-ha-cluster` | Redis Sentinel & Cluster | senior | Replication, hash slot, failover mất dữ liệu | L D | ⬜ |
| 6 | `redis-use-cases` | Redis cho lock, rate limit, leaderboard | senior | Distributed lock và tranh luận Redlock, Lua, sorted set | L B Sc | ⬜ |
| 7 | `messaging-fundamentals` | Messaging cơ bản | mid | Queue và pub/sub, at-least-once, thứ tự, consumer idempotent, DLQ | A L D | ⬜ |
| 8 | `kafka-architecture` | Kiến trúc Kafka | senior | Partition, replication, ISR, `acks`, leader election, KRaft | L D | ⬜ |
| 9 | `kafka-producer-consumer` | Kafka producer & consumer chuyên sâu | senior | Idempotent producer, transaction, consumer group, rebalance, commit offset | L S B | ⬜ |
| 10 | `kafka-troubleshooting` | Vận hành & sự cố Kafka | senior | Consumer lag, rebalance storm, poison message, số partition | L T | ⬜ |
| 11 | `rabbitmq` | RabbitMQ & so sánh với Kafka | mid | Exchange, ack, prefetch, quorum queue; chọn công cụ | L D Sc | ⬜ |

### 9. Security (`security`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `authn-authz-basics` | AuthN & AuthZ cơ bản | junior | Session và token, hash mật khẩu (bcrypt/argon2), MFA | A L D | ⬜ |
| 2 | `jwt-deep` | JWT chuyên sâu | mid | Cấu trúc, thuật toán ký, validate, hết hạn/refresh, thu hồi, nơi lưu | L B T | ⬜ |
| 3 | `oauth2-oidc` | OAuth2 & OpenID Connect | senior | Authorization code + PKCE, client credentials, scope, ID token và access token | L D Sc | ⬜ |
| 4 | `authorization-models` | Mô hình phân quyền | senior | RBAC, ABAC, ReBAC, policy engine (OPA), cô lập multi-tenant, IDOR | L B Sc | ⬜ |
| 5 | `owasp-top10` | OWASP Top 10 với Java/Spring | mid | Injection, broken access control, SSRF, XSS, CSRF, deserialization | L B | ⬜ |
| 6 | `cryptography-basics` | Mật mã cho kỹ sư | mid | Hash, mã hoá, encoding; đối xứng và bất đối xứng; envelope encryption, KMS | A L D | ⬜ |
| 7 | `secret-management` | Quản lý secret | mid | Vault, KMS, xoay vòng, secret lọt vào git | L T | ⬜ |
| 8 | `api-security` | Bảo mật API | senior | Rate limit, CORS, mTLS giữa service, API gateway, validate input | L Sc | ⬜ |
| 9 | `secure-sdlc` | Bảo mật trong quy trình phát triển | senior | Threat modeling (STRIDE), SAST/DAST/SCA, supply chain | L Sc | ⬜ |

### 10. Performance & Troubleshooting (`performance`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `java-high-cpu` | Ứng dụng Java CPU 100% | mid | `top -H`, thread dump, regex backtracking | L T | ✅ |
| 2 | `perf-methodology` | Phương pháp phân tích hiệu năng | mid | USE/RED, percentile, Little's law, Amdahl | A L D | ⬜ |
| 3 | `observability` | Observability: log, metric, trace | mid | OpenTelemetry, structured log, correlation id, SLI/SLO | L D Sc | ⬜ |
| 4 | `slow-api` | Điều tra API chậm | senior | Lần theo từng tầng: DB, downstream, GC, thread pool, mạng | L T | ⬜ |
| 5 | `thread-pool-exhaustion` | Request treo vì cạn thread | senior | Thread dump toàn WAITING, timeout thiếu, bulkhead | L T | ⬜ |
| 6 | `memory-growth-oom` | Bộ nhớ tăng dần & OOM | senior | Heap và native, leak, OOMKilled | L T | ⬜ |
| 7 | `db-performance` | Database chậm trên production | senior | `pg_stat_statements`, lock wait, cạn connection pool, replica lag | L T | ⬜ |
| 8 | `profiling` | Profiling | senior | async-profiler, flame graph, JFR, allocation profiling | L D T | ⬜ |
| 9 | `tail-latency` | Tail latency, timeout & retry | senior | Retry khuếch đại tải, timeout budget, hedging | L S Sc | ⬜ |
| 10 | `client-performance` | Hiệu năng phía client | mid | Payload, nén, HTTP cache header, CDN, Core Web Vitals | L Sc | ⬜ |
| 11 | `capacity-planning` | Capacity planning & autoscaling | senior | Ước lượng tải, headroom, autoscale theo metric nào | L Sc | ⬜ |

### 11. Design (`design`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `solid` | SOLID | junior | Từng nguyên tắc với ví dụ vi phạm và cách sửa | A L B | ⬜ |
| 2 | `creational-patterns` | Creational patterns | mid | Factory, Builder, Singleton (và vì sao nên tránh) | L B | ⬜ |
| 3 | `structural-patterns` | Structural patterns | mid | Adapter, Decorator, Proxy, Facade; ví dụ trong JDK và Spring | L D B | ⬜ |
| 4 | `behavioral-patterns` | Behavioral patterns | mid | Strategy, Template Method, Observer, Chain of Responsibility, State | L B | ⬜ |
| 5 | `clean-hexagonal` | Clean & Hexagonal Architecture | senior | Port/adapter, quy tắc phụ thuộc, khi nào quá tay | A L D Sc | ⬜ |
| 6 | `ddd-strategic` | DDD chiến lược | senior | Bounded context, context map, ubiquitous language | A L D Sc | ⬜ |
| 7 | `ddd-tactical` | DDD chiến thuật | senior | Aggregate, entity, value object, domain event, kích thước aggregate | L B Sc | ⬜ |
| 8 | `modular-monolith` | Modular monolith | senior | Ranh giới module, kiểm tra kiến trúc (ArchUnit), tách dần | L Sc | ⬜ |
| 9 | `refactoring-tech-debt` | Refactoring & nợ kỹ thuật | mid | Code smell, refactor an toàn, đo và trả nợ | L B | ⬜ |

### 12. Distributed Systems (`distributed`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `consistency-cap` | Consistency, CAP & PACELC | senior | Linearizable, causal, eventual; CAP và PACELC thật sự nói gì | A L D | ⬜ |
| 2 | `microservices-tradeoffs` | Microservices: khi nào và chia thế nào | senior | Chia theo domain, chi phí phân tán, khi nào giữ monolith | L Sc | ⬜ |
| 3 | `service-communication` | Giao tiếp giữa service | mid | REST, gRPC, async; API gateway; service discovery; load balancing | L D | ⬜ |
| 4 | `resilience-patterns` | Timeout, retry, circuit breaker, bulkhead | senior | Backoff + jitter, trạng thái circuit breaker, fallback | L S B | ⬜ |
| 5 | `idempotency` | Idempotency | senior | Idempotency key, dedup, exactly-once là gì thật sự | A L B Sc | ⬜ |
| 6 | `saga` | Saga | senior | Orchestration và choreography, compensation | L S Sc | ⬜ |
| 7 | `outbox-cdc` | Transactional outbox & CDC | senior | Vấn đề dual write, Debezium, thứ tự và trùng lặp | L D B | ⬜ |
| 8 | `cqrs-event-sourcing` | CQRS & Event Sourcing | senior | Read model, projection, snapshot, khi nào không dùng | L D Sc | ⬜ |
| 9 | `distributed-transactions` | 2PC & giao dịch phân tán | senior | 2PC, XA, vì sao tránh, các lựa chọn thay thế | L S | ⬜ |
| 10 | `consensus` | Consensus & leader election | architect | Raft, quorum, split brain, etcd/ZooKeeper | L S D | ⬜ |
| 11 | `distributed-locks` | Distributed lock & fencing token | senior | Lease, fencing, vì sao lock dựa trên thời gian nguy hiểm | L S B | ⬜ |
| 12 | `clocks-ids` | Đồng hồ, thứ tự & sinh ID | senior | Lệch đồng hồ, Lamport/vector clock, snowflake, UUID v7 | L D | ⬜ |
| 13 | `rate-limiting` | Rate limiting | senior | Token bucket, leaky bucket, sliding window; phân tán | L S Sc | ⬜ |

### 13. Cloud & DevOps (`cloud-devops`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `docker` | Docker chuyên sâu | mid | Layer, multi-stage, image cho JVM, bảo mật image | L D B | ⬜ |
| 2 | `kubernetes-core` | Kubernetes cơ bản | mid | Pod, Deployment, Service, Ingress, ConfigMap/Secret | A L D | ⬜ |
| 3 | `kubernetes-operations` | Vận hành ứng dụng trên Kubernetes | senior | Probe, requests/limits, HPA, rolling update, PDB, CrashLoopBackOff, OOMKilled | L T | ⬜ |
| 4 | `aws-core` | AWS cho kỹ sư backend | mid | VPC, EC2, ALB/NLB, S3, RDS, IAM | L D Sc | ⬜ |
| 5 | `cloud-networking` | Network trên cloud | senior | Subnet, NAT, security group, PrivateLink, DNS nội bộ, LB L4 và L7 | L D T | ⬜ |
| 6 | `ci-cd-pipeline` | CI/CD pipeline | mid | Các stage, artifact, trunk-based, feature flag | A L D | ⬜ |
| 7 | `deployment-strategies` | Rolling, blue-green, canary | senior | Rollback, tương thích schema và API khi deploy | L S Sc | ⬜ |
| 8 | `infrastructure-as-code` | Infrastructure as Code & GitOps | mid | Terraform state, module, drift, Argo CD | L B | ⬜ |
| 9 | `high-availability-dr` | High availability & disaster recovery | senior | Multi-AZ, multi-region, RPO/RTO, diễn tập | L D Sc | ⬜ |
| 10 | `incident-management` | Alerting, on-call & postmortem | mid | Alert theo SLO, runbook, postmortem không đổ lỗi | L T | ⬜ |
| 11 | `serverless` | Serverless | mid | Lambda, cold start, giới hạn, khi nào phù hợp | L Sc | ⬜ |

### 14. System Design (`system-design`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `sd-framework` | Khung trả lời System Design | mid | Yêu cầu, ước lượng, high-level, deep dive, trade-off, quản lý thời gian | A L D | ⬜ |
| 2 | `back-of-envelope` | Ước lượng nhanh | mid | Các con số cần nhớ, QPS, dung lượng, băng thông | L B | ⬜ |
| 3 | `design-url-shortener` | Thiết kế URL shortener | mid | Sinh mã, redirect, cache, analytics | L D Sc | ⬜ |
| 4 | `design-rate-limiter` | Thiết kế rate limiter | senior | Thuật toán, phân tán, nơi đặt | L D Sc | ⬜ |
| 5 | `design-news-feed` | Thiết kế news feed | senior | Fan-out on write và on read, người dùng nổi tiếng, xếp hạng | L D Sc | ⬜ |
| 6 | `design-chat` | Thiết kế ứng dụng chat | senior | WebSocket, presence, thứ tự tin nhắn, đồng bộ nhiều thiết bị | L D Sc | ⬜ |
| 7 | `design-notification` | Thiết kế hệ thống thông báo | senior | Nhiều kênh, retry, dedup, tuỳ chọn của người dùng | L D Sc | ⬜ |
| 8 | `design-search-autocomplete` | Thiết kế autocomplete | senior | Trie, top-k, cập nhật, cache | L D Sc | ⬜ |
| 9 | `design-payment` | Thiết kế hệ thống thanh toán | architect | Idempotency, sổ cái kép, đối soát, trạng thái | L D Sc | ⬜ |
| 10 | `design-flash-sale` | Thiết kế flash sale / bán vé | architect | Chống bán vượt tồn kho, hàng đợi, giữ chỗ có thời hạn | L D Sc | ⬜ |
| 11 | `design-file-storage` | Thiết kế lưu trữ file / video | senior | Upload theo phần, CDN, transcoding, metadata | L D Sc | ⬜ |
| 12 | `design-ride-hailing` | Thiết kế ứng dụng gọi xe | architect | Geo index (geohash, quadtree), ghép cặp, cập nhật vị trí | L D Sc | ⬜ |
| 13 | `design-id-generator` | Thiết kế bộ sinh ID phân tán | senior | Snowflake, sequence theo khối, thứ tự | L D Sc | ⬜ |
| 14 | `design-metrics-logging` | Thiết kế hệ thống metric/log | architect | Time-series, ingestion, downsampling, chi phí lưu trữ | L D Sc | ⬜ |

### 15. Solution Architect (`solution-architect`)

| # | id | Bài | Level | Trọng tâm chuyên sâu | Block | |
|---|---|---|---|---|---|---|
| 1 | `sa-role` | Vai trò Solution Architect | senior | Khác tech lead và enterprise architect, làm việc với stakeholder | A L | ⬜ |
| 2 | `nfr-quality-attributes` | NFR & quality attribute | architect | Định lượng NFR, quality attribute scenario, utility tree | L Sc | ⬜ |
| 3 | `architecture-tradeoffs` | Ra quyết định & trade-off | architect | Quyết định một chiều và hai chiều, ma trận đánh giá, rủi ro | L Sc | ⬜ |
| 4 | `adr-c4` | ADR, C4 model & tài liệu kiến trúc | senior | Viết ADR, các mức C4, arc42 | L D B | ⬜ |
| 5 | `architecture-styles` | Chọn kiểu kiến trúc | architect | Layered, microservices, event-driven, serverless, space-based | L D Sc | ⬜ |
| 6 | `integration-patterns` | Integration patterns | architect | EIP, API-led, ESB, file và event, tích hợp hệ thống cũ | L D Sc | ⬜ |
| 7 | `migration-modernization` | Migration & hiện đại hoá | architect | Strangler fig, 6R khi lên cloud, migrate dữ liệu | L D Sc | ⬜ |
| 8 | `cost-finops` | Ước tính chi phí & FinOps | architect | Mô hình chi phí cloud, tối ưu, đánh đổi chi phí và độ tin cậy | L Sc | ⬜ |
| 9 | `multi-tenancy` | Kiến trúc multi-tenant | architect | Mức cô lập, noisy neighbor, dữ liệu theo tenant | L D Sc | ⬜ |
| 10 | `build-vs-buy` | Build hay buy & chọn vendor | architect | Tiêu chí, PoC, lock-in, tổng chi phí sở hữu (TCO) | L Sc | ⬜ |
| 11 | `architecture-review` | Review một kiến trúc | architect | Risk storming, ATAM rút gọn, câu hỏi cần hỏi | L Sc | ⬜ |
| 12 | `communicating-architecture` | Trình bày kiến trúc cho stakeholder | architect | Sơ đồ theo người nghe, xử lý phản biện, viết đề xuất | L Sc | ⬜ |

## 4. Tổng quan

| Track | Đã có | Tổng |
|---|---|---|
| Nền tảng CS | 1 | 13 |
| Core Java | 5 | 16 |
| Concurrency | 5 | 15 |
| JVM | 0 | 10 |
| Spring | 0 | 11 |
| Testing | 0 | 9 |
| Database | 4 | 16 |
| Caching & Messaging | 0 | 11 |
| Security | 0 | 9 |
| Performance & Troubleshooting | 1 | 11 |
| Design | 0 | 9 |
| Distributed Systems | 0 | 13 |
| Cloud & DevOps | 0 | 11 |
| System Design | 0 | 14 |
| Solution Architect | 0 | 12 |
| **Tổng** | **16** | **180** |
