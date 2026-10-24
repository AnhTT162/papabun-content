## Quick

Với [[rolling-deployment|rolling deploy]], **code cũ và code mới chạy cùng lúc trên cùng một schema**, nên mỗi [[schema-migration|migration]] phải tương thích với cả hai. Thay đổi phá vỡ (đổi tên, đổi kiểu, xoá cột) được tách thành nhiều bước theo **[[expand-contract|expand-contract]]**: thêm cái mới, ghi cả hai, [[backfill|backfill]], chuyển đọc, rồi mới xoá cái cũ. Mỗi DDL phải **lấy lock ngắn** (`lock_timeout`, `CONCURRENTLY`, `NOT VALID`, online DDL) và không ghi lại cả bảng.

## Interview

**Flyway và Liquibase** chạy các file migration theo thứ tự phiên bản và ghi lại vào bảng lịch sử (`flyway_schema_history`, `DATABASECHANGELOG`) kèm checksum. Sửa một migration đã chạy thì checksum lệch và lần chạy sau báo lỗi; luôn viết migration mới.

**Chạy ở đâu**: để Spring Boot chạy lúc khởi động thì tiện, nhưng migration dài làm pod khởi động chậm, liveness probe giết pod giữa chừng, và mọi pod tranh nhau lock của công cụ. Hệ thống lớn chạy migration thành một bước riêng trong pipeline (job hoặc init) trước khi rollout.

**Tương thích hai chiều**. Đổi tên `phone` thành `phone_number` theo expand-contract:
1. Thêm cột mới, cho phép null.
2. Deploy code ghi cả hai cột, vẫn đọc cột cũ.
3. Backfill dữ liệu cũ theo lô.
4. Deploy code đọc cột mới.
5. Deploy code thôi ghi cột cũ, bỏ mapping.
6. Xoá cột cũ.

Mỗi bước rollback ứng dụng được.

**DDL nguy hiểm** (PostgreSQL):
- [[table-rewrite|Ghi lại bảng]] dưới `ACCESS EXCLUSIVE`: `ALTER COLUMN TYPE` (phần lớn trường hợp), `ADD COLUMN` với default volatile.
- Khoá chặn ghi suốt thời gian chạy: `CREATE INDEX` không `CONCURRENTLY`.
- Quét cả bảng dưới lock mạnh: thêm `NOT NULL`, `FOREIGN KEY`, `CHECK` mà không qua `NOT VALID` rồi `VALIDATE CONSTRAINT`.

Mọi DDL đều đặt [[lock-timeout|`lock_timeout`]] vài giây kèm retry, để không treo cả bảng vì [[lock-queue|hàng đợi lock]].

**MySQL**: [[online-ddl|online DDL]] có ba thuật toán:
- `INSTANT`: chỉ sửa metadata.
- `INPLACE`: dựng lại trong engine, phần lớn thời gian vẫn cho ghi.
- `COPY`: chép bảng, chặn ghi.

Ghi rõ `ALGORITHM=INSTANT` hoặc `INPLACE, LOCK=NONE` để lệnh báo lỗi thay vì âm thầm chép bảng. Bảng lớn thường dùng gh-ost hoặc pt-online-schema-change.

**Backfill** chạy theo lô vài nghìn dòng theo khoảng primary key, có nghỉ, theo dõi [[replica-lag|replica lag]], chạy lại được giữa chừng. Không bao giờ một câu `UPDATE` cho cả bảng.

## Deep

- **DDL nào an toàn trên PostgreSQL**:
  - `ADD COLUMN` không default, hoặc default không volatile (từ bản 11, kể cả `now()`), chỉ sửa metadata. `gen_random_uuid()` hay `clock_timestamp()` là volatile nên ghi lại bảng.
  - Tăng độ dài `varchar(n)` hoặc đổi sang `text` không ghi lại bảng, nhưng vẫn lấy `ACCESS EXCLUSIVE` trong chốc lát nên vẫn cần `lock_timeout`. Giảm độ dài, `int` sang `bigint`, `timestamp` sang `timestamptz` thì ghi lại bảng và dựng lại mọi index. Riêng `timestamp` sang `timestamptz` được miễn khi múi giờ của session là UTC (bản 12+).
  - `SET NOT NULL` phải quét cả bảng dưới `ACCESS EXCLUSIVE`. Từ bản 12, nếu đã có `CHECK (col IS NOT NULL)` hợp lệ thì bỏ qua lần quét: thêm check `NOT VALID`, `VALIDATE CONSTRAINT` (chỉ giữ `SHARE UPDATE EXCLUSIVE`, không chặn ghi), rồi `SET NOT NULL` và xoá check. Bản 18 cho thêm ràng buộc `NOT NULL` dạng `NOT VALID` trực tiếp.
  - Foreign key: `ADD CONSTRAINT ... FOREIGN KEY ... NOT VALID` chỉ lấy lock ngắn trên cả hai bảng; `VALIDATE CONSTRAINT` sau đó quét bảng mà không chặn ghi.
  - Unique: `CREATE UNIQUE INDEX CONCURRENTLY`, rồi `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE USING INDEX`.
- **`CREATE INDEX CONCURRENTLY`**: không chạy trong transaction, quét bảng hai lần và phải chờ mọi transaction đang mở kết thúc. Lỗi giữa chừng (trùng giá trị khi tạo unique, bị huỷ) để lại một index `INVALID` vẫn làm chậm mọi lần ghi: kiểm tra `pg_index.indisvalid`, `DROP INDEX CONCURRENTLY` rồi tạo lại. `REINDEX CONCURRENTLY` (bản 12+) dựng lại index phình.
- **Flyway và transaction**: trên PostgreSQL mỗi migration chạy trong một transaction. Flyway tự nhận ra các lệnh không chạy được trong transaction (`CREATE/DROP INDEX CONCURRENTLY`, `VACUUM`...) và chạy file đó ngoài transaction, nhưng báo lỗi nếu một file **trộn** lệnh như vậy với lệnh thường, trừ khi bật `mixed=true` (lúc đó cả file mất tính nguyên tử). Cách gọn: mỗi `CONCURRENTLY` một file riêng. Ghi đè thủ công bằng `executeInTransaction=false` trong file cấu hình đi kèm script; Liquibase dùng `runInTransaction="false"`. `SET lock_timeout` trong file chạy ngoài transaction có hiệu lực cho cả session của Flyway sau đó. Trên MySQL, DDL gây [[implicit-commit|implicit commit]], nên một migration có nhiều DDL lỗi giữa chừng sẽ để schema dở dang, và Flyway ghi migration đó là lỗi; phải sửa tay rồi `flyway repair`. Mỗi file chỉ nên có một DDL trên MySQL.
- **Lock của công cụ**: Liquibase ghi lock vào `DATABASECHANGELOGLOCK`; pod bị giết giữa chừng để lại lock và mọi pod sau chờ mãi (`Waiting for changelog lock`) tới khi có người xoá tay. Gỡ bằng `liquibase release-locks`. Flyway dùng advisory lock của PostgreSQL (hoặc `GET_LOCK` của MySQL), tự nhả khi session chết. Flyway Undo (`U__`) chỉ có ở bản trả phí; Liquibase có `rollback` miễn phí.
- **`spring.jpa.hibernate.ddl-auto`**: `update` không bao giờ dùng cho production (không xoá được gì, không đổi kiểu, không có lịch sử). Production đặt `validate` hoặc `none`.
- **Hibernate và cột mới**: entity của code cũ không biết cột mới, nên `INSERT` của nó không ghi cột đó. Cột mới phải cho phép null hoặc có default. Ngược lại, xoá một cột mà code cũ còn map sẽ làm `SELECT` của nó lỗi, nên phải deploy code bỏ mapping **trước**, rồi mới xoá cột.
- **Đổi giá trị enum**: thêm giá trị mới thì deploy code **đọc** được nó trước, code **ghi** nó sau. Code cũ đọc `EnumType.STRING` lạ sẽ ném exception, Jackson cũng vậy nếu không bật `READ_UNKNOWN_ENUM_VALUES_AS_NULL` hoặc `READ_UNKNOWN_ENUM_VALUES_USING_DEFAULT_VALUE` (kèm `@JsonEnumDefaultValue`). `EnumType.ORDINAL` thì chèn hay đổi thứ tự giá trị là đổi nghĩa dữ liệu cũ. Enum của PostgreSQL thêm giá trị bằng `ALTER TYPE ... ADD VALUE`, và giá trị mới chưa dùng được trong chính transaction đó.
- **Backfill đúng cách**:
  - Lô theo khoảng primary key: `UPDATE customers SET phone_number = phone WHERE id >= ? AND id < ? AND phone_number IS NULL`. Lô theo id đã có index, không dùng `OFFSET`.
  - Mỗi lô một transaction ngắn, nghỉ giữa các lô, dừng khi replica lag vượt ngưỡng.
  - Lưu vị trí đã chạy để chạy lại được; điều kiện `IS NULL` làm việc chạy lại không ghi đè dữ liệu mới.
  - PostgreSQL: mỗi dòng được update sinh một phiên bản mới, bảng có thể phình gần gấp đôi; để autovacuum theo kịp hoặc `VACUUM` giữa các đợt. MySQL: mỗi lô là một transaction nhỏ nên replica áp song song được.
- **Đọc và ghi trong lúc chuyển**: giữa bước 2 và bước 5, dữ liệu ghi bởi code mới phải nằm ở cả hai cột. Trigger trong database đồng bộ hai cột chắc hơn ghi kép trong code, vì không bỏ sót đường ghi nào (script tay, service khác). Đổi lại phải nhớ xoá trigger ở bước contract.
- **MySQL online DDL chi tiết**:
  - `INSTANT` cho `ADD COLUMN` ở cuối bảng từ 8.0.12, ở bất kỳ vị trí nào và `DROP COLUMN` từ 8.0.29. Từ 8.0.29, mỗi lần `ADD`/`DROP COLUMN` instant tạo một row version, tối đa 64 cho mỗi bảng (xem `INFORMATION_SCHEMA.INNODB_TABLES.TOTAL_ROW_VERSIONS`); chạm giới hạn thì `ALTER` không ghi `ALGORITHM` sẽ âm thầm dựng lại bảng.
  - `INPLACE` vẫn cần metadata lock độc quyền lúc bắt đầu và lúc kết thúc, nên vẫn kẹt sau transaction dài (bài Lock & deadlock). Đặt `lock_wait_timeout` ngắn.
  - Trên replica, DDL chỉ bắt đầu sau khi source chạy xong, và áp một luồng: `ALTER` 2 giờ trên source thành lag 2 giờ trên replica.
  - Thêm cột `AUTO_INCREMENT` dựng lại bảng và không cho ghi đồng thời.
  - gh-ost đọc binlog (cần `binlog_format = ROW`) để áp thay đổi lên bảng bóng, không dùng trigger, điều tốc được theo replica lag, và cho chọn lúc cắt chuyển, nhưng không hỗ trợ bảng có foreign key. pt-online-schema-change dùng trigger, thêm tải ghi và cần MDL khi tạo trigger, nhưng xử lý được foreign key (`--alter-foreign-keys-method`).
- **Đổi tên bảng hoặc tách bảng** cũng theo expand-contract. PostgreSQL có thể đổi tên bảng rồi tạo view tên cũ trỏ vào bảng mới để code cũ còn chạy trong lúc chuyển.
- **Kiểm thử migration**: chạy trên bản sao dữ liệu thật về kích thước (không chỉ database trống trong CI), đo thời gian và lock thật sự lấy. Công cụ lint như `squawk` (PostgreSQL) phát hiện DDL nguy hiểm trong pull request.
