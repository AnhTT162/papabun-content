## Quick

Câu `SELECT` được xử lý theo [[logical-query-order|thứ tự logic]] `FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → LIMIT`, không theo thứ tự viết. `NULL` nghĩa là "không biết": mọi phép so sánh với `NULL` ra `UNKNOWN`, nên **`= NULL` không bao giờ đúng, và `NOT IN` gặp một `NULL` trả về rỗng**.

## Interview

**Thứ tự logic** giải thích nhiều hành vi tưởng là lạ:
- `WHERE` lọc từng dòng **trước** khi gom nhóm, `HAVING` lọc **nhóm** sau khi gom. Điều kiện không cần hàm gộp nên đặt ở `WHERE` để bớt dòng phải gom.
- Alias đặt trong `SELECT` không dùng được ở `WHERE` (lúc đó `SELECT` chưa chạy), nhưng dùng được ở `ORDER BY`.
- Khi có `GROUP BY`, mỗi cột trong `SELECT` phải nằm trong `GROUP BY` hoặc nằm trong [[aggregate-function|hàm gộp]]. Cả PostgreSQL (9.1+) và MySQL (5.7.5+) cho phép thêm cột phụ thuộc hàm vào primary key đã group. MySQL từ 5.7.5 bật `ONLY_FULL_GROUP_BY` mặc định; tắt chế độ này thì MySQL trả một giá trị bất kỳ trong nhóm (muốn có chủ đích thì viết `ANY_VALUE(col)`).

**JOIN**:
- `INNER JOIN` chỉ giữ cặp dòng khớp.
- `LEFT JOIN` ([[outer-join|outer join]]) giữ mọi dòng bên trái, phần bên phải thiếu thì điền `NULL`.
- `FULL JOIN` giữ cả hai bên; `CROSS JOIN` ghép mọi cặp.

Bẫy kinh điển: `LEFT JOIN` rồi đặt điều kiện trên bảng bên phải ở `WHERE`. Các dòng được điền `NULL` bị loại, nên kết quả thành `INNER JOIN`. Điều kiện đó phải nằm trong `ON`.

**NULL và [[three-valued-logic|logic ba giá trị]]**:
- `x = NULL`, `x <> NULL` đều ra `UNKNOWN`; `WHERE` chỉ giữ dòng `TRUE`. Dùng `IS NULL`, `IS DISTINCT FROM` (PostgreSQL) hoặc `<=>` (MySQL).
- `x NOT IN (1, 2, NULL)` không bao giờ ra `TRUE`. Lọc "không nằm trong" bằng subquery thì dùng `NOT EXISTS`.
- Hàm gộp bỏ qua `NULL`: `COUNT(*)` đếm mọi dòng, `COUNT(col)` chỉ đếm dòng có giá trị, `AVG(col)` chia cho số dòng có giá trị. `SUM` trên toàn `NULL` ra `NULL`, không ra 0; dùng `COALESCE(SUM(x), 0)`.

**Gộp tập**: `UNION` loại trùng (phải sort hoặc hash), `UNION ALL` giữ nguyên và nhanh hơn. Không cần loại trùng thì luôn dùng `UNION ALL`.

## Deep

- **Thứ tự logic không phải thứ tự thật**: planner được phép đổi thứ tự thực thi (đẩy điều kiện xuống sớm, đổi thứ tự join) miễn là kết quả giống hệt. Thứ tự logic chỉ quyết định cái gì nhìn thấy được ở đâu.
- **`COUNT(1)` và `COUNT(*)` như nhau** trong PostgreSQL và MySQL. Chuyện `COUNT(1)` nhanh hơn chỉ là tin đồn.
- **Sắp xếp `NULL`**: PostgreSQL đặt `NULL` cuối khi `ASC` và đầu khi `DESC`; MySQL làm ngược lại. PostgreSQL có `NULLS FIRST/LAST`; MySQL phải viết `ORDER BY col IS NULL, col`.
- **`NULL` trong `UNIQUE`**: hai dòng `NULL` không bị coi là trùng (xem bài Index & Execution Plan).
- **[[correlated-subquery|Subquery tương quan]]** (tham chiếu cột của query ngoài) về logic chạy lại cho từng dòng. Planner hiện đại thường biến `EXISTS`/`IN` thành semi-join, nhưng subquery tương quan đặt trong `SELECT` vẫn có thể chạy N lần.
- **`WHERE` trên kết quả của hàm cửa sổ**: window function tính ở bước `SELECT`, nên muốn lọc theo nó phải bọc trong subquery hoặc CTE (PostgreSQL chưa có `QUALIFY`).
- **`BETWEEN` với thời gian** bao gồm cả hai đầu: `BETWEEN '2026-10-01' AND '2026-10-31'` bỏ sót mọi thứ sau 00:00 ngày 31. Dùng khoảng nửa mở `>= ... AND < ...`.
- **Chia số nguyên**: `SELECT 7 / 2` ra `3` trong PostgreSQL (chia nguyên) nhưng `3.5000` trong MySQL. Tính tỉ lệ thì ép kiểu rõ ràng.
- **Chuẩn SQL và phương ngữ**: `LIMIT/OFFSET` (PostgreSQL, MySQL) và `FETCH FIRST n ROWS ONLY` (chuẩn); `||` là nối chuỗi trong PostgreSQL nhưng là `OR` trong MySQL mặc định (đã deprecated từ 8.0.17; bật `PIPES_AS_CONCAT` thì thành nối chuỗi).
