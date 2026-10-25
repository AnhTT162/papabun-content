## Quick

[[propagation|Propagation]] quyết định chuyện gì xảy ra khi một method `@Transactional` được gọi trong lúc **đã có** transaction. Mặc định `REQUIRED` **tham gia** transaction có sẵn: một bước lỗi là cả transaction phải rollback, kể cả khi bên ngoài `catch` lỗi đó. `REQUIRES_NEW` tạm dừng transaction ngoài và mở transaction riêng trên **connection thứ hai**. `NESTED` dùng [[savepoint]] trên cùng connection. Chọn sai propagation gây ra `UnexpectedRollbackException`, cạn pool, hoặc một request tự chờ lock của chính nó.

## Interview

**Bảy kiểu propagation**:
- `REQUIRED` (mặc định): có thì tham gia, chưa có thì mở mới.
- `REQUIRES_NEW`: luôn mở mới; transaction ngoài bị tạm dừng nhưng **vẫn giữ connection và lock**.
- `NESTED`: savepoint trong transaction ngoài; lỗi thì rollback tới savepoint, transaction ngoài chạy tiếp.
- `SUPPORTS`: có thì tham gia, không có thì chạy không transaction.
- `NOT_SUPPORTED`: tạm dừng transaction ngoài, chạy không transaction.
- `MANDATORY`: bắt buộc đã có transaction, không thì ném lỗi.
- `NEVER`: có transaction thì ném lỗi.

**[[rollback-only|Rollback-only]]**: method bên trong (tham gia transaction) ném `RuntimeException`. Proxy của nó không được rollback transaction chung, nên **đánh dấu rollback-only**. Bên ngoài `catch` rồi trả về bình thường; lúc commit, Spring thấy dấu đó, rollback và ném `UnexpectedRollbackException`. Client nhận lỗi 500, dữ liệu mất, dù code "đã xử lý" lỗi.

**Cái giá của `REQUIRES_NEW`**:
- Mỗi request cần hai connection cùng lúc. Pool 10 connection với 10 request đồng thời là [[pool-deadlock|pool deadlock]].
- Transaction mới không thấy dữ liệu chưa commit của transaction ngoài, và phải chờ nếu đụng dòng transaction ngoài đang khoá. Transaction ngoài lại đang chờ nó trả về: request treo tới [[lock-timeout|lock timeout]].
- Transaction mới commit trước. Transaction ngoài rollback sau đó thì phần đã commit vẫn còn.

**Khi nào không có tác dụng**: gọi qua `this` ([[self-invocation]]); thuộc tính của method chỉ tham gia transaction có sẵn bị bỏ qua (bài @Transactional cơ bản).

**[[transactional-event-listener|`@TransactionalEventListener`]]** có bốn phase:
- `BEFORE_COMMIT`: vẫn trong transaction, lỗi làm rollback.
- `AFTER_COMMIT` (mặc định), `AFTER_ROLLBACK`, `AFTER_COMPLETION`: transaction đã xong. Ghi database ở đây phải mở transaction mới, và lỗi không rollback được gì.

## Deep

- **`NESTED` chỉ chắc chắn chạy với JDBC**: `DataSourceTransactionManager` (và `JdbcTemplate`) hỗ trợ savepoint mặc định. `JpaTransactionManager` mặc định `nestedTransactionAllowed = false` nên ném `NestedTransactionNotSupportedException`. Bật lên thì savepoint chỉ rollback câu SQL, **không** rollback object trong persistence context: entity vẫn mang giá trị đã sửa và có thể bị flush lại.
- **Ai được rollback**: chỉ method **mở** transaction mới thực sự rollback hay commit. Method tham gia chỉ đặt dấu rollback-only. `AbstractPlatformTransactionManager.setGlobalRollbackOnParticipationFailure(false)` tắt hành vi này, nhưng khi đó bên ngoài phải tự đảm bảo dữ liệu nhất quán, rất dễ sai.
- **Repository của Spring Data cũng là method `@Transactional`**: `save()` ném `DataIntegrityViolationException` thì proxy của repository đã đánh dấu rollback-only trước khi bạn `catch`. Với PostgreSQL, transaction còn bị database đánh dấu hỏng (bài PostgreSQL vs MySQL). Muốn "thử insert, trùng thì thôi" thì dùng `INSERT ... ON CONFLICT DO NOTHING`, hoặc chạy bước đó trong transaction riêng.
- **Lỗi lúc flush nằm ngoài `try`**: với id `SEQUENCE` hoặc tự gán, `INSERT` chỉ chạy lúc flush hay commit, sau khi method đã trả về, nên `catch` quanh `save()` không bắt được lỗi unique (với `IDENTITY` thì `INSERT` chạy ngay trong `save()`). `saveAndFlush()` trong `try` giúp bắt lỗi để đổi thành lỗi nghiệp vụ, nhưng transaction đã bị đánh dấu rollback-only: muốn đi tiếp thì bước đó phải chạy trong transaction riêng.
- **`readOnly` khi tham gia**: method `@Transactional` (ghi) gọi từ method `readOnly = true` sẽ tham gia transaction read-only. Hibernate để flush mode `MANUAL`, thay đổi không được ghi và không báo lỗi; với PostgreSQL, câu ghi bằng SQL báo `cannot execute UPDATE in a read-only transaction`. `setValidateExistingTransaction(true)` trên transaction manager làm Spring ném `IllegalTransactionStateException` khi method không read-only tham gia transaction read-only, hoặc khi `isolation` khai báo khác transaction đang chạy (`timeout` không được kiểm tra).
- **Định tuyến sang replica**: [[routing-datasource|`AbstractRoutingDataSource`]] chọn đích theo `TransactionSynchronizationManager.isCurrentTransactionReadOnly()`. Cờ này được đặt **sau** khi transaction manager đã lấy connection, nên phải bọc bằng `LazyConnectionDataSourceProxy` để connection chỉ được lấy ở câu SQL đầu tiên. Từ Spring 6.1.2, `LazyConnectionDataSourceProxy` có sẵn `setReadOnlyDataSource` cho đúng việc này. Nhớ replica có độ trễ: đọc ngay sau khi ghi có thể ra dữ liệu cũ.
- **Rollback rule chi tiết**:
  - `rollbackFor`, `noRollbackFor` xét cả lớp cha; khi nhiều rule cùng khớp, rule gần nhất trong cây kế thừa thắng.
  - `rollbackForClassName = "CustomException"` so khớp theo chuỗi con của tên lớp, nên khớp cả `CustomExceptionV2`. Dùng dạng `Class` an toàn hơn.
  - Đánh dấu bằng code: `TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()`, hoặc `status.setRollbackOnly()` trong `TransactionTemplate`.
- **`SUPPORTS` không phải "có cũng được"**: không có transaction thì mỗi câu SQL tự commit, và Hibernate có thể tải lazy ngoài transaction. Nếu method thật sự cần transaction, dùng `MANDATORY` để lỗi lộ ra sớm ở test.
- **`NOT_SUPPORTED` không trả connection**: transaction ngoài bị tạm dừng vẫn giữ connection của nó. Bọc một báo cáo chạy lâu bằng `NOT_SUPPORTED` bên trong transaction không giảm số connection đang giữ.
- **Listener chi tiết**:
  - Từ Spring 6.1, listener phase sau commit (`AFTER_*`) có `@Transactional` (trên method; từ 6.2 xét cả trên class) bắt buộc là `REQUIRES_NEW` (từ 6.1.3 thêm `NOT_SUPPORTED`), nếu không ứng dụng lỗi lúc khởi động. Lý do: với `REQUIRED`, ghi trong `AFTER_COMMIT` sẽ không bao giờ được commit. Phase `BEFORE_COMMIT` được miễn từ 6.2.10.
  - `BEFORE_COMMIT` chạy trước khi `EntityManager` flush lần cuối, nên entity sửa trong listener vẫn được ghi cùng transaction.
  - Publish ngoài transaction thì listener bị bỏ qua, trừ khi `fallbackExecution = true` (bài @Async, @Scheduled & event).
  - Event chỉ nằm trong bộ nhớ: pod chết ngay sau commit là mất. Việc bắt buộc phải xảy ra (gửi message cho service khác) cần outbox.
- **Test**: test có `@Transactional` rollback cuối test, nhưng method `REQUIRES_NEW` bên trong commit thật vào database test, nên dữ liệu rò sang test sau. Listener `AFTER_COMMIT` không chạy trong test như vậy vì không có commit; dùng `TestTransaction.flagForCommit()` và `TestTransaction.end()`, hoặc test không bọc transaction.
- **Hai database**: `@Transactional` chỉ gắn với một transaction manager. `ChainedTransactionManager` (của Spring Data Commons) đã deprecated từ bản 2.5, và nó chỉ commit lần lượt chứ không phải two-phase commit: commit thứ hai lỗi thì thứ nhất đã commit. Dùng outbox hoặc saga (bài Saga).
