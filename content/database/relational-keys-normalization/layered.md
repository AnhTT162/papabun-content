## Quick

[[primary-key|Primary key]] định danh duy nhất mỗi dòng; [[foreign-key|foreign key]] đảm bảo tham chiếu tới dòng có thật; `UNIQUE`, `NOT NULL`, `CHECK` là các [[constraint|ràng buộc]] khác. **Quy tắc dữ liệu quan trọng phải nằm trong database, không chỉ trong code**, vì code kiểm tra rồi mới ghi luôn có khe hở khi chạy đồng thời. [[normalization|Chuẩn hoá]] (1NF–3NF) bảo đảm mỗi sự thật chỉ lưu ở một nơi.

## Interview

**Các loại key**
- **Primary key**: duy nhất, không `NULL`, mỗi bảng một cái. Trong InnoDB, primary key còn là thứ tự lưu dữ liệu ([[clustered-index|clustered index]]).
- **Unique key** (alternate key): các cột khác cũng phải duy nhất, ví dụ `email`.
- **Foreign key**: giá trị phải tồn tại ở bảng được tham chiếu. Hành vi khi xoá dòng cha:
  - `RESTRICT`/`NO ACTION`: chặn xoá.
  - `CASCADE`: xoá theo.
  - `SET NULL`: đặt khoá ngoại về `NULL`.
- **Composite key**: key gồm nhiều cột, ví dụ `(order_id, line_no)`.

**[[surrogate-key|Surrogate key]] hay natural key**: natural key là giá trị có nghĩa nghiệp vụ (email, mã số thuế); surrogate key là id vô nghĩa (`bigint` tự tăng, UUID). Natural key có thể đổi (email đổi, mã bị nhập sai) và kéo theo sửa mọi bảng tham chiếu. Thực tế hay dùng surrogate key làm primary key, kèm `UNIQUE` trên natural key.

**Chuẩn hoá** loại bỏ các bất thường khi thêm, sửa, xoá:
- **1NF**: mỗi ô một giá trị nguyên tử, không có nhóm lặp (không lưu `"0901..., 0902..."` trong một cột).
- **2NF**: với key nhiều cột, mọi cột khác phụ thuộc vào **toàn bộ** key, không phải một phần.
- **3NF**: không có phụ thuộc bắc cầu, tức cột không phải key không phụ thuộc vào một cột không phải key khác (bảng đơn hàng không lưu tên khách, vì tên phụ thuộc `customer_id` chứ không phụ thuộc đơn).

Phi chuẩn hoá có chủ đích (lưu sẵn tổng tiền, chép tên sản phẩm vào dòng hàng tại thời điểm mua) là hợp lý khi cần đọc nhanh hoặc cần lưu **giá trị tại thời điểm đó**. Nhưng đó phải là quyết định có lý do, không phải thiết kế ngẫu nhiên.

**Vì sao ràng buộc phải ở database**: code kiểm tra `existsByEmail` rồi mới `INSERT`. Hai request đồng thời đều thấy "chưa có" và cùng chèn. Chỉ `UNIQUE` constraint mới chặn được triệt để; ứng dụng bắt lỗi trùng khoá và trả thông báo thân thiện.

## Deep

- **`CHECK` trong MySQL chỉ có hiệu lực từ 8.0.16**. Các bản trước parse cú pháp rồi âm thầm bỏ qua, nên schema chuyển từ MySQL cũ có thể đang dựa vào một ràng buộc chưa bao giờ chạy, và nâng cấp xong nó vẫn không tồn tại cho tới khi `ADD CONSTRAINT` lại.
- **Foreign key cần index ở bảng con**: InnoDB tự tạo, PostgreSQL thì không (xem bài Index & Execution Plan). Thiếu index thì mỗi lần xoá dòng cha phải quét cả bảng con và khoá lâu.
- **Ràng buộc deferrable** (PostgreSQL): `DEFERRABLE INITIALLY DEFERRED` để kiểm tra lúc `COMMIT`, hữu ích khi hai bảng tham chiếu vòng hoặc khi đổi thứ tự trong một danh sách có unique.
- **Thêm ràng buộc vào bảng lớn** (PostgreSQL): với `CHECK` và foreign key, `ADD CONSTRAINT ... NOT VALID` rồi `VALIDATE CONSTRAINT` để không khoá ghi lâu. Với `UNIQUE`, tạo `CREATE UNIQUE INDEX CONCURRENTLY` trước rồi `ADD CONSTRAINT ... UNIQUE USING INDEX`. Kiểm tra dữ liệu cũ có vi phạm trước khi bật.
- **Unique không phân biệt hoa thường**: PostgreSQL dùng `CREATE UNIQUE INDEX ... ON users (lower(email))` ([[expression-index|expression index]]; không viết được dạng constraint `UNIQUE (lower(email))`), hoặc kiểu `citext`. MySQL mặc định `utf8mb4_0900_ai_ci` đã không phân biệt hoa thường, **và cũng không phân biệt dấu** (`ai` = accent-insensitive), nên `an@` và `ân@` bị coi là trùng.
- **Xoá mềm và unique**: `deleted_at` khiến `UNIQUE (email)` chặn người dùng đăng ký lại; dùng partial unique index `WHERE deleted_at IS NULL` (PostgreSQL).
- **`ON DELETE CASCADE` nguy hiểm ở bảng lớn**: một lệnh xoá có thể kéo theo hàng triệu dòng con trong một transaction. Với dữ liệu quan trọng, ưu tiên `RESTRICT` và xoá có chủ đích.
- **UUID hay `bigint` làm surrogate key**: UUID v4 ngẫu nhiên làm dòng mới chèn vào giữa index (tách page, đặc biệt nặng với clustered index của InnoDB); UUID v7 có thứ tự theo thời gian nên tránh được, mà vẫn sinh được ở ứng dụng.
- **BCNF và các dạng cao hơn** hiếm khi cần trong hệ thống nghiệp vụ; nắm chắc 3NF và biết khi nào phi chuẩn hoá là đủ cho phỏng vấn.
