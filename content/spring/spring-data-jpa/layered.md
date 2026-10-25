## Quick

[[spring-data-repository|Spring Data JPA]] sinh code repository cho bạn, nhưng mọi thứ bên dưới vẫn là Hibernate: [[persistence-context|persistence context]], [[dirty-checking|dirty checking]], flush. Bốn chỗ hay gây sự cố ở hệ thống lớn: **persistence context phình** làm mỗi lần flush chậm dần; **[[bulk-update|bulk update]]** (`@Modifying`) đi thẳng xuống database và bỏ qua entity đang nằm trong bộ nhớ; **`Page` chạy thêm một câu `count`**; và **`equals`/`hashCode` của entity** viết sai làm entity "biến mất" khỏi `Set`.

## Interview

**Repository làm gì**:
- [[derived-query|Derived query]] (`findByEmailAndStatus`) được parse từ tên method lúc khởi động; tên sai là lỗi khởi động, không phải lỗi lúc chạy.
- `@Query` cho JPQL hoặc native SQL; projection (interface, record) để chỉ lấy cột cần.
- Method của `SimpleJpaRepository` có sẵn `@Transactional` (bài @Transactional cơ bản).

**Dirty checking tốn bao nhiêu**: mỗi lần flush, Hibernate so **mọi** entity managed với bản chụp của nó. Flush xảy ra trước commit và trước các query có thể bị ảnh hưởng ([[flush-mode|flush mode]] `AUTO`). Một vòng lặp mỗi lượt tải hoặc tạo một entity rồi chạy một query: lượt thứ n dirty check n entity, tổng chi phí tăng theo bình phương số dòng, và heap phình theo. Cách xử lý: chia lô theo transaction, `flush()` rồi `clear()`, `readOnly = true` cho phần chỉ đọc, hoặc projection thay cho entity.

**Bulk update và delete**:
- `@Modifying @Query("update ...")` chạy một câu SQL, không đi qua entity: persistence context không biết, nên entity đã tải vẫn mang giá trị cũ và có thể **ghi đè** kết quả bulk lúc flush.
- Bulk cũng bỏ qua `@Version`, callback `@PreUpdate`, cascade và auditing.
- Ngược lại, `deleteByStatus(...)` (derived delete) tải hết entity khớp bằng một `SELECT` rồi `remove()` từng cái (để cascade và `@PreRemove` vẫn chạy): 10.000 dòng là 10.000 câu `DELETE`, gộp được thành batch nếu bật `batch_size`.

**Phân trang**: `Page<T>` chạy thêm `SELECT count(*)`; trên bảng lớn có điều kiện phức tạp, câu `count` có thể chậm hơn cả câu lấy dữ liệu. Dùng `Slice<T>` (lấy `size + 1` dòng để biết còn trang sau) hoặc [[keyset-pagination|keyset]] khi không cần tổng số. `JOIN FETCH` collection kèm phân trang xem bài N+1 Query.

**`equals`/`hashCode`**: id tự sinh là `null` trước khi `persist`. Băm theo id thì hash đổi sau khi lưu, entity nằm trong `HashSet` không tìm lại được. Dùng business key bất biến, hoặc so theo id khi khác `null` với `hashCode` cố định theo class.

## Deep

- **Ghi theo lô**:
  - `saveAll()` chỉ gọi `save()` từng cái. Muốn JDBC batch thật, đặt `hibernate.jdbc.batch_size` (ví dụ 50), `hibernate.order_inserts` và `hibernate.order_updates`, và dùng `SEQUENCE` thay cho `IDENTITY` (bài JPA & Hibernate cơ bản).
  - Với MySQL, thêm `rewriteBatchedStatements=true` vào URL JDBC để driver gộp batch thành một câu nhiều dòng; PostgreSQL có `reWriteBatchedInserts=true` (bài JDBC & cách ứng dụng nói chuyện với DB).
- **Flush mode**:
  - `AUTO` (mặc định): khi nào flush trước query xem bài JPA & Hibernate cơ bản.
  - `COMMIT` chỉ flush lúc commit: query không thấy thay đổi chưa flush của chính transaction, nên "tìm, không có thì tạo" có thể tạo trùng (khi id không phải `IDENTITY`; với `IDENTITY` thì `persist` đã `INSERT` ngay).
  - `MANUAL` (khi `readOnly`) không bao giờ tự flush.
  - Mỗi lần auto flush vẫn phải dirty check toàn bộ persistence context trước khi biết có cần ghi hay không.
- **`@Modifying` chi tiết**:
  - `flushAutomatically = true` flush thay đổi đang chờ trước câu bulk. `clearAutomatically = true` xoá persistence context sau câu bulk: entity đã tải thành **detached**, sửa tiếp không được lưu và không báo lỗi.
  - An toàn nhất là không trộn bulk và entity trong cùng transaction; nếu phải trộn thì `entityManager.refresh(entity)` sau câu bulk.
  - Muốn bulk tăng version của Hibernate thì dùng HQL `update versioned Customer ...`, hoặc tự `set c.version = c.version + 1`.
- **`@DynamicUpdate`**: mặc định `UPDATE` ghi **mọi cột**, nên một thay đổi nhỏ trên entity cũ cũng ghi đè giá trị cũ của cột khác. `@DynamicUpdate` chỉ ghi cột thay đổi, giảm ghi đè nhưng mất cache câu SQL và không thay được `@Version`.
- **Khoá**:
  - `@Version` cho optimistic lock: xung đột ném `ObjectOptimisticLockingFailureException`.
  - `@Lock(LockModeType.PESSIMISTIC_WRITE)` sinh `SELECT ... FOR UPDATE` (bài Optimistic & pessimistic locking).
  - Hint `jakarta.persistence.lock.timeout`: với Hibernate 6 trên PostgreSQL và MySQL chỉ giá trị `0` (`NOWAIT`) có tác dụng, số dương bị bỏ qua không báo. Đặt `lock_timeout` (PostgreSQL, `SET LOCAL`) hoặc `innodb_lock_wait_timeout` (MySQL) cho session. Hibernate 7 trên PostgreSQL áp timeout qua `lock_timeout` của connection.
- **Projection**:
  - Interface projection "đóng" chỉ chọn đúng các cột của getter. Interface "mở" có `@Value("#{...}")` phải tải cả entity.
  - Record DTO qua constructor expression của JPQL là rẻ nhất cho màn hình chỉ đọc.
  - Projection không phải entity managed nên không bị dirty check.
- **Câu derived dễ chậm**:
  - `findByEmailIgnoreCase` sinh `upper(email) = upper(?)`, không dùng được index thường; cần [[expression-index|expression index]] hoặc cột chuẩn hoá sẵn. Trên MySQL, collation mặc định đã không phân biệt hoa thường nên `findByEmail` là đủ; vẫn dùng `IgnoreCase` thì cần functional index (8.0.13+).
  - `existsByEmail` dừng ở dòng đầu tiên. `countByEmail(...) > 0` đếm hết.
  - `findTop10By...OrderBy...` cần index khớp thứ tự sắp xếp.
- **`Stream<T>` từ repository**: phải chạy trong transaction và đóng bằng try-with-resources. Entity đã duyệt vẫn ở trong persistence context, nên cần `clear()` theo lô. Đặt fetch size để driver không tải hết vào bộ nhớ; với MySQL cần `useCursorFetch=true` thì fetch size mới có tác dụng (bài JDBC & cách ứng dụng nói chuyện với DB).
- **Tham số `IN`**: mỗi độ dài danh sách khác nhau là một câu SQL khác trong plan cache của Hibernate và của database. `hibernate.query.in_clause_parameter_padding=true` làm tròn lên lũy thừa của 2 để giảm số biến thể.
- **Entity và Lombok**: `@Data` sinh `equals`, `hashCode`, `toString` từ mọi field, kể cả collection lazy: `toString()` gây `LazyInitializationException` hoặc tải cả cây; quan hệ hai chiều gây `StackOverflowError`. Proxy của Hibernate là lớp con, nên `equals` phải dùng `instanceof` hoặc `Hibernate.getClass()`, không so `getClass()`. Record không làm entity được (field `final`, không có constructor rỗng).
- **[[open-session-in-view|Open Session in View]]**: Boot bật mặc định, persistence context sống tới khi ghi xong response; tắt nó (`spring.jpa.open-in-view=false`) để lỗi lazy lộ ra trong service (bài N+1 Query).
- **Phiên bản**: Boot 4 đi kèm Spring Data JPA 4 với Hibernate 7 và JPA 3.2. Từ Spring Data 2025.1 (Spring Data JPA 4) có AOT repository: khi chạy AOT processing của Boot, query của repository được sinh thành code lúc build, khởi động nhanh hơn và hợp với native image; với JPA chỉ hỗ trợ Hibernate.
