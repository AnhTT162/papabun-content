## Quick

Đa luồng có ba vấn đề tách biệt: [[atomicity]] (không bị chen giữa), [[visibility]] (thấy giá trị thread khác ghi) và ordering (không bị [[instruction-reordering|sắp xếp lại]]). **`synchronized` cho cả ba trong vùng được khoá; `volatile` chỉ cho visibility và ordering, nên `count++` trên biến `volatile` vẫn mất lần cộng.**

## Interview

[[jmm|Java Memory Model]] (JLS chương 17) không hứa rằng thread B thấy ngay giá trị thread A vừa ghi. Nó chỉ hứa khi hai thao tác có quan hệ [[happens-before]]. Không có quan hệ đó mà hai thread cùng truy cập một biến, ít nhất một bên ghi, là [[data-race]]: compiler, [[jit|JIT]] và CPU được phép giữ giá trị trong register hoặc đổi thứ tự lệnh.

Các quy tắc happens-before hay dùng:
- Trong một thread: lệnh trước happens-before lệnh sau (program order).
- **Unlock** một [[monitor]] happens-before mọi lần **lock** sau đó trên cùng monitor.
- **Ghi biến `volatile`** happens-before mọi lần **đọc** sau đó của chính biến đó.
- `thread.start()` happens-before mọi việc trong thread được start; mọi việc trong một thread happens-before khi `join()` trên thread đó trả về.
- Có tính bắc cầu: A trước B, B trước C thì A trước C.

**`synchronized`** cho loại trừ lẫn nhau (một thread trong vùng khoá) và cho happens-before giữa lần nhả khoá và lần lấy khoá sau. Nó là [[reentrancy|reentrant]]: thread đang giữ monitor vào lại được.

**`volatile`** bảo đảm mỗi lần đọc thấy lần ghi mới nhất, và mọi thứ thread A ghi **trước** khi ghi biến volatile đều hiện ra với thread B **sau** khi B đọc được giá trị đó. Hợp cho cờ dừng và công bố một object đã dựng xong.

Bẫy hay gặp:
- `volatile int count; count++` vẫn sai: `++` là đọc, cộng, ghi. Dùng `AtomicInteger` ([[cas|CAS]]), `LongAdder` khi nhiều thread cùng cộng, hoặc `synchronized`.
- Cờ dừng không `volatile`: JIT được phép đọc `running` một lần rồi quay mãi thành một vòng [[busy-spin]] đốt trọn một core.
- [[double-checked-locking|Double-checked locking]] thiếu `volatile` có thể trả về object chưa khởi tạo xong.

## Deep

- **Vì sao cờ dừng treo thật**: không có happens-before nên JIT được phép biến `while (running) { }` thành `if (running) while (true) { }`. Chạy thử trên HotSpot hiện đại, chương trình kiểu này thường treo vĩnh viễn sau khi JIT biên dịch vòng lặp. Thêm `println` vào vòng lặp đôi khi làm lỗi "biến mất" nhưng đó không phải đảm bảo.
- **Mô hình cache trong mô phỏng là đơn giản hoá**: JMM định nghĩa bằng happens-before, không nói về cache. Cache CPU thật được phần cứng giữ nhất quán (cache coherence); cái làm giá trị "kẹt" thường là register, store buffer và tối ưu của JIT. Kết luận thực hành vẫn giống nhau.
- **Ordering**: `data = 42; ready = true;` với `ready` không volatile thì thread khác có thể thấy `ready == true` mà `data` vẫn 0. Khai báo `ready` là `volatile` thì ghi `data` được "đẩy" theo: thấy `ready` là thấy `data`.
- **Double-checked locking**: `instance = new Singleton()` gồm cấp phát, chạy constructor và gán tham chiếu; thiếu `volatile`, thread khác có thể thấy tham chiếu trước khi constructor ghi xong field. Từ Java 5 (JSR-133), `volatile` sửa được. Cách gọn hơn: holder class (`static class Holder { static final Singleton INSTANCE = ... }`) hoặc `enum`.
- **Reentrancy**: method `synchronized` gọi method `synchronized` khác trên cùng object không tự deadlock; JVM đếm số lần vào và chỉ nhả monitor khi thoát hết. `ReentrantLock` cũng vậy (`getHoldCount()`).
- **Khoá trên object nào**: method instance khoá `this`, method `static` khoá object `Class`. Hai thread khoá hai object khác nhau thì không loại trừ nhau. Đừng khoá trên `String` literal hay `Integer` boxing vì chúng có thể được dùng chung ngoài ý muốn.
- **`AtomicInteger`** dùng CAS (`incrementAndGet` không khoá). Nhiều thread tranh cùng một biến thì CAS thất bại và thử lại nhiều. **`LongAdder`** (Java 8) chia thành nhiều ô cộng riêng rồi cộng dồn khi gọi `sum()`, nhanh hơn cho counter/metric nhưng `sum()` không phải ảnh chụp atomic, không dùng để cấp số thứ tự.
- **`long`/`double` không volatile** có thể bị ghi thành hai nửa 32 bit (JLS 17.7); khai báo `volatile` thì đọc/ghi atomic. JVM 64-bit thực tế thường không xé, nhưng spec không hứa.
- **Field `final`** được thấy đúng giá trị sau khi constructor xong, miễn là `this` không lọt ra ngoài trong lúc khởi tạo (JLS 17.5). Đây là lý do object [[immutable]] chia sẻ được mà không cần khoá.
- **Chi phí**: `volatile` chèn [[memory-barrier|memory barrier]]; trên x86, đọc volatile gần như rẻ như đọc thường, ghi volatile đắt hơn. `synchronized` không tranh chấp rất rẻ; chỉ khi tranh chấp, thread mới phải chờ và tốn chi phí chuyển ngữ cảnh.
