## Quick

`@Transactional` hoạt động nhờ **proxy**: proxy lấy connection, tắt [[autocommit]], gắn transaction vào **thread hiện tại**, gọi method, rồi commit, hoặc rollback khi method ném exception. **Mặc định chỉ rollback với `RuntimeException` và `Error`; checked exception vẫn commit.** Đặt ranh giới transaction ở method service ứng với một use case, giữ nó ngắn, và đừng gọi hệ thống ngoài bên trong.

## Interview

**Cơ chế**:
1. Bean có `@Transactional` được bọc proxy (bài AOP & proxy). Controller gọi `orderService.placeOrder()` là gọi vào proxy.
2. `TransactionInterceptor` hỏi `PlatformTransactionManager` (`JpaTransactionManager` khi có JPA) mở transaction: lấy connection từ pool, `setAutoCommit(false)`, gắn connection và `EntityManager` vào thread qua [[thread-local|ThreadLocal]].
3. Mọi repository, `JdbcTemplate` gọi trong method, trên **cùng thread**, dùng chung connection đó.
4. Method trả về bình thường thì commit. Ném exception thì xét rollback rule, rollback hoặc commit, rồi ném exception tiếp ra ngoài.

**Rollback rule**: mặc định rollback với unchecked exception, **commit** với checked exception (theo truyền thống EJB). Muốn rollback cả checked thì dùng `@Transactional(rollbackFor = Exception.class)`. Exception bị `catch` và nuốt trong method thì proxy không thấy, nên vẫn commit.

**Khi nào không có transaction dù có annotation**:
- Gọi method qua `this` trong cùng class ([[self-invocation]]): không qua proxy.
- Method `private`, hoặc object tự `new`.
- Code chạy ở thread khác (`@Async`, `CompletableFuture`, `parallelStream`): transaction gắn với thread gốc.

**Đặt ranh giới ở đâu**:
- Ở tầng service, một method cho một use case. Không đặt ở controller (giữ connection cả lúc ghi JSON). Không chỉ dựa vào transaction riêng của từng lệnh repository, vì hai lệnh `save` khi đó là hai transaction.
- Không gọi HTTP, gửi email hay đợi Kafka bên trong. Mỗi giây chờ là một connection bị giữ, pool cạn nhanh, và commit thất bại sau khi đã gửi đi thì không rút lại được ([[dual-write|dual write]]).

## Deep

- **Repository của Spring Data đã có transaction**: `SimpleJpaRepository` khai báo `@Transactional(readOnly = true)` ở class và `@Transactional` cho method ghi. Gọi `save` ngoài transaction vẫn chạy, nhưng mỗi lời gọi tự commit riêng.
- **Visibility của method**: Spring 6 hỗ trợ `@Transactional` trên method `protected` và package-private với proxy CGLIB; Spring 5 chỉ áp cho `public` (method khác bị bỏ qua không báo). Method `private` thì không bao giờ được proxy.
- **Annotation trên interface hay class**: từ Spring 5.0, annotation trên interface chạy với cả JDK proxy lẫn CGLIB, nhưng bị bỏ qua ở chế độ AspectJ. Spring khuyên đặt trên class implement.
- **`readOnly = true`**: Spring đặt connection read-only, flush mode `MANUAL` và session read-only cho Hibernate: không giữ bản chụp, bỏ dirty checking, không có `UPDATE` nào lọt ra. Định tuyến sang replica chỉ có khi bạn dùng routing `DataSource` hoặc driver hỗ trợ. Nó không ngăn ghi bằng native SQL trên mọi database.
- **Timeout**: `@Transactional(timeout = 5)` chỉ được kiểm tra ở một số điểm (khi JDBC tạo statement đặt query timeout theo thời gian còn lại). Hết hạn thì lệnh SQL kế tiếp ném `TransactionTimedOutException`; không phải hard timeout cho cả method, code Java chạy lâu không bị ngắt. `timeout`, `readOnly` và `isolation` chỉ áp khi method mở transaction mới (`REQUIRED` không có transaction sẵn, hoặc `REQUIRES_NEW`); method tham gia transaction có sẵn thì bị bỏ qua.
- **Rollback cả checked exception cho toàn ứng dụng**: Spring 6.2 có `@EnableTransactionManagement(rollbackOn = RollbackOn.ALL_EXCEPTIONS)`. Tài liệu Spring khuyên bật, trừ khi code dựa vào quy ước business exception kiểu EJB (nhất là với Kotlin, vốn không có checked exception). Công tắc này áp cả cho `jakarta.transaction.Transactional`.
- **"Transaction silently rolled back because it has been marked as rollback-only"**: method bên trong (cùng transaction) ném `RuntimeException`, bên ngoài `catch` rồi tiếp tục; transaction đã bị đánh dấu chỉ được rollback nên commit thất bại với `UnexpectedRollbackException`. Chi tiết và cách dùng `REQUIRES_NEW` ở bài @Transactional chuyên sâu.
- **Test với `@Transactional`**: Spring Test rollback cuối mỗi test. Thường không có flush, nên lỗi ràng buộc chỉ xảy ra lúc flush sẽ không lộ ra; gọi `flush()` trong test, hoặc test không bọc transaction.
- **Nhiều transaction manager**: ứng dụng có hai `DataSource` cần hai manager, và `@Transactional("ordersTransactionManager")` để chọn. Transaction không trải qua hai database; cần thiết kế lại (outbox, saga) thay vì kỳ vọng XA.
- **Programmatic**: `TransactionTemplate.execute(status -> ...)` cho ranh giới nhỏ hơn method, hoặc khi cần transaction trong code không phải bean. Không bị bẫy self-invocation.
- **Phát hiện transaction dài**: log của `JpaTransactionManager` ở mức DEBUG in mở và commit; metric của HikariCP (`hikaricp.connections.usage`) cho thấy connection bị giữ bao lâu; phía database xem bài ACID & transaction cơ bản.
