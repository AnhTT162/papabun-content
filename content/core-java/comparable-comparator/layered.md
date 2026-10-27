## Quick

[[comparable|`Comparable`]] là thứ tự tự nhiên của class (`compareTo`), [[comparator|`Comparator`]] là thứ tự đặt từ bên ngoài. Cả hai phải là một [[total-order|thứ tự toàn phần]] nhất quán: **đảo dấu khi đổi chỗ, bắc cầu, và không bao giờ viết bằng phép trừ** vì tràn số làm sai dấu.

## Interview

`compareTo` trả số âm, 0 hoặc dương. Contract gồm: `sgn(a.compareTo(b)) == -sgn(b.compareTo(a))`; bắc cầu (`a > b`, `b > c` thì `a > c`); và nếu `a.compareTo(b) == 0` thì `a`, `b` so với mọi `c` cho cùng kết quả. Javadoc khuyến nghị thêm `compareTo == 0` khi và chỉ khi `equals`.

Vi phạm contract không báo lỗi ngay. Thuật toán sắp xếp tin vào contract nên cho kết quả sai, và với danh sách đủ dài thì [[timsort|TimSort]] phát hiện mâu thuẫn và ném `IllegalArgumentException: Comparison method violates its general contract!`, thường chỉ ở production vì dữ liệu test ít.

Nguồn vi phạm hay gặp nhất là phép trừ: `(a, b) -> (int) (a.createdAt() - b.createdAt())`. Hai mốc thời gian lệch hơn khoảng 24,8 ngày (2³¹ mili giây) thì ép kiểu sang `int` [[integer-overflow|tràn]] và đổi dấu. Ngay cả `a - b` trên `int` cũng sai mỗi khi hiệu vượt phạm vi `int`, ví dụ `Integer.MIN_VALUE - 1`. Dùng `Long.compare`, `Integer.compare` hoặc `Comparator.comparingLong`.

Ghép comparator bằng API có sẵn: `Comparator.comparing(Order::status).thenComparing(Order::createdAt, Comparator.reverseOrder())`. Bẫy: `reversed()` đảo **toàn bộ** chuỗi phía trước, không chỉ khoá cuối. Khoá có thể `null` thì bọc `Comparator.nullsLast(...)`, nếu không sắp xếp ném NPE.

[[iterator|`Iterator`]] là cách duyệt chung của collection; `for-each` biên dịch thành `iterator()`, `hasNext()`, `next()`. Xoá phần tử trong `for-each` thường ném `ConcurrentModificationException` (xoá đúng phần tử áp chót thì không, nên đừng dựa vào lỗi này để bắt bug) vì iterator là [[fail-fast]]; xoá bằng `iterator.remove()` hoặc `removeIf`. Chi tiết cơ chế `modCount` ở bài Collections Overview.

## Deep

- **Đã chạy JDK 27 (lab)**: ba sự kiện cách nhau 30 và 10 ngày, comparator trừ rồi ép `int` cho thứ tự vòng A < C < B < A và ra `[C, B, A]`. Với 2.000 sự kiện ngẫu nhiên trong 60 ngày, khoảng một phần tư số lần chạy ném lỗi contract (49/200 và 41/200 ở hai lần thử), không đảm bảo; số còn lại sắp sai mà im lặng.
- **TimSort chỉ ném khi gặp mâu thuẫn**: danh sách dưới 32 phần tử dùng binary insertion sort nên không bao giờ ném, chỉ sai thứ tự. Cờ `-Djava.util.Arrays.useLegacyMergeSort=true` vẫn làm lỗi biến mất trên JDK 27, nhưng chỉ là giấu lỗi; sửa comparator.
- **Ổn định**: `List.sort`, `Collections.sort`, `Arrays.sort(Object[])` là [[stable-sort|sắp xếp ổn định]]: phần tử bằng nhau giữ thứ tự cũ, nên sắp theo khoá phụ trước rồi khoá chính sau cũng ra đúng. `Arrays.sort(int[])` dùng dual-pivot quicksort, không ổn định nhưng với primitive thì không phân biệt được.
- **So `double`**: `(int) (a.score() - b.score())` biến chênh 0,3 thành 0, coi hai điểm là bằng. Dùng `Double.compare`, nó cũng xử lý `NaN` và `-0.0` nhất quán (`NaN` lớn nhất, `-0.0 < 0.0`), khác toán tử `<`.
- **Nhất quán với `equals` trong collection có thứ tự**: `TreeSet` dùng comparator chỉ theo tên sẽ bỏ mất hai người trùng tên khác tuổi. Thêm khoá phụ có tính duy nhất (id) vào cuối comparator. Ví dụ `BigDecimal` và cách so tiền đúng ở bài Số thực & tiền tệ.
- **`reversed()` và suy luận kiểu**: `Comparator.comparing(p -> p.name()).reversed()` không biên dịch vì lambda bị suy ra kiểu `Object`; dùng method reference `Person::name` hoặc ghi kiểu `(Person p) -> p.name()`. Muốn đảo một khoá thì truyền `Comparator.reverseOrder()` vào `thenComparing` của khoá đó.
- **`Stream.sorted()`** ổn định với stream có thứ tự; `PriorityQueue` chỉ bảo đảm phần tử đầu, duyệt iterator không theo thứ tự. `Comparable` raw (không generic) so khác kiểu sẽ ném `ClassCastException` lúc chạy.
- **`comparingInt`, `comparingLong`** tránh boxing từng lần so; với list lớn sắp xếp nhiều lần thì đáng kể.
- **Thứ tự chữ tiếng Việt**: `String.compareTo` so theo code unit UTF-16 nên `Ánh` đứng sau `Zoan`. Dùng `java.text.Collator` theo locale, cùng ý tưởng với [[collation]] của database nhưng chạy trong JVM, xem bài Thời gian & mã hoá ký tự.
- **`Comparable` trên entity JPA**: so theo id tự sinh thì entity chưa lưu (id `null`) làm NPE hoặc trùng nhau trong `TreeSet`. So theo khoá nghiệp vụ, hoặc sắp xếp ở query (`ORDER BY`) thay vì trong bộ nhớ.
- **Iterator tự viết**: `next()` khi hết phần tử phải ném `NoSuchElementException`, `remove()` mặc định ném `UnsupportedOperationException`. Implement `Iterable` để dùng được `for-each`. Duyệt song song và chia nhỏ là việc của `Spliterator`, xem bài Stream API.
- **Collection đồng thời không fail-fast**: iterator của `ConcurrentHashMap`, `CopyOnWriteArrayList` là [[weakly-consistent]], không ném lỗi nhưng có thể không thấy thay đổi mới, xem bài ConcurrentHashMap.
