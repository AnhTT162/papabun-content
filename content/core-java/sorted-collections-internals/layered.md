## Quick

`TreeMap`/`TreeSet` là [[red-black-tree|cây đỏ đen]]: luôn có thứ tự theo `compareTo`/comparator, mọi thao tác O(log n). `LinkedHashMap` là `HashMap` cộng một danh sách liên kết đôi giữ thứ tự chèn hoặc thứ tự truy cập ([[lru|LRU]]). `PriorityQueue` là [[binary-heap|binary heap]] trong mảng: lấy phần tử nhỏ nhất O(log n) nhưng **chỉ phần tử đầu có thứ tự**. Chọn theo câu hỏi cần trả lời: "khoảng/gần nhất" thì TreeMap, "thứ tự chèn/LRU" thì LinkedHashMap, "lớn nhất tiếp theo" thì PriorityQueue.

## Interview

**TreeMap**: mỗi node đỏ hoặc đen; gốc đen, node đỏ không có con đỏ, mọi đường từ một node xuống lá có cùng số node đen. Hệ quả: đường dài nhất không quá hai lần đường ngắn nhất, chiều cao ≤ 2·log₂(n+1). Thêm node mới tô đỏ, nếu vi phạm thì đổi màu hoặc [[tree-rotation|xoay]] (tối đa hai lần xoay mỗi lần chèn). Key bằng nhau khi `compare` trả 0, không dùng `equals`/`hashCode`.

Giá trị của TreeMap là truy vấn theo thứ tự ([[navigable-map|NavigableMap]]): `floorKey`, `ceilingEntry`, `headMap`, `tailMap`, `subMap`, `firstEntry`, `pollFirstEntry`. `floor`/`lower`/`ceiling`/`higher` là ≤ / < / ≥ / >, trả `null` khi không có (với key 100, 200, 500: `floorKey(250)` là 200, `lowerKey(200)` là 100). `headMap(k)` loại `k`, `tailMap(k)` gồm `k`, `subMap(a, b)` là [a, b), có overload chỉ định bao hay không. Ví dụ bảng giá theo bậc: `prices.floorEntry(amount)`. Đổi lại, tra cứu theo key chậm hơn `HashMap` nhiều: mỗi bước so sánh là một lần nhảy con trỏ tới node khác.

**LinkedHashMap**: mỗi entry có thêm `before`/`after`. Mặc định giữ thứ tự chèn (`put` lại key cũ không đổi thứ tự). Constructor `LinkedHashMap(cap, 0.75f, true)` chuyển sang thứ tự truy cập: `get` đẩy entry xuống cuối; kết hợp `removeEldestEntry` là LRU một dòng. Bẫy: ở chế độ truy cập, `get` (cả `getOrDefault`, `put` lên key cũ, `compute`, `merge`) **đổi cấu trúc**, nên gọi `get` trong lúc duyệt `keySet()` làm iterator [[fail-fast]] ném `ConcurrentModificationException` ở lần lặp sau, và đọc từ nhiều thread cũng không an toàn.

**PriorityQueue**: heap trong mảng, phần tử ở `i` có con ở `2i+1`, `2i+2`, cha nhỏ hơn con. `offer`/`poll` O(log n), `peek` O(1), nhưng `contains` và `remove(Object)` O(n) vì phải quét mảng. Dựng từ một collection là heapify O(n); phần tử cùng độ ưu tiên ra theo thứ tự không xác định. Top-k phần tử lớn nhất từ luồng n phần tử: giữ min-heap cỡ k, O(n log k) và bộ nhớ O(k).

Bẫy hay gặp: duyệt `PriorityQueue` tưởng có thứ tự; sửa field dùng để so sánh sau khi phần tử đã vào TreeMap/PriorityQueue (cấu trúc không tự sắp lại); dùng TreeMap chỉ để tra cứu theo key.

## Deep

- **Đã chạy JDK 27 (đo thô, không JMH)**: 1 triệu key `Integer` ngẫu nhiên, tra cứu lại toàn bộ: `HashMap` 24–33 ms, `TreeMap` 289–302 ms (khoảng 10 lần, phần lớn do cây lớn hơn cache CPU; map nhỏ chênh ít hơn nhiều). LRU sức chứa 3: `put a, b, c`, `get a`, `put d` còn `[c, a, d]`. `PriorityQueue` từ `[5,1,4,2,3]` in `[1, 2, 4, 5, 3]` (thứ tự mảng là chi tiết cài đặt của OpenJDK), `poll` dần ra `[1, 2, 3, 4, 5]`.
- **Phần tử bị sửa sau khi thêm**: task có `prio` 5, 3, 4; đổi task 5 thành 1 sau khi thêm, `peek()` vẫn trả task có `prio` 3 (đã chạy). Muốn đổi độ ưu tiên thì `remove` rồi `offer` lại, hoặc dùng phần tử bất biến.
- **View của TreeMap sống theo map gốc**: `headMap(300)` thấy key 150 được thêm sau vào map gốc; `put(400, ...)` qua view ném `IllegalArgumentException: key out of range`. Duyệt view và sửa map gốc cùng lúc cũng là fail-fast.
- **TreeMap và `null`**: key `null` ném NPE với thứ tự tự nhiên; comparator `nullsFirst` thì nhận. Value `null` luôn được.
- **Tại sao không AVL**: AVL cân bằng chặt hơn (tra cứu nhanh hơn chút). Khi chèn, cả hai cần tối đa 2 lần xoay; khi xoá, AVL có thể phải xoay O(log n) lần còn cây đỏ đen tối đa 3, nên cây đỏ đen là thoả hiệp tốt cho cấu trúc đọc ghi lẫn lộn. Bin dạng cây của `HashMap` (treeify) cũng là cây đỏ đen (bài HashMap Internals).
- **Bản đồng thời**: `ConcurrentSkipListMap`/`Set` là TreeMap an toàn đa luồng không khoá toàn cục (bài Cấu trúc dữ liệu trong hệ thống lớn); `PriorityBlockingQueue` là heap có khoá, `DelayQueue` là heap theo thời điểm hết hạn (nền của `ScheduledThreadPoolExecutor` dùng heap riêng tương tự).
- **`ArrayDeque`** là mảng vòng, nhanh hơn `Stack` (đồng bộ, kế thừa `Vector`) và `LinkedList` cho cả stack lẫn queue; không nhận `null`.
- **Bộ nhớ**: node `TreeMap` có key, value, left, right, parent, color; entry `LinkedHashMap` có thêm `before`, `after` so với `HashMap`. Với hàng triệu phần tử, chi phí object và tham chiếu thường lớn hơn dữ liệu thật (số đo `HashMap<Long, Long>` ở bài Cấu trúc dữ liệu cơ bản & Big-O).
- **`TreeMap` sắp theo chuỗi**: `String.compareTo` so code unit nên tên tiếng Việt có dấu (dạng NFC) đứng sau chữ Z; dùng `TreeMap<>(collator)` với `Collator` cho tiếng Việt (bài Comparable, Comparator & Iterator).
