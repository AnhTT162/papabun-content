## Quick

Stream là pipeline mô tả phép xử lý, không phải cấu trúc chứa dữ liệu. [[intermediate-operation|Thao tác trung gian]] (`filter`, `map`) chỉ dựng pipeline; khi gọi [[terminal-operation|thao tác kết thúc]] (`toList`, `count`, `findFirst`), từng phần tử mới chảy qua **toàn bộ pipeline lần lượt** ([[lazy-evaluation|lười]]). **Hàm truyền vào phải không có side effect và không phụ thuộc thứ tự**, nhất là khi chạy song song; một stream chỉ dùng được một lần.

## Interview

**Chạy theo từng phần tử**: `Stream.of("a","b","c").filter(...).map(...).findFirst()` chạy `filter a`, `map a` rồi dừng; `b` và `c` không bao giờ được xét. Pipeline không phải "lọc hết rồi map hết". Thao tác [[short-circuit|short-circuit]] (`findFirst`, `anyMatch`, `limit`, `takeWhile`) cho phép dừng sớm, kể cả với stream vô hạn (`Stream.iterate(1, x -> x * 2).limit(5)`).

**[[stateful-operation|Stateful]]**: `sorted` phải nhận mọi phần tử rồi mới chuyển tiếp, nên là rào chắn: sau nó không còn lười, và `sorted` trên stream vô hạn chạy tới `OutOfMemoryError`. `distinct` tuần tự vẫn lười (đẩy phần tử mới đi ngay) nhưng giữ một `HashSet` mọi phần tử đã gặp; song song có thứ tự thì phải đệm.

**[[collector|Collector]]** gom kết quả: `toMap`, `groupingBy`, `partitioningBy`, `joining`, `teeing` (12). Bẫy:

- `toMap` ném `IllegalStateException: Duplicate key` khi trùng key; truyền hàm gộp (`Long::sum`) và, nếu cần thứ tự, `TreeMap::new`. Value `null` thì NPE (bài Null & Optional).
- `groupingBy` mặc định trả `HashMap` không thứ tự; collector con (`counting`, `summingLong`, `mapping`) tránh tạo list trung gian.
- `Stream.toList()` (16) trả list **bất biến**; `Collectors.toList()` trả `ArrayList` sửa được nhưng không được hứa trong spec.

**[[parallel-stream|Parallel stream]]** chia nguồn bằng [[spliterator]] và chạy trên [[common-pool|ForkJoinPool common pool]]. Side effect vào collection thường (`forEach(list::add)`) mất phần tử hoặc ném `ArrayIndexOutOfBoundsException`; dùng collector. `reduce` với identity sai (`reduce(10, Integer::sum)`) cộng identity nhiều lần khi song song.

**Khi nào không dùng stream**: logic có nhiều nhánh, cần `break`/`continue` phức tạp, cần ném checked exception, hoặc cần chỉ số phần tử; vòng `for` rõ ràng hơn. Stream cũng có chi phí dựng pipeline và lambda; với vài phần tử trên đường nóng, `for` nhanh hơn.

Cách làm đúng: pipeline ngắn, hàm thuần; chọn collector đúng thay vì `forEach` ghi ra ngoài; dùng `IntStream`/`mapToLong` để tránh boxing khi tính tổng.

## Deep

- **Đã chạy JDK 27**: `findFirst` sau `filter`/`map` chỉ in `filter a`, `map a`. `Stream.of(1,2,3).peek(...).count()` không in gì vì từ Java 9 `count()` bỏ qua pipeline khi biết trước kích thước; thêm `filter` thì `peek` chạy. Gọi `count()` lần hai ném `stream has already been operated upon or closed`. `toMap` trùng key ném `Duplicate key an (attempted merging values 100 and 70)`.
- **Side effect song song (đã chạy)**: `IntStream.range(0, 100_000).parallel().forEach(list::add)` với `ArrayList` cho size 17.219, 8.316, 10.282 qua các lần chạy và có lần ném `ArrayIndexOutOfBoundsException`; `.boxed().toList()` luôn ra 100.000. `Stream.of(1,2,3,4).parallel().reduce(10, Integer::sum)` ra 50, tuần tự ra 20: identity phải là phần tử trung lập (0 cho cộng).
- **`peek` chỉ để debug**: tuỳ thao tác kết thúc mà nó có chạy hay không, nên đừng đặt logic nghiệp vụ trong `peek`.
- **Thứ tự**: `forEach` trên parallel stream không giữ thứ tự, `forEachOrdered` thì giữ nhưng mất phần lớn lợi ích song song. `findAny` nhanh hơn `findFirst` khi song song. Stream từ `HashSet` vốn không có thứ tự gặp.
- **Common pool**: song song mặc định bằng số core trừ một (máy 10 core: 9) cộng thread gọi; worker có tên `ForkJoinPool.commonPool-worker-N` và thread `main` cũng tham gia. Gọi I/O trong parallel stream làm nghẽn mọi parallel stream và `CompletableFuture` mặc định của cả JVM (bài ForkJoinPool).
- **Nguồn chia kém**: `LinkedList`, `Stream.iterate`, `BufferedReader.lines()` chia không đều, parallel ít lợi hoặc chậm hơn.
- **Stream từ tài nguyên phải đóng**: `Files.lines(path)` giữ file mở tới khi stream bị đóng; dùng try-with-resources. Stream của collection thì không cần.
- **`flatMap` và `mapMulti`** (16): `flatMap` tạo một stream con cho mỗi phần tử; `mapMulti` đẩy phần tử ra qua consumer, ít object hơn khi mỗi phần tử sinh 0–1 kết quả.
- **Gatherer** (Java 24, JEP 485): thao tác trung gian tự định nghĩa như cửa sổ trượt (`Gatherers.windowFixed(3)`), lấp chỗ trống trước đây phải dùng collector hay vòng lặp.
- **Debug pipeline dài**: stack trace có nhiều frame `java.util.stream`; tách lambda thành method có tên để stack trace và profiler đọc được.
