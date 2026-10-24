## Quick

[[isolation-level|Isolation level]] quy định các [[transaction]] chạy đồng thời thấy dữ liệu của nhau tới đâu. Level càng cao càng ít lỗi đồng thời nhưng càng nhiều chờ hoặc lỗi phải retry. **Mặc định của PostgreSQL (READ COMMITTED) và MySQL (REPEATABLE READ) đều không chặn [[lost-update|lost update]]** khi code đọc giá trị, tính ở ứng dụng rồi ghi đè.

## Interview

Transaction đảm bảo [[acid|ACID]]. Isolation là chữ I: transaction chạy đồng thời mà kết quả như thể chạy lần lượt. Đảm bảo tuyệt đối thì rất đắt, nên chuẩn SQL định nghĩa 4 level theo các hiện tượng được phép xảy ra:

- **READ UNCOMMITTED**: cho phép [[dirty-read|dirty read]] (đọc dữ liệu chưa commit).
- **READ COMMITTED**: chỉ đọc dữ liệu đã commit, nhưng đọc lại một dòng có thể ra giá trị khác ([[non-repeatable-read|non-repeatable read]]).
- **REPEATABLE READ**: đọc lại cùng dòng luôn ra cùng giá trị, nhưng chuẩn vẫn cho phép [[phantom-read|phantom read]] (query lại thấy thêm dòng mới).
- **SERIALIZABLE**: kết quả tương đương chạy lần lượt.

Database hiện đại dùng [[mvcc|MVCC]]: mỗi dòng có nhiều phiên bản, người đọc thấy một [[snapshot-isolation|snapshot]] nên không chặn người ghi. Cài đặt thực tế khác chuẩn:
- **PostgreSQL** mặc định READ COMMITTED; REPEATABLE READ là snapshot isolation và không có phantom; SERIALIZABLE dùng [[ssi|SSI]].
- **MySQL InnoDB** mặc định REPEATABLE READ. `SELECT` thường là [[consistent-read|consistent read]] (đọc snapshot). `SELECT ... FOR UPDATE` và `UPDATE` là locking read, đọc bản mới nhất.

Lỗi đáng lo nhất trong code nghiệp vụ là **lost update**: hai transaction cùng đọc số dư 100, mỗi bên tính ở ứng dụng rồi ghi đè, một lần trừ biến mất. Bốn cách sửa:
1. **Cập nhật nguyên tử**: `UPDATE account SET balance = balance - 30 WHERE id = 1 AND balance >= 30` (ở READ COMMITTED không cần retry).
2. **[[pessimistic-locking|Khoá bi quan]]**: `SELECT ... FOR UPDATE` trước khi đọc, transaction kia phải chờ.
3. **[[optimistic-locking|Khoá lạc quan]]**: cột `version` (JPA `@Version`), ghi kèm `WHERE version = ?`; không dòng nào bị sửa thì retry.
4. **SERIALIZABLE**: PostgreSQL phát hiện xung đột và huỷ một transaction với [[serialization-failure|serialization failure]] (MySQL dùng lock nên thường thành [[deadlock]]); ứng dụng phải retry cả transaction.

Chỉ SERIALIZABLE (hoặc khoá tường minh các dòng điều kiện bằng `FOR UPDATE`) mới chặn được [[write-skew|write skew]]: hai transaction cùng đọc một điều kiện rồi sửa hai dòng khác nhau, làm điều kiện bị vi phạm.

## Deep

- **PostgreSQL READ UNCOMMITTED** chạy như READ COMMITTED: PostgreSQL không bao giờ cho dirty read.
- **PostgreSQL REPEATABLE READ phát hiện lost update**: nếu dòng đã bị transaction khác sửa sau khi snapshot được tạo, `UPDATE` báo `could not serialize access due to concurrent update` (SQLSTATE `40001`). MySQL REPEATABLE READ thì không phát hiện, giá trị bị ghi đè âm thầm.
- **Snapshot được tạo khi nào**: PostgreSQL REPEATABLE READ lấy snapshot ở câu lệnh đầu tiên của transaction, không phải ở `BEGIN`. InnoDB lấy snapshot ở lần `SELECT` thường đầu tiên; `UPDATE` hay `FOR UPDATE` chạy trước đó không tạo snapshot. `START TRANSACTION WITH CONSISTENT SNAPSHOT` tạo snapshot ngay lúc bắt đầu.
- **Locking read của InnoDB** khi quét theo khoảng hoặc theo index không unique sẽ khoá cả khoảng giữa các bản ghi ([[next-key-lock|next-key lock]]) để chặn insert gây phantom. Tìm đúng một dòng bằng unique index thì chỉ khoá dòng đó.
- **InnoDB trộn hai kiểu đọc**: trong cùng transaction REPEATABLE READ, consistent read (`SELECT` thường) có thể không thấy một dòng, nhưng `UPDATE ... WHERE` vẫn sửa dòng đó (vì nó đọc bản mới nhất), sau đó `SELECT` lại thấy dòng đó.
- **[[retry-backoff|Retry]] đúng cách**: chỉ retry lỗi tạm thời (serialization failure `40001`, deadlock `40P01` của PostgreSQL, `1213` của MySQL), retry **cả transaction** với số lần giới hạn và backoff. Trong Spring, các lỗi này thường là `ConcurrencyFailureException`/`TransientDataAccessException`, và vòng retry phải nằm **ngoài** method `@Transactional`. MySQL `1205` (hết thời gian chờ lock) mặc định chỉ rollback câu lệnh, không rollback cả transaction.
- **Spring `@Transactional`** mặc định dùng isolation của database (`Isolation.DEFAULT`). Đổi level chỉ có tác dụng khi transaction thật sự bắt đầu ở method đó.
- **Transaction dài rất đắt**: giữ lock làm transaction khác chờ (MySQL chờ tối đa `innodb_lock_wait_timeout`, mặc định 50 giây), và giữ snapshot cũ làm PostgreSQL không dọn được phiên bản cũ (bảng phình to). Đừng gọi API bên ngoài hay chờ người dùng khi đang mở transaction.
- **`SELECT ... FOR UPDATE SKIP LOCKED`** giúp nhiều worker cùng lấy job từ một bảng làm hàng đợi mà không chờ nhau. `NOWAIT` báo lỗi ngay thay vì chờ lock.
- **Khoá lạc quan hợp khi xung đột hiếm** (sửa hồ sơ, giỏ hàng). Khi xung đột thường xuyên (một dòng "nóng" như tồn kho của sản phẩm đang flash sale), retry liên tục còn tệ hơn chờ lock: dùng cập nhật nguyên tử hoặc khoá bi quan.
