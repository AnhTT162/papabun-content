## Quick

`equals` trả lời câu hỏi "hai object có bằng nhau về ý nghĩa không". `hashCode` trả về một số nguyên để `HashMap`, `HashSet` biết cần tìm ở [[bucket]] nào. Quy tắc bắt buộc: **hai object `equals` nhau thì phải có cùng `hashCode`**.

## Interview

Mặc định, `Object.equals` so sánh tham chiếu (giống `==`), còn `Object.hashCode` dựa trên danh tính object. Vì vậy hai object khác nhau luôn được coi là khác nhau.

Khi override `equals` để so theo giá trị, phải giữ đúng contract:

- **Reflexive**: `a.equals(a)` luôn `true`.
- **Symmetric**: `a.equals(b)` thì `b.equals(a)`.
- **Transitive**: `a.equals(b)` và `b.equals(c)` thì `a.equals(c)`.
- **Consistent**: gọi nhiều lần cho cùng kết quả nếu object không đổi.
- `a.equals(null)` luôn `false`.

Contract với `hashCode`: hai object `equals` nhau phải có cùng `hashCode`. Chiều ngược lại không bắt buộc: hai object khác nhau vẫn có thể trùng `hashCode`, gọi là [[hash-collision]].

Nếu override `equals` mà quên `hashCode`, `HashSet` có thể chứa hai phần tử "bằng nhau", còn `HashMap.get` trả về `null` với một key tương đương. Lý do: lookup tính `hashCode` trước, rơi vào bucket khác nên không bao giờ tới bước gọi `equals`.

Cách làm an toàn: dùng cùng một tập field cho cả hai method, dùng `Objects.equals` và `Objects.hash`, hoặc dùng `record` (Java 16+) để compiler tự sinh cả hai.

## Deep

- **Key bị sửa sau khi `put`**: nếu field tham gia `hashCode` thay đổi sau khi object đã nằm trong `HashMap`, entry vẫn ở bucket cũ và không tìm lại được nữa. Vì vậy key nên là [[immutable]].
- **Kế thừa**: dùng `instanceof` trong `equals` có thể phá tính symmetric khi lớp con thêm field. Các lựa chọn: so `getClass()`, khai báo class `final`, hoặc dùng composition thay cho kế thừa.
- **`HashMap` dùng `hashCode` thế nào**: trộn bit cao xuống bit thấp bằng `h ^ (h >>> 16)`, rồi chọn bucket bằng `(n - 1) & hash`. `hashCode` phân bố kém sẽ dồn nhiều key vào cùng một bucket và làm chậm lookup.
- **`String` cache `hashCode`** trong field `hash`, làm được vì `String` là immutable.
- **Hiệu năng**: `Objects.hash(...)` tạo mảng varargs mỗi lần gọi. Với class làm key trong đoạn code rất nóng, có thể tự viết `31 * result + field.hashCode()`.
