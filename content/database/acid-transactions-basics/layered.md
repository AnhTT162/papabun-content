## Quick

[[transaction|Transaction]] gom nhiều câu lệnh thành một đơn vị: `COMMIT` thì mọi thay đổi cùng có hiệu lực, `ROLLBACK` hoặc lỗi thì không thay đổi nào còn lại. [[acid|ACID]] là bốn đảm bảo của nó. **Mặc định mỗi câu lệnh tự là một transaction ([[autocommit]])**, nên nhiều thao tác phải đi cùng nhau thì phải mở transaction rõ ràng.

## Interview

Bốn chữ của ACID:
- **Atomicity**: tất cả hoặc không. InnoDB ghi [[undo-log|undo log]] và khi rollback thì áp ngược từng thay đổi, nên rollback một transaction lớn rất lâu. PostgreSQL không có undo: phiên bản dòng mới được ghi ra, rollback chỉ đánh dấu transaction là aborted nên gần như tức thì, còn các phiên bản bỏ đi được VACUUM dọn sau.
- **Consistency**: transaction đưa dữ liệu từ trạng thái hợp lệ sang trạng thái hợp lệ, theo các ràng buộc (`UNIQUE`, foreign key, `CHECK`). Quy tắc nghiệp vụ không khai báo được thành ràng buộc, như "tổng tiền không đổi khi chuyển khoản", là trách nhiệm của ứng dụng.
- **Isolation**: các transaction chạy đồng thời không thấy trạng thái dở dang của nhau, ở mức do [[isolation-level|isolation level]] quyết định (bài Transaction & Isolation Level).
- **Durability**: đã commit thì không mất dù sập máy. Database ghi [[wal|WAL]] (PostgreSQL) hoặc redo log (InnoDB) xuống đĩa và `fsync` trước khi báo commit thành công.

**Autocommit**: JDBC, PostgreSQL và MySQL mặc định coi mỗi câu lệnh là một transaction tự commit. Trong Spring, `@Transactional` tắt autocommit trên connection, chạy method, rồi commit hoặc rollback. Không có `@Transactional`, mỗi lời gọi repository (`save`, `delete`) tự commit ngay khi xong.

**Lỗi giữa transaction khác nhau giữa hai database**:
- **PostgreSQL**: một câu lệnh lỗi làm cả transaction hỏng. Mọi lệnh sau đó báo `current transaction is aborted, commands ignored until end of transaction block` cho tới khi `ROLLBACK`.
- **MySQL**: phần lớn lỗi (trùng khoá, vi phạm ràng buộc, chờ lock quá hạn) chỉ rollback câu lệnh đó; transaction vẫn tiếp tục, và ứng dụng phải tự quyết định rollback. Ngoại lệ quan trọng: [[deadlock]] rollback **cả** transaction, ứng dụng phải chạy lại từ đầu.

**Bẫy hay gặp**: transaction quá dài (gọi API ngoài, chờ người dùng) giữ lock và connection; transaction quá ngắn (mỗi bước tự commit) thì mất atomicity. Ranh giới transaction nên ôm đúng một đơn vị nghiệp vụ, và chỉ chứa thao tác database.

## Deep

- **DDL trong transaction**: PostgreSQL cho `CREATE TABLE`, `ALTER TABLE` nằm trong transaction và rollback được. MySQL thì mỗi DDL gây [[implicit-commit|implicit commit]]: commit luôn mọi thứ trước nó, tự commit chính nó, và kết thúc transaction nên các lệnh sau đó chạy ở chế độ autocommit. Một script migration "BEGIN; UPDATE ...; ALTER ...; UPDATE ...; ROLLBACK" trên MySQL không rollback được lệnh nào. (MySQL 8.0 có atomic DDL: bản thân một lệnh DDL không bị dở dang khi sập, nhưng vẫn commit ngầm.)
- **[[savepoint|Savepoint]]**: `SAVEPOINT s1` rồi `ROLLBACK TO s1` huỷ một phần transaction. Spring dùng savepoint cho `Propagation.NESTED`. Trong PostgreSQL, savepoint còn là cách tiếp tục sau một lệnh lỗi.
- **Durability có thể được nới lỏng**: PostgreSQL có `synchronous_commit = off` (có thể mất vài trăm mili giây dữ liệu gần nhất khi sập, nhưng không hỏng dữ liệu). InnoDB có `innodb_flush_log_at_trx_commit = 2` hoặc `0`. Đổi lấy throughput; chỉ dùng cho dữ liệu chấp nhận mất.
- **Transaction mở lâu gây hại âm thầm**: PostgreSQL không dọn được phiên bản dòng cũ mà transaction đó còn có thể thấy (giữ lùi xmin horizon), nên bảng và index phình dần; InnoDB thì history list (undo chưa purge) tăng. Phát hiện bằng `pg_stat_activity` (`state = 'idle in transaction'`, `xact_start` cũ) hoặc `information_schema.innodb_trx`. Phòng bằng `idle_in_transaction_session_timeout`, `transaction_timeout` (PostgreSQL 17+) và `@Transactional(timeout = ...)`.
- **Commit chậm vì đĩa**: mỗi commit chờ `fsync`. Ghi từng dòng trong vòng lặp với autocommit sẽ chậm hơn hàng chục lần so với gom vào một transaction hoặc dùng batch.
- **Read-only transaction** (`SET TRANSACTION READ ONLY`, hoặc `@Transactional(readOnly = true)`) cho phép database và Hibernate bỏ qua một số việc như [[dirty-checking|dirty checking]], và có thể định tuyến sang replica.
- **Transaction không trải qua nhiều hệ thống**: commit database xong rồi gửi Kafka lỗi, hoặc ngược lại, thì không rollback chung được. Đó là bài toán [[dual-write|dual write]] (bài Transactional outbox & CDC).
- **Commit thành công nhưng client không biết**: mạng đứt ngay sau `COMMIT` thì client nhận lỗi trong khi dữ liệu đã ghi. Retry mù sẽ ghi hai lần; thao tác quan trọng cần [[idempotency-key|idempotency key]].
