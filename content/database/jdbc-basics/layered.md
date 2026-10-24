## Quick

[[jdbc|JDBC]] là lớp mà mọi thư viện Java dùng để nói chuyện với database: JPA/Hibernate, Spring `JdbcTemplate`/`JdbcClient`, MyBatis đều chạy trên nó. Ba điều phải đúng ở tầng này: **luôn dùng [[prepared-statement|PreparedStatement]] với tham số** (chống [[sql-injection|SQL injection]]), **luôn đóng resource** (không thì rò connection), và **hiểu driver thật sự đọc/ghi dữ liệu thế nào** (fetch size, batch).

## Interview

Luồng một query:
1. Lấy `Connection` từ [[datasource|DataSource]]. Production luôn dùng [[connection-pool|connection pool]] (HikariCP), vì mở connection mới tốn một vòng bắt tay TCP, [[tls-handshake|TLS]] và xác thực.
2. Tạo `PreparedStatement` với dấu `?` và bind tham số.
3. Driver gửi query theo giao thức của database và nhận `ResultSet` (đọc hết một lần hay theo lô tuỳ fetch size, xem dưới).
4. Đóng `ResultSet`, `Statement`, `Connection` (trả về pool) bằng [[try-with-resources]].

**PreparedStatement chống SQL injection** vì giá trị tham số được gửi tách khỏi câu SQL (hoặc được driver escape đúng cách), nên không bao giờ thành cú pháp SQL. Nhưng tham số chỉ thay được **giá trị**, không thay được tên cột, tên bảng hay `ASC/DESC`. Phần động đó phải chọn từ một danh sách giá trị cho phép cố định (whitelist).

**[[fetch-size|Fetch size]]** quyết định đọc kết quả lớn thế nào:
- **PostgreSQL**: driver mặc định đọc **toàn bộ** kết quả vào bộ nhớ. Chỉ đọc theo lô (dùng cursor phía server) khi tắt [[autocommit]], đặt `setFetchSize(n)` và query là một câu lệnh đơn. Có thể đặt mặc định bằng `defaultRowFetchSize` hoặc `hibernate.jdbc.fetch_size`.
- **MySQL Connector/J**: mặc định cũng đọc hết. Muốn đọc dần thì dùng `useCursorFetch=true` kèm fetch size, hoặc streaming (đọc từng dòng trên connection đang mở) với `Integer.MIN_VALUE`.

Đọc 10 triệu dòng mà quên điều này là OutOfMemoryError.

**[[jdbc-batching|Batch]]**: `addBatch()`/`executeBatch()` gom nhiều lệnh ghi thành ít lượt đi về. Driver MySQL chỉ gộp thành `INSERT` nhiều dòng khi bật `rewriteBatchedStatements=true`; PostgreSQL có `reWriteBatchedInserts=true`. Hibernate cần `hibernate.jdbc.batch_size`, và **không batch được insert khi id sinh bằng `IDENTITY`**, vì phải chờ database trả id cho từng dòng.

**Autocommit** mặc định bật: mỗi lệnh tự commit. `@Transactional` của Spring tắt nó trên connection trong suốt transaction.

## Deep

- **Rò connection** ([[connection-leak|connection leak]]): quên `close()` thì connection không về pool. Sau vài phút pool cạn, mọi request chờ rồi lỗi `HikariPool-1 - Connection is not available, request timed out after 30000ms`. Bật `leakDetectionThreshold` để Hikari log stack trace của nơi mượn mà không trả.
- **Timeout**: `connectTimeout` (mở kết nối), `socketTimeout` (chờ dữ liệu trên socket; với nhiều driver mặc định là 0, tức chờ vô hạn), và `Statement.setQueryTimeout` (huỷ query chạy quá lâu). Thiếu `socketTimeout`, một lần database treo hay mạng rơi gói tin có thể giữ thread tới hàng chục phút.
- **Server-side prepare**: PostgreSQL JDBC dùng prepared statement phía server sau 5 lần chạy cùng một câu (`prepareThreshold=5`), nhờ đó tái sử dụng plan. MySQL Connector/J mặc định escape tham số phía client (`useServerPrepStmts=false`), vẫn an toàn trước SQL injection.
- **`LIKE` với tham số**: bind `"%" + keyword + "%"` là an toàn, nhưng người dùng vẫn gõ được `%` và `_` để khớp mọi thứ. Escape hai ký tự này nếu ngữ nghĩa tìm kiếm cần chính xác.
- **Kiểu dữ liệu**: `getInt` trả 0 cho `NULL`, phải gọi `wasNull()`. Dùng `getObject(col, Integer.class)` để nhận `null`. Thời gian nên đọc bằng `getObject(col, OffsetDateTime.class)` cho `timestamptz` và `LocalDateTime.class` cho `timestamp`, thay vì `java.sql.Timestamp` vốn dễ lệch múi giờ.
- **Spring `JdbcClient`** (Spring 6.1+) là API gọn hơn `JdbcTemplate` cho SQL viết tay, vẫn dùng tham số an toàn. Hợp với query báo cáo phức tạp mà ORM làm khó.
- **[[orm|ORM]] không thay thế hiểu biết về JDBC**: lỗi [[n-plus-one|N+1]], batch không chạy, OOM khi đọc nhiều dòng đều xảy ra ở tầng JDBC bên dưới Hibernate. Bật log SQL và metric của pool để nhìn thấy nó.
