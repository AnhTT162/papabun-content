## Quick

Bộ nhớ là một chuỗi tầng, mỗi tầng chậm hơn tầng trước từ vài lần tới hàng trăm lần: [[cpu-cache|cache L1]] khoảng 1 ns, RAM khoảng 100 ns, SSD khoảng 100 µs, một vòng mạng trong datacenter khoảng 0,5 ms, sang region khác hàng chục tới hàng trăm ms. **Hiệu năng phụ thuộc vào số lần phải đi xuống tầng chậm hơn là số phép tính: đọc liền nhau, gom thao tác lại, và đừng gọi qua mạng trong vòng lặp.**

## Interview

Tôi nhớ các [[latency-numbers|latency numbers]] theo bậc độ lớn, không theo số chính xác:

| Thao tác | Cỡ |
|---|---|
| Đọc L1 | ~1 ns |
| Đọc L2 / L3 | ~4 ns / 10–40 ns |
| Đọc RAM | ~100 ns |
| Đọc ngẫu nhiên 4 KB từ NVMe SSD | 20–100 µs |
| Vòng mạng cùng datacenter | 0,1–0,5 ms |
| Đọc ngẫu nhiên trên ổ cứng HDD | 5–10 ms |
| Hà Nội ↔ Singapore | ~40 ms |

Phóng to cho dễ nhớ: nếu L1 là 1 giây thì RAM là gần 2 phút, SSD là hơn một ngày, một vòng mạng trong datacenter là gần một tuần.

**Cơ chế**: CPU không đọc từng byte từ RAM. Nó nạp cả một [[cache-line|cache line]] (64 byte trên x86, 128 byte trên Apple Silicon), và [[hardware-prefetch|bộ prefetch]] thấy bạn đọc tuần tự thì nạp trước line tiếp theo. Vì vậy mảng `int[]` duyệt tuần tự nhanh hơn nhiều so với đi theo con trỏ như `LinkedList`, dù cả hai đều O(n). Đây là [[cache-locality|cache locality]].

**Bẫy hay gặp**:
- Duyệt mảng hai chiều theo cột: mỗi phần tử nằm trên một line khác.
- Nhiều thread ghi các biến khác nhau nằm chung một cache line: [[false-sharing|false sharing]].
- Ở tầng hệ thống, sai lầm đắt nhất là coi lời gọi mạng như lời gọi hàm. 200 query trong vòng lặp, mỗi query 0,5 ms, là 100 ms chỉ để chờ mạng, trong khi xử lý trên CPU chỉ vài micro giây.

**Cách làm đúng**: chọn cấu trúc dữ liệu liền mạch (mảng, `ArrayList`) cho đường nóng; gom thao tác I/O thành batch; đặt các service gọi nhau đồng bộ trong cùng region; và khi tối ưu thì đo bằng JMH hoặc profiler, không đoán.

## Deep

- **Đo trên JDK 27, Apple M4** (lấy lần nhanh nhất trong 7 lần chạy, chỉ để thấy bậc độ lớn):
  - Cộng mảng `int[4096][4096]` theo hàng mất 3 ms, theo cột mất 45 ms, chậm gấp 15 lần.
  - Đọc mảng 128 MB theo chỉ số ngẫu nhiên chậm khoảng 12 lần so với tuần tự.
  - Cộng 5 triệu phần tử: `ArrayList<Integer>` 2 ms, `LinkedList<Integer>` 15 ms. Danh sách vừa được tạo tuần tự nên node vẫn nằm khá gần nhau (JVM cấp bộ nhớ liên tiếp trong TLAB); chênh lệch đến từ node to hơn (mỗi node 24 byte cộng `Integer` 16 byte) và chuỗi phụ thuộc: phải đọc xong node này mới biết địa chỉ node sau. Sau nhiều lần thêm xoá và GC, node rải rác hơn và chênh lệch còn lớn hơn.

  Trên x86 với cache nhỏ hơn, chênh lệch thường còn lớn hơn.
- **Mảng hai chiều của Java là mảng của mảng**: `int[][]` là một mảng tham chiếu, mỗi hàng là một object riêng. Hàng thì liền mạch, nhưng hai hàng không chắc nằm cạnh nhau. Ma trận lớn cần tốc độ thì dùng một mảng `int[rows * cols]` và tự tính chỉ số `i * cols + j`.
- **Boxing phá locality**: `Integer[]` hay `List<Integer>` lưu tham chiếu, mỗi `Integer` là một object 16 byte nằm ở chỗ khác trên heap. Mảng `int[]` thì giá trị nằm liền nhau. JDK 27 bật mặc định compact [[object-header|object header]] (header 8 byte thay vì 12; ở JDK 25, JEP 519, vẫn phải bật `-XX:+UseCompactObjectHeaders`), làm object nhỏ hơn, nhưng không gộp được giá trị vào mảng. Gộp như vậy cần value class của Project Valhalla, chưa có trong JDK 27.
- **Cache hierarchy**: L1 (thường 32–64 KB dữ liệu) và L2 riêng từng core; L3 dùng chung cho nhiều core (vài MB tới hàng trăm MB trên server). Kiểm trên Linux bằng `lscpu` hoặc `getconf -a | grep CACHE`, trên macOS bằng `sysctl hw.cachelinesize hw.l1dcachesize`.
- **Bộ prefetch cần mẫu truy cập đoán được**: tuần tự hoặc bước đều. Đi theo con trỏ (`LinkedList`, `TreeMap`, chuỗi node trong bucket của `HashMap`) thì mỗi bước phải chờ địa chỉ của bước trước, CPU không gửi được nhiều lần đọc cùng lúc như khi duyệt mảng.
- **[[branch-prediction|Branch prediction]]**: CPU đoán nhánh của `if` để chạy trước. Cùng vòng lặp `if (v >= 128) sum += v` trên 1 triệu số ngẫu nhiên trong khoảng 0..255 (`nextInt(256)`, nên nhánh đúng sai cỡ một nửa), mảng đã sắp xếp chạy nhanh khoảng 8 lần (đo trên JDK 27, M4) vì nhánh dễ đoán. JIT đôi khi đổi nhánh thành lệnh chọn không rẽ nhánh (`cmov`, `csel`) và chênh lệch biến mất: lý do microbenchmark phải chạy bằng JMH và xem kết quả trên đúng phần cứng.
- **[[tlb|TLB]] và huge page**: mỗi địa chỉ ảo phải được dịch sang địa chỉ vật lý; TLB cache các bản dịch đó theo page (4 KB mặc định trên Linux x86, 16 KB trên macOS Apple Silicon). Heap hàng chục GB truy cập ngẫu nhiên làm TLB miss nhiều; `-XX:+UseTransparentHugePages` hoặc `-XX:+UseLargePages` dùng page 2 MB để giảm. Virtual memory và page cache ở bài Process, thread & bộ nhớ của hệ điều hành.
- **[[numa|NUMA]]**: server nhiều socket có RAM gắn với từng socket; đọc RAM của socket kia chậm hơn đáng kể. `-XX:+UseNUMA` cho Parallel GC, và G1 từ JDK 14 (JEP 345), cấp vùng nhớ gần với thread đang chạy. Máy ảo cloud nhỏ thường chỉ có một node NUMA.
- **[[latency|Latency]] và bandwidth ([[throughput]] tối đa của một kênh) là hai thứ khác nhau**: đọc tuần tự 1 MB từ RAM mất vài chục µs, từ NVMe vài trăm µs, qua mạng 10 Gbit/s khoảng 0,8 ms. Một ổ trả mỗi lần đọc 100 µs mà chỉ đọc lần lượt từng cái thì tối đa 10.000 [[iops|IOPS]]; muốn hơn phải có nhiều request song song (queue depth). EBS gp3 cho mặc định 3.000 IOPS và 125 MB/s, mua thêm thì cao hơn.
- **Mạng bị giới hạn bởi tốc độ ánh sáng**: trong cáp quang khoảng 200 km mỗi ms, nên đi Hà Nội tới Singapore và quay về không thể dưới khoảng 20 ms, thực tế khoảng 40 ms. Gọi chéo AZ thường thêm dưới vài ms mỗi vòng so với cùng AZ, tuỳ cloud và region. Cache hay tối ưu code không xoá được chi phí đó; chỉ có giảm số vòng hoặc đặt dữ liệu gần người dùng.
- **Dùng con số để ước lượng**: ước lượng nhanh dung lượng, QPS và số máy ở bài Back-of-the-envelope; false sharing và `@Contended` ở bài Atomic, CAS & LongAdder.
