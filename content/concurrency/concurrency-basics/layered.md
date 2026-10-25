## Quick

Các thread trong một JVM dùng chung heap: mọi object mà hai thread cùng giữ tham chiếu đều là **state dùng chung**. Khi kết quả phụ thuộc vào thứ tự xen kẽ của các thread, đó là [[race-condition|race condition]]. Hai dạng hay gặp nhất là **đọc-sửa-ghi** (`count++`) và **[[check-then-act|kiểm tra rồi hành động]]** (`if (!map.containsKey(k)) map.put(k, v)`). Code **thread-safe** là code vẫn đúng dù nhiều thread gọi cùng lúc, với bất kỳ cách xen kẽ nào, mà bên gọi không phải tự đồng bộ thêm.

## Interview

**Ba điều cần có khi chia sẻ state thay đổi được**:
- [[atomicity|Atomicity]]: một nhóm thao tác không bị thread khác chen vào giữa. `count++` là đọc, cộng, ghi; hai thread cùng đọc 5 thì cùng ghi 6, mất một lần cộng ([[lost-update|lost update]]).
- [[visibility|Visibility]]: thread B thấy được giá trị thread A đã ghi. Không có đồng bộ thì Java không hứa điều này (bài synchronized & volatile).
- Thứ tự: compiler và CPU được phép đổi thứ tự lệnh khi nhìn từ thread khác.

**[[critical-section|Critical section]]** là đoạn code truy cập state dùng chung mà chỉ được một thread chạy tại một thời điểm. Nó phải bao **toàn bộ** thao tác ghép: kiểm tra và hành động phải nằm trong cùng một lần khoá.

**[[thread-safe|Thread-safe]] bằng cách nào** (theo thứ tự nên nghĩ tới):
1. Không chia sẻ: biến cục bộ và tham số nằm trên stack riêng của thread ([[thread-confinement|thread confinement]]).
2. Không thay đổi: object [[immutable]] (`record` với field bất biến, `String`, `DateTimeFormatter`) dùng chung thoải mái.
3. Giao cho class đồng thời của JDK: `ConcurrentHashMap`, `AtomicLong`, `BlockingQueue`, và dùng thao tác atomic của chúng (`merge`, `computeIfAbsent`).
4. Tự khoá bằng `synchronized` hay `Lock`.

**Bean singleton**: Spring mặc định tạo **một** object cho mỗi bean ([[bean-scope|scope]] singleton), và mọi thread xử lý request (Tomcat mặc định tối đa 200) gọi vào cùng object đó. Field là dependency được inject một lần lúc khởi động thì an toàn. Field giữ dữ liệu của từng request ("user hiện tại", kết quả tạm, `SimpleDateFormat`) là race condition. Bean nên **stateless**: dữ liệu theo request đi qua tham số.

**Một JVM chưa phải cả hệ thống**: `synchronized` chỉ chặn thread trong cùng tiến trình. Ba pod cùng trừ tồn kho thì cần khoá ở database hoặc ràng buộc trong database (bài Optimistic & pessimistic locking).

## Deep

- **Race condition và [[data-race|data race]] là hai chuyện khác**:
  - Data race là định nghĩa của [[jmm|Java Memory Model]]: hai thread truy cập cùng biến, ít nhất một bên ghi, không có đồng bộ giữa chúng.
  - Race condition là lỗi logic do thứ tự xen kẽ. Có race condition mà không có data race: `containsKey` rồi `put` trên `ConcurrentHashMap`, từng lời gọi đều an toàn nhưng cặp lời gọi thì không.
  - Cũng có data race vô hại có chủ đích: `String.hashCode()` lưu hash vào field thường; hai thread có thể cùng tính, nhưng luôn ra cùng một giá trị.
- **Ghép hai lời gọi thread-safe không ra thread-safe**:
  - `if (!map.containsKey(k)) map.put(k, load(k))` có thể gọi `load` hai lần và ghi đè. Dùng `map.computeIfAbsent(k, this::load)`: với `ConcurrentHashMap`, cả lời gọi là atomic và hàm chạy nhiều nhất một lần trong khi khoá còn vắng (hàm trả `null` hoặc ném exception thì không lưu gì, lần gọi sau chạy lại).
  - Đếm theo khoá: `map.merge(k, 1, Integer::sum)` thay cho `get` rồi `put`.
  - Hàm trong `compute*` chạy khi đang giữ khoá của bin: đừng gọi I/O chậm trong đó, và đừng sửa chính map đó trong hàm (Java 9+ có thể ném `IllegalStateException: Recursive update`).
- **`Collections.synchronizedList`** khoá từng lời gọi, nhưng duyệt bằng iterator thì phải tự `synchronized (list)` bao cả vòng lặp, nếu không có thể gặp `ConcurrentModificationException`. Exception này chỉ là phát hiện "cố gắng hết sức", không phải cơ chế đảm bảo.
- **`HashMap` dùng chung giữa nhiều thread ghi**:
  - Java 7: resize đồng thời có thể tạo vòng trong danh sách liên kết, sau đó `get` quay vô hạn và một core lên 100%.
  - Java 8 trở đi: không còn vòng do resize danh sách liên kết, nhưng vẫn mất phần tử, `size()` sai, có thể ném `ClassCastException` (`HashMap$Node` sang `HashMap$TreeNode`) hoặc treo 100% CPU trong thao tác trên bin dạng cây (`TreeNode.balanceInsertion`, `root`).
  - Cách sửa luôn là `ConcurrentHashMap`, không phải "thêm try-catch".
- **Ví dụ kinh điển trong code Spring**:
  - `private static final SimpleDateFormat FMT` dùng chung: thỉnh thoảng ra ngày sai hoặc `NumberFormatException` dưới tải. Thay bằng `DateTimeFormatter` (bất biến).
  - Cache tự viết bằng `HashMap` trong field của bean: thay bằng `ConcurrentHashMap` hoặc Caffeine.
  - Bean scope `prototype` không giải quyết được vấn đề: [[prototype-in-singleton|inject vào singleton]] thì vẫn chỉ có một object.
  - "User hiện tại" nên ở đâu: Spring Security giữ nó trong `SecurityContextHolder`, `RequestContextHolder` giữ request; cả hai dựa trên `ThreadLocal`, tức là confinement theo thread (bài ThreadLocal & ScopedValue). Bean `@RequestScope` là một proxy trỏ tới object riêng của từng request.
  - Bật virtual thread (`spring.threads.virtual.enabled=true`) thì không còn trần 200 thread của Tomcat: số request chạy song song cao hơn hẳn và race condition lộ ra nhanh hơn.
- **Đọc ghi một biến có atomic không**: đọc hay ghi một `int`, `boolean` hay tham chiếu là atomic. `long` và `double` không `volatile` thì spec cho phép xé thành hai nửa 32 bit (JLS 17.7). Atomic từng lần đọc ghi vẫn không làm `x++` hay `if (x == null) x = ...` thành atomic.
- **Thu nhỏ critical section**: chỉ khoá phần đọc và ghi state, không khoá quanh lời gọi HTTP hay database. Khoá giữ lâu biến server nhiều thread thành hàng đợi một làn.
- **Mức độ thread-safe** (theo Effective Java): bất biến; thread-safe vô điều kiện (`ConcurrentHashMap`); thread-safe có điều kiện, khi bên gọi phải tự khoá cho thao tác ghép (`Collections.synchronizedList` khi duyệt); không thread-safe (`ArrayList`, `HashMap`); và thù địch với thread (thread-hostile): không dùng an toàn được dù bên gọi khoá thế nào, thường vì sửa state `static` mà không đồng bộ. Javadoc của class nên ghi rõ mức nào.
- **Vì sao test không bắt được**: race condition cần đúng cửa sổ thời gian, thường chỉ vài nano giây. Test đơn luồng luôn qua; lỗi xuất hiện dưới tải thật và biến mất khi thêm log. Cách tái hiện và kiểm thử ở bài Kiểm thử code đồng thời.
