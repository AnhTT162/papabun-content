## Quick

Object [[immutable|bất biến]] không đổi trạng thái sau khi tạo, nên chia sẻ giữa các thread, làm key của map và cache mà không cần khoá. **Bất biến phải sâu**: field `final` chưa đủ nếu nó trỏ tới object mutable; phải [[defensive-copy|sao chép phòng thủ]] khi nhận vào và không để lộ tham chiếu ra ngoài. [[record-class|Record]] (Java 16) sinh sẵn phần khung nhưng chỉ bất biến nông.

## Interview

Năm điều kiện của class bất biến:

1. Không có method sửa trạng thái (setter, `add`).
2. Class `final` (hoặc constructor `private` + static factory), để lớp con không thêm trạng thái mutable.
3. Mọi field `private final`.
4. Field trỏ tới object mutable (list, mảng, `Date`) thì sao chép khi nhận vào constructor và khi trả ra getter, hoặc chỉ giữ bản bất biến.
5. `this` không lọt ra ngoài trong constructor ([[this-escape]]).

**View không sửa được khác bản sao**: `Collections.unmodifiableList(list)` là [[unmodifiable-view|view]], chặn sửa qua view nhưng thấy mọi thay đổi trên list gốc. `List.copyOf(list)` (Java 10) tạo bản sao bất biến thật, từ chối `null`, và trả lại chính nó nếu đầu vào đã là list tạo bởi `List.of`/`copyOf` (một view `unmodifiableList` thì vẫn bị chép).

**Record** `record Money(BigDecimal amount, Currency currency) {}` sinh: field `private final`, constructor đủ tham số (canonical), accessor `amount()`, `equals`/`hashCode`/`toString` theo mọi component. Record là `final`, kế thừa `java.lang.Record`, không kế thừa class khác nhưng implement được interface. [[compact-constructor|Compact constructor]] dùng để validate và chuẩn hoá: `Money { if (amount.signum() < 0) throw ...; amount = amount.setScale(...); }`.

Lợi ích: không có lớp lỗi "ai đó sửa object của tôi", `hashCode` ổn định khi làm key, an toàn đa luồng nhờ ngữ nghĩa field `final` (bài Java Memory Model), cache được mà không cần sao chép. Giá: mỗi lần "sửa" tạo object mới; với object lớn sửa liên tục (buffer, ma trận) thì mutable rẻ hơn.

Bẫy hay gặp: record giữ `List` hay mảng nhận từ ngoài; getter trả thẳng field mutable; `unmodifiableList` bọc list mà class khác vẫn giữ tham chiếu; nghĩ `final` là bất biến.

Cách làm đúng: mặc định viết DTO, command, event, [[value-object|value object]] bằng record; chép collection bằng `List.copyOf`/`Map.copyOf` trong compact constructor; mảng thì `clone()` cả lúc nhận và lúc trả, hoặc thay bằng `List`.

## Deep

- **Đã chạy JDK 27 (lab)**: record `Order` giữ `ArrayList` từ bên ngoài, đưa vào `HashSet` rồi bên gọi `items.add("quan")`: record in ra đã đổi, `set.contains(o)` là `false` dù là chính object đó, và `contains` với một `Order` bằng nó theo `equals` cũng `false`. Còn `Collections.unmodifiableList(base)` thấy phần tử `base` thêm sau, `List.copyOf(base)` thì không.
- **Chép trước, kiểm sau**: validate list rồi mới chép thì thread khác có thể sửa list giữa hai bước (TOCTOU). Viết `items = List.copyOf(items); if (items.isEmpty()) throw ...` để kiểm trên bản đã chép.
- **"Bất biến" không giống nhau**: `List.of`/`List.copyOf` bất biến và từ chối `null`; `Stream.toList()` (16) bất biến nhưng nhận `null`; `Collections.unmodifiableList` chỉ là view; `Arrays.asList` sửa được phần tử (`set`) chỉ không đổi được kích thước.
- **Record chứa `BigDecimal`**: `equals` của record dùng `BigDecimal.equals`, nhạy scale, nên `Money(1.0)` khác `Money(1.00)`. Chuẩn hoá `setScale` trong compact constructor (bài Số thực & tiền tệ).
- **Record với mảng**: `equals` so mảng bằng tham chiếu, nên `new Hash(new byte[]{1}).equals(new Hash(new byte[]{1}))` là `false`. Override `equals`, `hashCode`, `toString` bằng `Arrays.equals`/`Arrays.hashCode`, và `clone()` trong constructor lẫn accessor; hoặc dùng `List<Byte>`/`ByteBuffer` chỉ đọc tuỳ trường hợp.
- **Compact constructor gán lại tham số**, không gán `this.items`: compiler tự gán field từ tham số ở cuối. Accessor có thể override nhưng phải trả cùng kiểu; trả bản sao trong accessor tốn mỗi lần đọc, nên chép một lần trong constructor tốt hơn.
- **"Wither"**: JDK 27 chưa có cú pháp `with` cho record, kể cả ở chế độ preview (JEP 468 mới là đề xuất; đã thử `--enable-preview`); viết method `withAmount(BigDecimal a) { return new Money(a, currency); }`. Record nhiều field mà hay đổi một field thì cân nhắc builder.
- **Record và serialization**: Java serialization khôi phục record qua canonical constructor, nên validate trong compact constructor chạy cả khi deserialize, khác class thường (bài Serialization & lỗ hổng deserialization).
- **[[value-based-class|Value-based class]]** như `Optional`, `LocalDate`, `Integer` là bất biến và không nên dùng danh tính (`==`, `synchronized`). Project Valhalla (JEP 401) sẽ cho JVM bỏ danh tính của chúng để trải phẳng trong mảng; chưa có trong JDK 27, kiểm lại khi nâng JDK.
- **Bất biến và đa luồng**: object bất biến tự nó [[safe-publication|công bố an toàn]] nhờ đảm bảo của field `final`, kể cả khi tham chiếu được chia sẻ qua [[data-race|data race]]. Biến **trỏ tới** object bất biến thì vẫn cần `volatile` hay `AtomicReference` nếu nhiều thread thay nó ([[copy-on-write]]: tạo object mới rồi đổi tham chiếu).
- **`BigDecimal` bất biến nhưng không `final`**: nên một lớp con độc hại có thể mutable; code bảo mật nhận `BigDecimal` từ bên ngoài nên chuẩn hoá lại bằng `new BigDecimal(x.unscaledValue(), x.scale())` (khuyến nghị của Effective Java).
- **Collection bất biến của Guava** (`ImmutableList`) có trước `List.copyOf`, giữ thứ tự chèn của `ImmutableMap`; `Map.of`/`Map.copyOf` của JDK thì thứ tự duyệt không xác định. Kotlin `List` chỉ là interface chỉ-đọc, không bảo đảm bất biến.
