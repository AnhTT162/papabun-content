## Quick

Mọi lỗi là `Throwable`. `Error` (ví dụ `OutOfMemoryError`) là lỗi của JVM, gần như không nên bắt. `Exception` chia thành [[checked-exception|checked]] (compiler bắt khai báo hoặc xử lý) và [[unchecked-exception|unchecked]] (`RuntimeException`). Khi bọc lỗi sang loại khác, **luôn truyền exception gốc làm `cause`**, nếu không sẽ mất dấu nguyên nhân thật.

## Interview

Cây kế thừa:
- `Throwable`
  - `Error`: `OutOfMemoryError`, `StackOverflowError`. Ứng dụng thường không phục hồi được.
  - `Exception`
    - Checked: `IOException`, `SQLException`, `InterruptedException`. Phải `catch` hoặc khai báo `throws`.
    - `RuntimeException` (unchecked): `NullPointerException`, `IllegalArgumentException`, `IllegalStateException`.

Quy ước dùng: checked cho lỗi bên ngoài mà bên gọi có thể xử lý (file không có, mạng lỗi). Unchecked cho lỗi lập trình hoặc vi phạm điều kiện (tham số sai, trạng thái sai). Các framework hiện đại như Spring gần như chỉ dùng unchecked: `DataAccessException` bọc `SQLException`, để tầng trên không phải khai báo `throws` khắp nơi.

[[exception-chaining|Exception chaining]]: khi đổi loại lỗi giữa các tầng, dùng constructor có `cause`: `throw new OrderLoadException("Không tải được đơn " + id, e)`. Stack trace sẽ có phần `Caused by:` chỉ ra lỗi gốc. Bỏ mất `e` là lỗi phổ biến nhất khi debug production.

[[try-with-resources]] (Java 7) tự gọi `close()` cho mọi `AutoCloseable`, theo thứ tự ngược với lúc mở, và **trước** khi `catch`/`finally` chạy. Nếu thân `try` ném lỗi và `close()` cũng ném lỗi, lỗi của `close()` được gắn vào lỗi chính dưới dạng [[suppressed-exception|suppressed]] (`getSuppressed()`) thay vì đè mất lỗi chính.

Ba bẫy hay gặp:
- **`return` trong `finally`** nuốt mất exception đang bay. Đừng bao giờ `return` hay `throw` trong `finally`.
- **Log rồi ném lại** ở mọi tầng làm một lỗi in ra 5 lần. Mỗi lỗi chỉ nên log một lần, ở nơi xử lý nó (thường là handler chung như `@ControllerAdvice`).
- **Nuốt `InterruptedException`**: nếu không ném lại được thì gọi `Thread.currentThread().interrupt()` để giữ cờ [[thread-interrupt|interrupt]].

Với Spring, `@Transactional` mặc định chỉ rollback khi gặp `RuntimeException` hoặc `Error`. Method ném checked exception sẽ **commit** những gì đã ghi, trừ khi khai báo `rollbackFor = Exception.class`.

## Deep

- **Tạo exception tốn chi phí chủ yếu ở `fillInStackTrace()`**, vì phải duyệt toàn bộ stack. Không dùng exception để điều khiển luồng trong vòng lặp nóng. Với exception dùng lại nhiều lần, constructor `protected Throwable(message, cause, enableSuppression, writableStackTrace)` cho phép tắt stack trace.
- **[[fast-throw|OmitStackTraceInFastThrow]]**: khi một chỗ ném `NullPointerException`, `ArithmeticException` hay `ArrayIndexOutOfBoundsException` quá nhiều lần, [[jit|JIT]] của HotSpot thay bằng exception tạo sẵn **không có stack trace và message**. Log production lúc đó chỉ còn `java.lang.NullPointerException`. Tìm lại log cũ hơn để thấy stack trace đầy đủ, hoặc chạy với `-XX:-OmitStackTraceInFastThrow`.
- **Helpful NullPointerException** (JEP 358, bật mặc định từ Java 15): message chỉ rõ biến nào null, ví dụ `Cannot invoke "String.length()" because "user.name" is null`.
- **Lambda không ném được checked exception** vì `Function`, `Consumer` không khai báo `throws`. Bọc lại bằng `UncheckedIOException` (cho `IOException`) hoặc exception riêng, và đừng nuốt lỗi bằng `catch` rỗng.
- **Multi-catch** `catch (IOException | SQLException e)`: biến `e` là `final` ngầm định. Hai loại trong cùng một multi-catch không được có quan hệ cha–con.
- **`catch (Exception e)` cũng bắt cả `RuntimeException`**, kể cả lỗi lập trình. `catch (Throwable t)` còn bắt cả `OutOfMemoryError`; chỉ dùng ở biên ngoài cùng (vòng lặp của worker, handler cuối) để log rồi dừng có kiểm soát.
- **Exception trong `static` initializer** (không phải `Error`) được bọc thành `ExceptionInInitializerError`. Mọi lần dùng class sau đó ném `NoClassDefFoundError: Could not initialize class ...`. Trước Java 18, lỗi gốc chỉ thấy ở lần đầu. Từ Java 18, tên và message của lỗi gốc nằm trong `Caused by`, nhưng không có stack trace gốc. Vì vậy hãy tìm lần lỗi đầu tiên trong log.
- **Custom exception** nên mang dữ liệu để xử lý (mã lỗi, id) thay vì chỉ có message, và đặt tên theo vấn đề (`InsufficientBalanceException`), không theo tầng (`ServiceException`).
