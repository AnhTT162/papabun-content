## Quick

Bộ nhớ tăng dần kết thúc theo hai cách rất khác nhau: [[out-of-memory-error|`OutOfMemoryError`]] do JVM tự ném (có stack trace, có [[heap-dump|heap dump]] nếu bật), và [[oomkilled|OOMKilled]] khi kernel giết process vì container vượt memory limit (exit code 137, không log, không dump). **Việc đầu tiên là xác định bộ nhớ tăng ở đâu: so heap sau GC với [[rss|RSS]] của process.** Heap sau GC tăng dần là [[memory-leak|leak]] trong heap, cần heap dump; heap phẳng mà RSS vẫn tăng là bộ nhớ native, cần [[native-memory-tracking|NMT]].

## Interview

**Hai kiểu chết**: thông điệp của `OutOfMemoryError` cho biết vùng nào hết: `Java heap space`, `GC overhead limit exceeded`, `Metaspace`, `Cannot reserve ... bytes of direct buffer memory`, `unable to create native thread`. OOMKilled thì xem `kubectl describe pod`: `Reason: OOMKilled`, `Exit Code: 137` (128 + SIGKILL). JVM bị giết ngay lập tức nên `-XX:+HeapDumpOnOutOfMemoryError` không có cơ hội chạy.

**Ngân sách của container**: RSS = heap + [[metaspace|metaspace]] + code cache + stack của thread + cấu trúc của GC + [[direct-buffer|direct buffer]] + malloc của thư viện native. `-XX:MaxRAMPercentage` mặc định chỉ 25%; container chỉ chạy JVM thường đặt 70–75%, phần còn lại dành cho native. Đẩy heap sát limit là cách nhanh nhất để bị OOMKilled.

**Điều tra**:
1. Nhìn heap **sau GC** (đáy của hình răng cưa), không nhìn heap used. Đáy tăng đều qua nhiều giờ là leak; đáy phẳng nhưng cao là heap thiếu hoặc cache quá lớn.
2. Leak trong heap: `jcmd <pid> GC.class_histogram` hai lần cách nhau vài phút để xem class nào tăng, rồi heap dump, mở bằng Eclipse MAT, xem [[dominator-tree|dominator tree]] theo [[retained-size|retained size]] và đường tới GC root.
3. Heap phẳng mà RSS tăng: bật `-XX:NativeMemoryTracking=summary`, chạy `jcmd <pid> VM.native_memory baseline`, vài giờ sau chạy `summary.diff`. Hạng mục tăng chỉ ra thủ phạm: `Thread` (rò thread), `Class` (rò classloader), `Other` (direct buffer, buffer tạm của NIO). Tổng của NMT thấp hơn RSS nhiều thì phần chênh là malloc nằm ngoài JVM.

**Nguyên nhân hay gặp**: `static Map` dùng làm cache không giới hạn, [[thread-local|ThreadLocal]] không dọn trong pool, hàng đợi không giới hạn, tag metric có [[metric-cardinality|cardinality]] cao, persistence context của Hibernate trong job batch, thread tạo ra mà không đóng.

**Phòng ngừa**: bật sẵn `-XX:+HeapDumpOnOutOfMemoryError` với `HeapDumpPath` trỏ vào volume và `-XX:+ExitOnOutOfMemoryError`; alert theo heap sau GC và theo RSS so với limit; mọi cache đều có giới hạn.

## Deep

- **Đọc thông điệp `OutOfMemoryError`**:
  - `Java heap space`: object còn sống vượt `-Xmx` (leak, hoặc một lần đọc quá nhiều dữ liệu như `findAll()` trên bảng lớn).
  - `GC overhead limit exceeded`: GC chạy gần như liên tục mà thu hồi rất ít; về bản chất cùng loại với heap space. Chủ yếu gặp với Parallel GC; với G1 thường gặp thẳng `Java heap space`.
  - `Metaspace`: quá nhiều class, thường là rò [[classloader|classloader]] khi redeploy trong app server hoặc sinh class động (proxy, script) không giới hạn. `MaxMetaspaceSize` mặc định không giới hạn, nên trong container thường thành OOMKilled thay vì lỗi này.
  - `Cannot reserve N bytes of direct buffer memory (allocated: ..., limit: ...)`: tổng `ByteBuffer.allocateDirect` chạm `-XX:MaxDirectMemorySize`, mặc định bằng `-Xmx`.
  - `unable to create native thread`: hết giới hạn số process/thread (`ulimit -u`, `pids.max` của container) hoặc hết bộ nhớ cho stack.
- **OOME của direct buffer do code Java ném, không phải JVM**: `-XX:+HeapDumpOnOutOfMemoryError` và `-XX:+ExitOnOutOfMemoryError` chỉ chạy khi chính JVM ném lỗi (heap, metaspace). Lỗi direct buffer từ `java.nio.Bits.reserveMemory` không tạo dump, không làm JVM thoát, và có thể bị một `catch (Throwable)` nuốt mất.
- **Thread nhận OOME chưa chắc là thủ phạm**: thread nào cấp phát đúng lúc heap đầy thì nhận lỗi. Sau OOME, một số thread đã chết giữa chừng, lock có thể chưa được trả, nên ứng dụng ở trạng thái không đáng tin; `ExitOnOutOfMemoryError` để Kubernetes khởi động lại sạch sẽ.
- **Heap dump**: kích thước gần bằng heap đang dùng, dừng ứng dụng vài giây tới vài chục giây và chứa dữ liệu cá nhân. Ghi vào PVC hoặc `emptyDir` trên đĩa: `emptyDir` với `medium: Memory` là tmpfs, tính vào memory limit của pod, nên ghi dump vào đó có thể chính là lý do bị OOMKilled. Cách lấy dump và các công cụ ở bài Bộ công cụ chẩn đoán JVM.
- **Đọc dump bằng MAT**: shallow size là kích thước của chính object; retained size là lượng bộ nhớ được giải phóng nếu object đó mất. Dominator tree xếp object theo retained size, nên một `HashMap` giữ 900 MB hiện ngay đầu dù chính nó chỉ vài chục byte. "Path to GC Roots" (loại trừ weak/soft reference) cho biết ai đang giữ nó: thường là một field `static`, một `ThreadLocal` của thread trong pool, hoặc một listener chưa huỷ đăng ký. Chi tiết các kiểu leak ở bài Memory leak & heap dump.
- **`GC.class_histogram` chạy [[full-gc|full GC]]** để chỉ đếm object còn sống (thêm `-all` để bỏ qua), nên nhẹ hơn heap dump nhưng vẫn dừng ứng dụng một lúc. So hai histogram: class nào tăng đều số instance là đầu mối.
- **RSS cao chưa chắc là leak**: G1 hiếm khi trả heap đã commit về cho hệ điều hành; nó chỉ thu nhỏ sau full GC hoặc khi bật `-XX:G1PeriodicGCInterval` (JDK 12, JEP 346). So `jvm.memory.used` với `jvm.memory.committed`: committed cao, used sau GC thấp là cấu hình, không phải rò.
- **Container và phiên bản JDK**: JVM đọc memory limit của cgroup từ JDK 10 (backport 8u191); cgroup v2 cần JDK 15+, hoặc 11.0.16+, 8u372+. JDK cũ hơn trên node dùng cgroup v2 thấy RAM của cả node, tính heap 25% của node và bị OOMKilled. Kiểm tra bằng `java -XshowSettings:system -version` trong container. Chi tiết ở bài JVM trong container.
- **Native: thread**: mỗi thread có stack riêng (`-Xss` mặc định 1 MB trên Linux x64, chỉ commit phần đã dùng). Tạo `Executors.newFixedThreadPool` trong mỗi request mà không `shutdown` làm số thread và hạng mục `Thread` trong NMT tăng mãi.
- **Native: buffer tạm của NIO**: ghi một heap `ByteBuffer` vào `FileChannel` hoặc `SocketChannel`, JDK chép nó sang một direct buffer tạm bằng đúng kích thước đó và **giữ lại trong cache của từng thread** (`sun.nio.ch.Util`). 200 thread Tomcat từng ghi 8 MB là 1,6 GB native. Khác biệt theo phiên bản: tới JDK 23 (kể cả 21), buffer tạm cấp bằng `ByteBuffer.allocateDirect`, nên nó hiện trong `jvm.buffer.memory.used{id=direct}` và bị `MaxDirectMemorySize` chặn (lỗi thành `Cannot reserve ...`). Từ JDK 24, JDK cấp bằng `Unsafe.allocateMemory`: không hiện trong metric direct, không bị giới hạn đó chặn, chỉ NMT thấy trong `Other`. `-Djdk.nio.maxCachedBufferSize=262144` bỏ cache cho buffer lớn hơn 256 KB; `Files.write` ghi theo từng khối 8 KB nên không bị.
- **Native ngoài tầm NMT**: NMT chỉ theo dõi bộ nhớ do JVM cấp, không thấy malloc của thư viện native (JNI, driver). glibc tạo nhiều malloc arena (tới 8 × số core) và phân mảnh, làm RSS lớn hơn tổng NMT. Cách giảm: `MALLOC_ARENA_MAX=2`, dùng jemalloc, hoặc `jcmd <pid> System.trim_native_heap` và `-XX:TrimNativeHeapInterval` (JDK 22+; một số bản cập nhật của 17 và 21 có backport).
- **NMT có giá**: phải bật lúc khởi động; mức `summary` tốn vài phần trăm hiệu năng, `detail` tốn nhiều hơn. Bật `summary` sẵn trên một pod canary là đủ để có dữ liệu khi cần.
- **Leak trong heap hay gặp ở ứng dụng Spring**: cache `ConcurrentHashMap` không giới hạn (dùng Caffeine có `maximumSize`); tag metric chứa `userId` hay URL có id làm Micrometer giữ hàng triệu meter (bài Metrics, tracing & SLO); `ThreadLocal` không `remove()` (bài ThreadLocal & ScopedValue); job batch đọc hàng triệu entity mà không `flush`/`clear` [[persistence-context|persistence context]]; hàng đợi của executor `@Async` mặc định không giới hạn (bài Request treo vì cạn thread).
