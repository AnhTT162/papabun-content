## Quick

`ConcurrentHashMap` (Java 8+) không khoá cả map: bin trống thì chèn bằng [[cas|CAS]], bin đã có node thì `synchronized` trên node đầu bin, còn `get` không khoá gì. Khi resize, nhiều thread cùng chuyển bin sang bảng mới. **Từng thao tác là thread-safe, nhưng ghép hai thao tác (`get` rồi `put`) thì không; dùng `compute`, `merge`, `computeIfAbsent`, và hàm truyền vào phải ngắn, không được sửa chính map đó.**

## Interview

Cấu trúc giống `HashMap`: mảng [[bucket|bin]], chuỗi node, chuỗi dài thì [[treeify|thành cây]] (xem bài HashMap Internals). Khác ở cách đồng bộ:
- **Đọc**: `get` đọc phần tử mảng bằng đọc volatile, duyệt chuỗi không khoá. Field `val` và `next` của node là `volatile`, nên thấy node là thấy giá trị đã ghi đầy đủ.
- **Ghi vào bin trống**: một lần CAS đặt node mới, không khoá.
- **Ghi vào bin có node**: `synchronized` trên node đầu bin. Hai thread chỉ chặn nhau khi trúng cùng bin, nên độ song song bằng số bin.
- **Đếm**: `size()` cộng một `baseCount` với mảng ô đếm giống [[long-adder|LongAdder]], nên là xấp xỉ khi đang có ghi đồng thời.

Java 7 thì khác: map chia thành các `Segment` (mặc định 16, theo `concurrencyLevel`), mỗi segment là một `ReentrantLock` riêng, nên số thread ghi song song tối đa bằng số segment. Java 8 bỏ segment; tham số `concurrencyLevel` trong constructor chỉ còn dùng để ước kích thước.

**Resize đồng thời**: khi `size` đạt 0.75 × số bin, một thread tạo bảng gấp đôi và chuyển từng đoạn bin. Bin đã chuyển được thay bằng một [[forwarding-node]]. Thread khác `put` trúng bin đã chuyển, hoặc `put` thêm key mới trong lúc đang resize, sẽ vào giúp chuyển đoạn tiếp theo; `get` trúng bin đó thì đi tìm ở bảng mới, không phải chờ.

Bẫy hay gặp:
- `if (!map.containsKey(k)) map.put(k, v)` hay `map.put(k, map.get(k) + 1)` là [[check-then-act]], mất cập nhật. Dùng `putIfAbsent`, `merge(k, 1, Integer::sum)`, `compute`.
- Hàm trong `compute*` chạy trong lúc giữ khoá bin: gọi database hay HTTP trong đó làm mọi thread trúng bin đó chờ theo.
- Key và value `null` bị cấm: `get` trả `null` phải có nghĩa duy nhất là "không có".

Iterator là [[weakly-consistent]]: không ném `ConcurrentModificationException`, có thể thấy hoặc không thấy thay đổi đang diễn ra.

## Deep

- **Các giá trị hash đặc biệt**: hash của key được trộn bằng `(h ^ (h >>> 16)) & 0x7fffffff`, luôn không âm, vì các hash âm dành cho node đặc biệt: `MOVED = -1` (forwarding node), `TREEBIN = -2` (node `TreeBin` bọc cây), `RESERVED = -3` (node giữ chỗ của `computeIfAbsent`/`compute` trên bin trống). Thấy hash âm ở đầu bin là biết phải đi đường riêng.
- **`sizeCtl`**: một biến `int` volatile mang nhiều nghĩa. `-1` là đang khởi tạo bảng (bảng tạo lười ở lần `put` đầu). Âm khác là đang resize: 16 bit cao là "resize stamp" theo kích thước bảng, 16 bit thấp là 1 + số thread đang chuyển. Dương là ngưỡng resize tiếp theo, `0.75 × n`.
- **Chia việc khi resize**: mỗi thread nhận một đoạn bin bằng CAS trên `transferIndex`, đi từ cuối bảng về đầu. Kích thước đoạn là `max((n >>> 3) / NCPU, 16)` trên máy nhiều CPU (máy một CPU thì cả bảng là một đoạn), nên bảng 16 bin chỉ có một đoạn và một thread làm, bảng lớn mới chia cho nhiều thread. Mỗi bin được khoá node đầu rồi tách thành hai danh sách ở `i` và `i + n` (cùng mẹo bit `hash & n` như `HashMap`). Thread xong cuối cùng quét lại toàn bảng rồi mới gán `table = nextTable`.
- **`put` trúng bin chưa chuyển** trong lúc resize vẫn ghi vào bảng cũ dưới khoá bin; lúc thread resize tới bin đó, nó phải chờ khoá nên không mất dữ liệu.
- **Tree bin**: bin vượt 8 node (bảng ≥ 64 bin) đổi thành `TreeBin`. `TreeBin` có khoá đọc-ghi nhẹ riêng: đang có thread ghi thì `get` duyệt danh sách liên kết song song thay vì chờ cây, nên đọc vẫn không bị chặn.
- **`computeIfAbsent` không được đệ quy**: hàm chạy trong lúc giữ bin (bin trống thì giữ bằng `ReservationNode`). Nếu hàm gọi lại `computeIfAbsent` trên một key rơi vào **cùng bin**, Java 9+ ném `IllegalStateException: Recursive update`; Java 8 có thể quay vòng vô hạn ở 100% CPU (JDK-8062841). Key rơi vào bin khác thì chạy được, nhưng đó là giữ hai khoá lồng nhau: hai thread lồng theo thứ tự ngược nhau có thể [[deadlock]]. Javadoc (Java 9+) ghi rõ hàm "must not modify this map during computation".
- **Chi phí của `computeIfAbsent` khi key đã có**: Java 8 luôn khoá bin kể cả khi key có sẵn, nên cache nóng gọi `computeIfAbsent` liên tục bị tranh khoá. Java 9 (JDK-8161372) thêm bước kiểm tra node đầu bin trước khi khoá; key không nằm ở đầu bin (sau trong chuỗi hoặc trong `TreeBin`) vẫn phải khoá. Trên Java 8, mẫu `V v = map.get(k); if (v == null) v = map.computeIfAbsent(k, f);` tránh được.
- **Hot key**: mọi lần ghi cùng một key đều tuần tự trên một bin. Counter theo key nên dùng `map.computeIfAbsent(k, x -> new LongAdder()).increment()` thay vì `merge(k, 1L, Long::sum)`.
- **Thao tác gộp không atomic**: `putAll`, `clear` làm từng phần; thread khác có thể thấy map đang dở. `size()` và `isEmpty()` chỉ là ảnh chụp gần đúng; số phần tử có thể vượt `Integer.MAX_VALUE` thì dùng `mappingCount()`.
- **Bulk operation** (Java 8): `forEach`, `search`, `reduce` nhận `parallelismThreshold`; số phần tử vượt ngưỡng thì chạy song song trên `ForkJoinPool.commonPool()`. Đặt `Long.MAX_VALUE` để chạy tuần tự.
- **Lựa chọn khác**: `Collections.synchronizedMap` và `Hashtable` khoá cả map, duyệt phải tự khoá; cần key có thứ tự thì `ConcurrentSkipListMap`; cần `Set` đồng thời thì `ConcurrentHashMap.newKeySet()`. Cache có giới hạn kích thước và hết hạn thì dùng thư viện (Caffeine), vì `ConcurrentHashMap` không tự xoá gì và lớn dần tới hết heap.
