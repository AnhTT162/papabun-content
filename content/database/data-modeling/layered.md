## Quick

Mô hình tốt bắt đầu từ **các ràng buộc nghiệp vụ và các cách dữ liệu được đọc**, không từ class Java. Bốn quyết định hay bị làm theo thói quen: **phi chuẩn hoá** (phải có người chịu trách nhiệm giữ đồng bộ), **kiểu id** ([[uuid-v7|UUID v7]] hoặc `bigint`, tránh UUID v4 làm khoá chính), **[[soft-delete|xoá mềm]]** (tiện nhưng có giá ở mọi query), và **cột JSON** (cho phần thật sự linh hoạt, không phải để né thiết kế schema).

## Interview

**Phi chuẩn hoá có chủ đích** có hai loại khác nhau:
- **Chụp lại giá trị tại thời điểm** (tên và giá sản phẩm trong dòng hàng, địa chỉ giao hàng của đơn): đây không phải bản sao, mà là một sự thật khác, và **không được** đồng bộ theo bảng gốc.
- **Lưu sẵn giá trị suy ra** (tổng tiền đơn, số bình luận của bài viết): phải quyết định ai cập nhật nó (cùng transaction, trigger, hay job bất đồng bộ), chấp nhận lệch bao lâu, và có job đối soát.

**Kiểu id**:
- `bigint` tự tăng: nhỏ, có thứ tự, index gọn. Nhược: lộ số lượng nếu đưa ra URL, phải hỏi database mới có id. Với Hibernate, dùng `SEQUENCE` thay vì `IDENTITY` để còn batch insert được.
- UUID v4: sinh ở đâu cũng được, nhưng ngẫu nhiên nên dòng mới chèn rải rác khắp index (nặng nhất với [[clustered-index|clustered index]] của InnoDB).
- **UUID v7** (RFC 9562): 48 bit đầu là thời gian, nên gần như tăng dần như `bigint` mà vẫn sinh được ở ứng dụng. PostgreSQL lưu kiểu `uuid` 16 byte; MySQL lưu `BINARY(16)`, đừng lưu `CHAR(36)`.

**Xoá mềm** (`deleted_at`) giữ lại dòng để khôi phục hoặc tra cứu. Cái giá: mọi query phải nhớ lọc, unique phải thành [[partial-index|partial index]] `WHERE deleted_at IS NULL`, foreign key vẫn trỏ tới dòng "đã xoá", bảng phình mãi, và xung đột với yêu cầu xoá dữ liệu cá nhân.

Thường tốt hơn là trạng thái nghiệp vụ (`DISCONTINUED`, `CLOSED`), hoặc chuyển dòng sang bảng lưu trữ.

**Audit và lịch sử** ([[audit-trail|audit trail]]): cột `created_at/by`, `updated_at/by` cho biết ai sửa gần nhất. Muốn biết **toàn bộ lịch sử** thì cần bảng lịch sử: ghi bằng trigger, Hibernate Envers, hoặc [[cdc|CDC]]. Một số database có [[temporal-table|temporal table]] sẵn.

**Cột JSON**: [[jsonb]] của PostgreSQL (dạng nhị phân, có GIN index) hoặc `JSON` của MySQL. Hợp với thuộc tính khác nhau theo loại sản phẩm, payload từ hệ ngoài, cấu hình. Không hợp với dữ liệu cần ràng buộc, foreign key, hay được lọc và join thường xuyên.

## Deep

- **UUID v7 trong PostgreSQL**: từ bản 18 có hàm `uuidv7()`; bản cũ sinh ở ứng dụng (ví dụ thư viện `java-uuid-generator`, hoặc `UuidCreator`). Hibernate 7.0+ (Spring Boot 4) có `@UuidGenerator(style = VERSION_7)` (đang ở trạng thái incubating). Hibernate 6.x chỉ có `RANDOM` và `TIME` (UUID kiểu cũ giống v1, không sắp xếp tốt theo byte), nên phải sinh v7 ở ứng dụng hoặc tự viết generator. UUID v7 còn khoảng 62–74 bit ngẫu nhiên tuỳ cách cài đặt (RFC cho phép dùng một phần làm bộ đếm), nên đừng dùng nó làm token bí mật.
- **UUID trong MySQL**: lưu bằng `UUID_TO_BIN(x)` không kèm cờ swap; `UUID_TO_BIN(x, 1)` chỉ dành cho v1 và sẽ xáo trộn phần thời gian của v7. Hàm `UUID()` của MySQL sinh v1, MySQL không có hàm sinh v7. UUID v7 lộ thời điểm tạo; nếu đó là thông tin nhạy cảm thì đừng đưa nó ra ngoài.
- **Id nội bộ và id công khai**: giữ `bigint` làm khoá chính và thêm cột `public_id` (UUID hoặc mã ngẫu nhiên ngắn) có unique index cho URL và API. Join nội bộ gọn, còn bên ngoài không đoán được số lượng hay id kế tiếp.
- **Sequence của Hibernate**: `allocationSize` (mặc định 50) phải khớp với `INCREMENT BY` của sequence. Hibernate 5.4+ kiểm tra lúc khởi động và mặc định báo lỗi (`hibernate.id.sequence.increment_size_mismatch_strategy = EXCEPTION`); id trùng chỉ xảy ra khi tắt kiểm tra này hoặc sequence bị sửa khi app đang chạy. Hibernate 6 dùng pooled optimizer và đổi tên sequence mặc định thành `<entity>_SEQ` thay cho `hibernate_sequence`, một bẫy khi nâng từ bản 5. MySQL không có sequence: `SEQUENCE` bị giả lập bằng bảng, còn `IDENTITY` tắt batch insert, nên lời khuyên "dùng `SEQUENCE` để batch" chỉ đúng với PostgreSQL và Oracle.
- **Xoá mềm trong Hibernate** có hai cách thay thế cho nhau. Cách thứ nhất: `@SQLDelete(sql = "UPDATE product SET deleted_at = now() WHERE id = ?")` để `remove()` thành `UPDATE`, cộng `@SQLRestriction("deleted_at IS NULL")` (6.3+, thay `@Where`) để tự lọc khi đọc. Cách thứ hai: `@SoftDelete` (6.4+) lo cả ghi lẫn lọc, nhưng ở Hibernate 6 nó dùng cột boolean (mặc định tên `deleted`); kiểu cột thời gian `strategy = SoftDeleteType.TIMESTAMP` chỉ có từ Hibernate 7.0. Native query và báo cáo SQL viết tay vẫn phải tự lọc; một view `active_products` giúp không ai quên.
- **Bảng lưu trữ thay xoá mềm**: `WITH moved AS (DELETE FROM orders WHERE ... RETURNING *) INSERT INTO orders_archive SELECT * FROM moved;` di chuyển nguyên tử trong một câu lệnh của PostgreSQL. Bảng chính nhỏ lại, index không phải gánh dòng chết.
- **Lịch sử giá trị theo khoảng thời gian**: bảng `product_price(product_id, price, valid_during tstzrange)` với [[exclusion-constraint|exclusion constraint]] `EXCLUDE USING gist (product_id WITH =, valid_during WITH &&)` (cần extension `btree_gist`) để database tự chặn hai khoảng giá chồng nhau. Tra giá tại thời điểm `t`: `WHERE valid_during @> t`.
- **PostgreSQL 18** có ràng buộc theo khoảng thời gian: `PRIMARY KEY (product_id, valid_during WITHOUT OVERLAPS)` và `FOREIGN KEY (..., PERIOD valid_during)`, thay được `EXCLUDE` + `btree_gist`. Bản cũ hơn dùng exclusion constraint.
- **Temporal table chuẩn SQL:2011** (system-versioned): MariaDB, SQL Server, Db2 có sẵn; Oracle có Flashback. PostgreSQL và MySQL chưa có: dùng bảng lịch sử ghi bằng trigger, hoặc CDC sang kho lưu trữ.
- **Spring Data auditing**: `@EnableJpaAuditing`, `@CreatedDate`, `@LastModifiedBy` với `AuditingEntityListener`; chỉ ghi được khi thay đổi đi qua JPA. Thay đổi bằng SQL tay hay migration không có dấu vết: audit bắt buộc phải nằm ở database (trigger) hoặc CDC.
- **`jsonb` và `json`**: `json` lưu nguyên văn (giữ khoảng trắng, thứ tự khoá, khoá trùng); `jsonb` lưu nhị phân, bỏ khoá trùng, nhanh khi truy vấn. [[gin-index|GIN]] với `jsonb_path_ops` nhỏ và nhanh cho `@>` nhưng không hỗ trợ `?` (kiểm tra có khoá). Thuộc tính được lọc nhiều nên tách thành cột thường hoặc [[generated-column|generated column]] có B-tree index: planner không có thống kê bên trong `jsonb` nên hay ước lượng sai.
- **Cập nhật `jsonb` ghi lại cả giá trị**: đổi một khoá trong document 50KB là ghi lại 50KB (cộng TOAST và WAL). Document lớn bị sửa thường xuyên là dấu hiệu nên tách thành bảng. MySQL 8.0 cập nhật tại chỗ được với `JSON_SET`/`JSON_REPLACE` trong một số điều kiện (partial update).
- **JSON trong MySQL**: không index trực tiếp được; dùng generated column có index, functional index (8.0.13+, thực chất là generated column ẩn), hoặc multi-valued index (8.0.17+) cho mảng: `INDEX ((CAST(tags->'$' AS CHAR(32) ARRAY)))`.
- **JSON trong Hibernate 6**: `@JdbcTypeCode(SqlTypes.JSON)` ánh xạ một field (record, `Map`) sang cột JSON mà không cần thư viện mapping riêng; Hibernate dùng Jackson hoặc JSON-B có sẵn trên classpath (thiếu cả hai thì lỗi lúc chạy).
- **Thời gian**: PostgreSQL dùng `timestamptz` (lưu thời điểm tuyệt đối, hiển thị theo `TimeZone` của session); `timestamp` không có múi giờ gây lệch khi server và ứng dụng khác múi giờ. MySQL `TIMESTAMP` lưu UTC nhưng chỉ tới năm 2038; `DATETIME` không có múi giờ, nên quy ước luôn lưu UTC. Java: `Instant` hoặc `OffsetDateTime`. Ngày sinh hay ngày hết hạn hợp đồng là `date`, không phải thời điểm.
- **Enum**: kiểu `ENUM` của PostgreSQL thêm giá trị được (`ALTER TYPE ... ADD VALUE`) nhưng không xoá hay đổi thứ tự dễ dàng. `ENUM` của MySQL sắp xếp theo vị trí khai báo, không theo chữ; thêm giá trị vào cuối danh sách là thay đổi metadata tức thì, còn chèn giữa, xoá hay đổi thứ tự thì copy cả bảng. PostgreSQL: `ADD VALUE` chạy trong transaction được từ bản 12 nhưng giá trị mới chưa dùng được trước khi commit, bẫy với migration chạy mọi thứ trong một transaction. Thường linh hoạt hơn: `varchar` + `CHECK`, hoặc bảng tra cứu có foreign key. Trong JPA luôn dùng `@Enumerated(EnumType.STRING)`: `ORDINAL` (mặc định) hỏng dữ liệu khi ai đó chèn hằng mới vào giữa enum.
- **Kế thừa trong JPA**: `SINGLE_TABLE` (một bảng, nhiều cột `NULL`, nhanh nhất), `JOINED` (bảng con join với bảng cha, chuẩn hoá nhưng nhiều join), `TABLE_PER_CLASS` (query đa hình thành `UNION`, hiếm khi đáng dùng). Nhiều khi cột JSON cho phần khác nhau gọn hơn cả ba.
- **Multi-tenant**: nếu chung bảng, `tenant_id` nên là cột đầu của mọi index và nằm trong mọi unique constraint (`UNIQUE (tenant_id, email)`); xem bài Multi-tenancy.
