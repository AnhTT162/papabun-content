## Quick

Java 17 và 21 (hai bản LTS) cùng [[record-class|record]] biến Java thành ngôn ngữ mô hình hoá dữ liệu tốt hơn: record cho dữ liệu, [[sealed-class|sealed]] cho tập biến thể đóng, và [[pattern-matching|pattern matching]] để tách dữ liệu theo từng biến thể. **`switch` trên kiểu `sealed` không có `default` được compiler kiểm đủ nhánh**, nên thêm biến thể là lỗi biên dịch thay vì lỗi production. Nâng cấp từ 8/11 thì phần khó là [[strong-encapsulation|đóng gói chặt]] nội bộ JDK và `javax` sang `jakarta`, không phải cú pháp mới.

## Interview

**[[switch-expression|Switch expression]]** (14): `switch` trả giá trị, phải đủ nhánh, khối nhiều lệnh dùng `yield`. Nhãn mũi tên `case A, B ->` (dùng được cả trong switch statement) không rơi xuống nhánh dưới; nhãn `case A:` trong switch expression vẫn rơi xuống.

**Pattern matching cho `instanceof`** (16): `if (o instanceof String s && s.length() > 3)` vừa kiểm vừa gán, `s` chỉ có phạm vi ở nơi điều kiện chắc chắn đúng.

**Pattern matching cho `switch`** (21): nhánh theo kiểu (`case Card c ->`), kèm điều kiện (`case Cash c when c.amount() > 1000 ->`), và [[record-pattern|record pattern]] tách component ngay trong nhánh (`case Card(var last4) ->`). Nhánh cụ thể phải đứng trước nhánh tổng quát, nếu không compiler báo nhánh không bao giờ chạy tới.

**`null` trong switch**: `switch` truyền thống và pattern switch không có `case null` vẫn ném NPE với `null`. Java 21 cho viết `case null ->` hoặc `case null, default ->`.

**Sealed** (17): `sealed interface Payment permits Card, Cash, Wallet {}`; lớp con phải `final`, `sealed` hoặc `non-sealed`. Kết hợp với record là kiểu dữ liệu đại số: `Payment` là đúng một trong ba dạng.

**[[text-block|Text block]]** (15): `"""` nhiều dòng, phần thụt đầu dòng chung bị cắt theo vị trí của dòng thụt ít nhất (kể cả dòng `"""` đóng), khoảng trắng cuối dòng bị xoá; giữ bằng `\s`, nối dòng bằng `\` ở cuối.

**[[sequenced-collection|Sequenced collection]]** (21): `List`, `Deque`, `LinkedHashSet`, `SortedSet` có chung `getFirst`, `getLast`, `addFirst`, `reversed()`; `LinkedHashMap`, `TreeMap` có `firstEntry`, `lastEntry`, `putFirst`, `sequencedKeySet`.

**Nâng cấp từ 8/11**: JDK 9+ chia module ([[jpms|JPMS]]); từ 16 mặc định chặn, từ 17 (JEP 403) chặn hẳn reflection vào nội bộ JDK. Việc Java 11 xoá JAXB, JAX-WS ở bài Java 8 → 11. Spring Boot 3 cần Java 17 và chuyển `javax.*` sang `jakarta.*`. Thư viện sinh bytecode (Lombok, Mockito, ByteBuddy, ASM) phải lên bản hiểu class file mới; từ 21 (JEP 451) agent nạp động như Mockito inline mock in cảnh báo, cần `-javaagent` hoặc `-XX:+EnableDynamicAgentLoading`.

Cách làm đúng: nâng từng LTS, chạy test với JDK mới trước khi đổi `--release`, đọc cảnh báo `illegal reflective access` từ Java 9–15 vì đó là danh sách lỗi sẽ gặp.

## Deep

- **Đã chạy JDK 27**: `switch` có `case Card(var l4)`, `case Cash(long amt) when amt > 1000`, `case Cash c` trên `sealed` không cần `default` và chạy ra `big cash`; `switch` trên `Object` `null` không có `case null` ném NPE. Reflection `ArrayList.elementData` ném `Unable to make field transient java.lang.Object[] java.util.ArrayList.elementData accessible: module java.base does not "opens java.util" to unnamed module`. `sealed` không khai báo được cho class local.
- **Kiểm đủ nhánh và biên dịch tách rời**: compiler kiểm đủ nhánh lúc biên dịch; nếu thư viện thêm biến thể mà code của bạn không biên dịch lại, `switch` gặp kiểu lạ lúc chạy ném `MatchException` (Java 21; enum thì `IncompatibleClassChangeError` ở bản cũ). Đó là lý do `sealed` hợp nhất khi các lớp con nằm cùng module.
- **Thứ tự và dominance**: `case CharSequence cs` đứng trước `case String s` là lỗi biên dịch. Nhánh có `when` không được tính vào kiểm đủ nhánh, nên vẫn cần một nhánh không điều kiện cho kiểu đó.
- **Text block có dòng trống cuối**: đặt `"""` đóng ở dòng riêng thì chuỗi kết thúc bằng `\n`; JSON hay SQL so sánh chính xác sẽ khác. Thụt `"""` đóng sang trái để giữ thụt đầu dòng mong muốn.
- **`reversed()` là view**: `list.reversed()` của sequenced collection phản ánh thay đổi của list gốc và không sao chép. `LinkedHashMap.firstEntry()`, `pollFirstEntry()` hữu ích cho cache LRU tự viết.
- **Xung đột tên khi nâng lên 21**: class tự viết kế thừa `List` có method `getFirst()` trả kiểu khác sẽ không biên dịch. Code Kotlin gọi `list.removeFirst()` biên dịch với JDK 21 sẽ trỏ vào method mới của JDK và ném `NoSuchMethodError` khi chạy trên JRE cũ hơn (JEP 431 mục rủi ro). `getFirst()` trên list rỗng ném `NoSuchElementException`, khác `get(0)` ném `IndexOutOfBoundsException`; `TreeSet.addFirst` ném `UnsupportedOperationException`.
- **`--add-opens` và `--add-exports`**: `--add-opens module/package=ALL-UNNAMED` mở reflection sâu, `--add-exports` mở truy cập lúc biên dịch. Ghi chúng vào manifest `Add-Opens` của jar chạy được hoặc biến `JDK_JAVA_OPTIONS`, kèm ticket để gỡ khi thư viện được nâng.
- **API bị xoá theo lộ trình**: Nashorn bị xoá ở 15, SecurityManager deprecated ở 17 và vô hiệu ở 24, finalization deprecated để xoá (18, JEP 421), `Thread.stop` ném lỗi từ 20. Chạy `jdeprscan` và `jdeps --jdk-internals` trên jar cũ để liệt kê trước.
- **Mặc định đổi giữa các bản**: UTF-8 mặc định (18, bài Thời gian & mã hoá ký tự), helpful NPE (15), G1 làm mặc định (9), `UseCompactObjectHeaders` mặc định (JDK 27). Đo lại hiệu năng và bộ nhớ sau khi nâng, không giả định giống cũ.
- **Preview không phải tính năng chính thức**: unnamed pattern `_` là preview ở 21 (chính thức ở 22), String Templates preview ở 21 rồi bị gỡ ở 23; preview cần `--enable-preview`. Generational ZGC có từ 21 (JEP 439).
- **Virtual thread** (21) là lý do nâng cấp lớn nhất của Java 21 cho server I/O; chi tiết ở bài Virtual Threads chuyên sâu.
