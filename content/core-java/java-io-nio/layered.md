## Quick

`java.io` có hai họ: **byte stream** (`InputStream`/`OutputStream`) cho dữ liệu nhị phân và **character stream** (`Reader`/`Writer`) cho văn bản, chuyển qua lại bằng một charset. Mỗi lần đọc ghi trực tiếp là một system call, nên **luôn có [[buffered-io|buffer]], luôn đóng tài nguyên bằng [[try-with-resources|try-with-resources]], luôn ghi rõ charset**. NIO (`java.nio`) thêm `Path`/`Files` tiện hơn, `Channel` + [[byte-buffer|`ByteBuffer`]] cho I/O theo khối, và các tối ưu như [[memory-mapped-file|mmap]], [[zero-copy|zero-copy]].

## Interview

**Buffer**: `FileInputStream.read()` không buffer gọi xuống OS cho **từng byte**. Đọc 10 MB như vậy mất 3.291 ms, bọc `BufferedInputStream` (buffer 8 KB) còn 43 ms, tự đọc vào mảng 8 KB còn 8 ms (đã chạy JDK 27). Ghi cũng vậy: `BufferedWriter` gom dữ liệu trong bộ nhớ và chỉ ghi xuống khi buffer đầy, khi `flush()` hoặc `close()`.

**Đóng tài nguyên**: không đóng writer thì phần còn trong buffer **mất luôn** khi process kết thúc; không đóng reader thì rò [[file-descriptor|file descriptor]] tới lúc `Too many open files`. Try-with-resources đóng theo thứ tự ngược và giữ exception bị che (`getSuppressed`). Đóng wrapper ngoài cùng là đủ, nó đóng cả stream bên trong.

**Charset**: `new FileReader(file)` trước Java 18 dùng charset mặc định của hệ điều hành; từ Java 18 mặc định UTF-8 (bài Thời gian & mã hoá ký tự). Ghi rõ `StandardCharsets.UTF_8`. Đọc bằng charset không chứa nổi chuỗi byte (UTF-8 đọc bằng `US_ASCII`) thì `Files.readAllLines` ném `MalformedInputException`; charset nhận mọi byte như `ISO_8859_1` thì không bao giờ lỗi mà ra chữ vỡ.

**`Files` API** (Java 7: `newBufferedReader`, `copy`, `move`; Java 8: `lines`, `walk`; Java 11: `readString`, `writeString`). Báo lỗi rõ hơn `java.io.File` (ném `NoSuchFileException`, `AccessDeniedException` thay vì trả `false`). `readAllBytes`/`readAllLines` nạp cả file vào heap; file lớn thì dùng `lines()` trong try-with-resources.

**NIO buffer và channel**: `ByteBuffer` có `position`, `limit`, `capacity`. Ghi vào buffer làm tăng `position`; trước khi đọc ra phải `flip()` (đặt `limit = position`, `position = 0`). Quên `flip` là lỗi kinh điển: đọc ra 0 byte hoặc rác. `FileChannel` đọc ghi theo khối, có `force()` ([[fsync]]), `transferTo` (zero-copy) và `map` (mmap).

**Ghi file an toàn**: ghi vào file tạm cùng thư mục rồi `Files.move(tmp, target, ATOMIC_MOVE)` ([[atomic-move|đổi tên nguyên tử]]), để người đọc không bao giờ thấy file ghi dở; muốn bền cả khi mất điện thì `force(true)` file tạm trước khi đổi tên.

## Deep

- **Đã chạy JDK 27 (lab)**: `BufferedWriter` từ `Files.newBufferedWriter` ghi 1.000 dòng (14.893 byte) rồi không đóng: trên đĩa 0 byte. 5.000 dòng: 65.536 byte, 4.166 dòng đủ và một dòng bị cắt giữa chừng. Gọi `close()` thì đủ 1.000 dòng.
- **Đóng không bằng bền**: `close()` đẩy dữ liệu xuống [[page-cache|page cache]] của OS, chưa chắc xuống đĩa. Dữ liệu không được mất khi mất điện (ledger, WAL) cần `FileChannel.force(true)` hoặc mở với `StandardOpenOption.DSYNC`; mỗi lần fsync tốn từ trăm micro giây tới vài mili giây tuỳ đĩa (page cache ở bài Process, thread & bộ nhớ của hệ điều hành).
- **`ATOMIC_MOVE`** chỉ nguyên tử trong cùng một filesystem; khác filesystem ném `AtomicMoveNotSupportedException`. Muốn bền cả thao tác đổi tên thì fsync cả thư mục chứa.
- **Path traversal (đã chạy)**: `Path.of("/data/uploads").resolve("../../etc/passwd").normalize()` ra `/etc/passwd`, `startsWith("/data/uploads")` là `false`. Kiểm sau `normalize()`, với `base` cũng đã `toAbsolutePath().normalize()`; `resolve("/etc/passwd")` với đường dẫn tuyệt đối bỏ luôn thư mục gốc. Symlink trong thư mục thì cần `toRealPath()`. Giải nén zip cũng phải kiểm như vậy (Zip Slip).
- **`Files.lines` và `Files.walk` giữ file/thư mục mở** cho tới khi stream bị đóng; dùng trong try-with-resources, nếu không sẽ rò file descriptor trong service chạy lâu.
- **[[direct-buffer|Direct buffer]]** (`allocateDirect`) nằm ngoài heap, tránh một lần chép khi I/O nhưng cấp phát chậm và chỉ được giải phóng khi object bị GC; giới hạn bởi `-XX:MaxDirectMemorySize`. Rò direct buffer là nguồn OOM ngoài heap (bài Bộ nhớ tăng dần & OOM).
- **mmap** (`FileChannel.map`): OS ánh xạ file vào bộ nhớ ảo, đọc như mảng, rất nhanh với truy cập ngẫu nhiên trên file lớn; nhưng (trước API FFM chính thức ở Java 22 với `Arena`) vùng map chỉ được gỡ khi GC dọn buffer, file đang map khó xoá trên Windows, và lỗi đĩa hiện ra thành `InternalError` khi truy cập. Kafka dùng mmap cho index, Lucene cho segment.
- **`transferTo`** dùng `sendfile` của Linux để chép từ file sang socket không qua user space; chi tiết cùng các mô hình I/O ở bài Mô hình I/O.
- **`File` và `Path`**: `File.delete()` trả `false` mà không nói lý do; `Files.delete` ném exception có nguyên nhân. `File.listFiles()` trả `null` khi lỗi. Code mới dùng `Path`/`Files`.
- **`WatchService`** theo dõi thay đổi thư mục; trên Linux dùng inotify. Độ trễ và độ đầy đủ của sự kiện khác nhau theo hệ điều hành, và không tin vào nó cho file trên ổ mạng.
- **`Scanner` chậm với file lớn**: `Scanner` dùng regex để tách token; với file vài trăm MB, `BufferedReader` + tự tách nhanh hơn nhiều lần.
