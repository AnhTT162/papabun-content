## Quick

`String` là [[immutable]]: mọi method "sửa" chuỗi đều trả về object mới. Các literal giống nhau dùng chung một object trong [[string-pool|String Pool]], nên `==` lúc thì ra `true`, lúc ra `false`: **so sánh nội dung chuỗi luôn dùng `equals`**.

## Interview

`String` là class `final`. Dữ liệu nằm trong mảng private `value` và không bao giờ bị sửa. Từ Java 9, nhờ [[compact-strings|Compact Strings]], mảng này là `byte[]` đi kèm field `coder`. Chuỗi chỉ có ký tự Latin-1 tốn 1 byte cho mỗi ký tự. Chỉ cần một ký tự nằm ngoài Latin-1 (ví dụ `đ`, `ă`, `ơ`, `ư`, `ạ`) là cả chuỗi chuyển sang UTF-16, 2 byte mỗi ký tự. Các chữ như `é`, `à`, `ô` vẫn thuộc Latin-1.

Vì immutable nên String chia sẻ được an toàn. JVM giữ một bảng gọi là String Pool. Mỗi literal như `"ADMIN"` trong code được [[string-interning|intern]]: lần đầu chạy tới, JVM tra bảng; chưa có thì tạo, có rồi thì dùng lại. Biểu thức hằng như `"AD" + "MIN"`, hoặc phép ghép từ biến `final` khởi tạo bằng hằng, được compiler [[constant-folding|gộp sẵn]] thành một literal, nên cũng vào pool.

Chuỗi tạo lúc runtime thì không vào pool. Ví dụ: `new String("ADMIN")`, `sb.toString()`, chuỗi đọc từ request, JSON hay DB, chuỗi ghép từ biến thường. Mỗi chuỗi đó là một object mới trên heap. Vì vậy `==` (so sánh tham chiếu) pass trong unit test dùng literal nhưng fail ở production. Luôn dùng `equals` và đặt literal phía trước (`"ADMIN".equals(role)`) để không lỗi khi `role` là `null`. Tốt hơn nữa là parse sang `enum`.

`intern()` trả về object trong pool, nên `s.intern() == "ADMIN"` là `true`. Pool nằm trong heap từ Java 7, nên chuỗi trong pool không còn ai tham chiếu vẫn được GC dọn. Dù vậy, tự `intern()` hàng triệu chuỗi để tiết kiệm bộ nhớ thường không đáng. Nên dùng `Map` của riêng bạn hoặc bật [[string-deduplication]] của GC.

Immutable còn mang lại các lợi ích sau:
- [[hash-code|hashCode]] tính một lần rồi cache, nên String là key tốt cho `HashMap`.
- Chuỗi dùng làm tên class, đường dẫn file hay URL không bị sửa sau khi đã kiểm tra quyền.
- Chia sẻ giữa nhiều thread mà không cần lock.

Bẫy hiệu năng hay gặp là ghép chuỗi bằng `+=` trong vòng lặp. Mỗi vòng tạo String mới và copy toàn bộ nội dung cũ, nên tổng chi phí là O(n²). Dùng `StringBuilder`, `String.join` hoặc `Collectors.joining`.

## Deep

- **Hằng lúc compile**: chỉ biến `final` khởi tạo bằng biểu thức hằng mới được gộp. Với `final String part = "AD";`, `part + "MIN"` vào pool. Bỏ `final`, hoặc khởi tạo bằng lời gọi method (`final String part = prefix();`), thì phép ghép xảy ra lúc runtime.
- **Java 9+ (JEP 280)**: `a + b` được compile thành `invokedynamic` gọi `StringConcatFactory`, nhanh hơn `StringBuilder` do compiler cũ sinh ra. Nhưng trong vòng lặp vẫn tạo chuỗi mới mỗi vòng, nên quy tắc dùng `StringBuilder` không đổi.
- **`new String("hi")`** tạo một String object mới nhưng **dùng chung mảng `value`** với literal. Constructor chỉ copy tham chiếu tới mảng, và điều này an toàn vì mảng không bao giờ bị sửa.
- **`substring`** từ Java 7u6 copy ký tự sang mảng mới. Trước đó nó dùng chung mảng của chuỗi gốc: cắt 10 ký tự từ chuỗi 10MB vẫn giữ cả 10MB trong bộ nhớ.
- **String Pool là một bảng băm** trong JVM. Có thể chỉnh số bucket bằng `-XX:StringTableSize` và xem thống kê bằng `-XX:+PrintStringTableStatistics`.
- **String deduplication** (`-XX:+UseStringDeduplication`): có trên G1 từ Java 8u20 và trên mọi GC chính từ Java 18. GC gộp các mảng `value` có nội dung trùng nhau. Object String vẫn khác nhau, nên `==` vẫn ra `false`.
- **`switch` trên String** được compile thành `switch` theo `hashCode()` rồi kiểm tra bằng `equals`, nên chạy đúng với chuỗi tạo lúc runtime.
- **Đổi chữ hoa/thường phụ thuộc `Locale`**: trên máy đặt locale Thổ Nhĩ Kỳ, `"TITLE".toLowerCase()` ra `"tıtle"` (chữ i không có chấm). Khi xử lý mã, key hay header thì dùng `toLowerCase(Locale.ROOT)` hoặc `equalsIgnoreCase`.
- **Mật khẩu nên để trong `char[]`**: String immutable nên không xoá được. Nó nằm trong bộ nhớ tới khi GC dọn và có thể lộ ra trong heap dump.
