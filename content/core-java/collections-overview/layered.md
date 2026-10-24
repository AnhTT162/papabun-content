## Quick

Bốn nhóm chính: `List` (có thứ tự, cho trùng), `Set` (không trùng), `Queue`/`Deque` (hàng đợi) và `Map` (key → value, không kế thừa `Collection`). Mặc định nên chọn **`ArrayList`, `HashMap`, `HashSet`, `ArrayDeque`**. Chỉ đổi sang cài đặt khác khi cần đúng tính chất của nó: sắp xếp, giữ thứ tự, ưu tiên hoặc thread-safe.

## Interview

Gốc của [[collection-framework|Collections Framework]] là `Collection` với ba nhánh `List`, `Set`, `Queue`. `Map` đứng riêng.

**List**
- `ArrayList` là mảng động. `get(i)` là O(1). `add` cuối là O(1) [[amortized-complexity|khấu hao]]: khi đầy, mảng tăng khoảng 1,5 lần và copy sang mảng mới. Chèn hay xoá ở giữa là O(n) vì phải dịch phần tử.
- `LinkedList` là danh sách liên kết đôi. Thêm/xoá ở hai đầu là O(1), nhưng `get(i)` là O(n). Mỗi phần tử còn tốn thêm một node object. Thực tế `ArrayList` thường nhanh hơn kể cả khi chèn giữa, nhờ [[cache-locality]] và `System.arraycopy`.

**Set**
- `HashSet` dùng `HashMap` bên trong: O(1) trung bình, không giữ thứ tự.
- `LinkedHashSet` giữ thứ tự thêm vào.
- `TreeSet` là [[red-black-tree|cây đỏ đen]], O(log n), luôn sắp xếp. Nó có thêm các thao tác tìm theo khoảng như `floor`, `ceiling`, `headSet`.

**Queue/Deque**
- `ArrayDeque` là lựa chọn mặc định cho cả stack lẫn queue, nhanh hơn `Stack` và `LinkedList`.
- `PriorityQueue` là binary heap: `offer`/`poll` O(log n), `peek` O(1).

**Map**
- `HashMap` O(1) trung bình.
- `LinkedHashMap` giữ thứ tự thêm vào, hoặc thứ tự truy cập nếu bật `accessOrder`. Đây là cách viết LRU cache nhanh nhất.
- `TreeMap` O(log n), có `floorKey`, `ceilingEntry`, `subMap`.
- `EnumMap`/`EnumSet` dùng khi key là enum, rất gọn và nhanh.

**Bất biến và view**: Java 9 có `List.of`, `Set.of`, `Map.of`. Các collection này không sửa được, không nhận `null`, và `Set.of` ném lỗi nếu có phần tử trùng. `Collections.unmodifiableList(list)` chỉ là [[unmodifiable-view|view]]: list gốc đổi thì view đổi theo. `List.copyOf` mới thật sự tạo bản sao. `Arrays.asList` có kích thước cố định: `set` được, còn `add`/`remove` ném `UnsupportedOperationException`.

**Đa luồng**: collection thường không thread-safe. Lựa chọn tuỳ theo cách dùng:
- `ConcurrentHashMap` cho map dùng chung.
- `CopyOnWriteArrayList` cho danh sách đọc nhiều, ghi rất ít (ví dụ listener). Đây là kiểu [[copy-on-write]].
- `BlockingQueue` cho mô hình producer–consumer.

`Vector`, `Hashtable` và `Collections.synchronizedXxx` khoá toàn bộ collection mỗi thao tác, và vẫn phải tự khoá khi duyệt.

Bẫy hay gặp: xoá phần tử trong vòng `for-each` thường ném `ConcurrentModificationException` vì iterator là [[fail-fast]]. Dùng `removeIf` hoặc `Iterator.remove()`.

## Deep

- **Java 21 ([[sequenced-collection|Sequenced Collections]], JEP 431)**: `List`, `Deque`, `LinkedHashSet`, `SortedSet` có thêm `getFirst()`, `getLast()`, `reversed()`, nên không cần viết `list.get(list.size() - 1)` nữa. Map có thứ tự (`LinkedHashMap`, `SortedMap`) cài đặt `SequencedMap` với `firstEntry()`, `lastEntry()`, `putFirst()`, `putLast()`, `reversed()`. `TreeMap.putFirst` ném `UnsupportedOperationException` vì vị trí do thứ tự key quyết định.
- **`TreeSet`/`TreeMap` coi hai phần tử là trùng khi `compare` trả 0**, không dùng `equals`. Comparator chỉ so độ dài sẽ làm `"an"` và `"bo"` thành một phần tử. Comparator nên nhất quán với `equals`, hoặc thêm tiêu chí phụ bằng `thenComparing`.
- **`PriorityQueue` không sắp xếp khi duyệt**: `iterator()` và `toString()` đi theo thứ tự của mảng heap. Chỉ `poll()` lần lượt mới ra đúng thứ tự ưu tiên.
- **`List.of(...).contains(null)` ném `NullPointerException`**, không trả `false`. `Map.of` có thứ tự duyệt không xác định và có thể khác nhau giữa các lần chạy JVM.
- **`Stream.toList()` (Java 16)** trả list không sửa được. `Collectors.toList()` không cam kết gì về khả năng sửa, dù thực tế đang trả `ArrayList`.
- **`ConcurrentHashMap` không nhận `null`** cho cả key và value, để `get` trả `null` chỉ có một nghĩa là "không có". Cập nhật kiểu đọc rồi ghi thì dùng `compute`, `merge`, `computeIfAbsent` để thao tác là nguyên tử.
- **Định trước dung lượng**: `new ArrayList<>(n)` tránh copy nhiều lần. Từ Java 19, `HashMap.newHashMap(n)` tính sẵn dung lượng theo [[load-factor]] để chứa đủ `n` phần tử. `new HashMap<>(n)` chỉ đặt capacity (làm tròn lên luỹ thừa của 2), nên có thể resize trước khi đủ `n` phần tử: ngưỡng là capacity × 0,75.
- **Bộ nhớ**: `ArrayList<Integer>` vẫn phải boxing từng số. Với hàng triệu số, mảng `int[]` hoặc thư viện collection cho kiểu primitive tiết kiệm bộ nhớ hơn nhiều lần.
- **Fail-fast chỉ là "cố gắng"**: xoá đúng phần tử áp chót trong `for-each` không ném lỗi, vì `hasNext()` trả `false` trước khi `next()` kịp kiểm tra. Code vẫn sai, chỉ là lỗi bị che.
- **`subList` là view** của list gốc: sửa cấu trúc list gốc rồi dùng lại `subList` sẽ ném `ConcurrentModificationException`.
