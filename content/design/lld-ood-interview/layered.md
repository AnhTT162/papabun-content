## Quick

Bài [[low-level-design|low-level design]] (OOD) kiểm tra cách bạn biến yêu cầu mơ hồ thành **class có trách nhiệm rõ, interface ở đúng chỗ thay đổi, và code đúng khi nhiều thread cùng chạy**. Đi theo thứ tự: hỏi rõ yêu cầu, tìm thực thể và trách nhiệm, vẽ class và interface, rồi viết phần lõi. **Chỉ dùng pattern ở chỗ có lực thay đổi thật**, và nói ra trade-off.

## Interview

**Khung 45 phút**:
1. *Làm rõ yêu cầu (5 phút)*: phạm vi, quy mô, thứ gì sẽ thay đổi. Bãi đỗ xe: mấy tầng, mấy loại xe, tính tiền theo giờ hay theo lượt, nhiều cổng vào cùng lúc không?
2. *Thực thể và trách nhiệm (10 phút)*: danh từ thành ứng viên class (`ParkingLot`, `Floor`, `Spot`, `Ticket`, `Vehicle`), động từ thành method. Mỗi class trả lời được "nó chịu trách nhiệm gì".
3. *Class và interface (10 phút)*: interface đặt ở chỗ đã biết sẽ thay đổi: `PricingPolicy` (giá đổi theo mùa), `SpotAllocator` (gần thang máy hay lấp đầy từng tầng).
4. *Code phần lõi (15 phút)*: luồng chính `park()` / `leave()`, có xử lý lỗi.
5. *Mở rộng và đồng thời (5 phút)*: nhiều cổng, thêm loại xe, chạy nhiều instance.

**Ba bài kinh điển và ý người phỏng vấn tìm**:
- **Parking lot**: loại xe là dữ liệu (`enum VehicleSize`), không phải cây kế thừa `Car extends Vehicle` không có hành vi khác nhau. Giá là Strategy. Cấp chỗ phải **atomic**: hai cổng không được nhận cùng một chỗ.
- **[[lru|LRU]] cache**: `HashMap` cộng danh sách liên kết đôi cho `get`/`put` O(1), hoặc `LinkedHashMap(capacity, 0.75f, true)` với `removeEldestEntry`. Hỏi tiếp về thread-safety và [[ttl|TTL]].
- **Elevator**: trạng thái thang (`IDLE`, `MOVING_UP`, `DOOR_OPEN`) là State; thuật toán chọn thang và thứ tự phục vụ (SCAN/LOOK, đi hết một chiều rồi quay lại) là Strategy để thay được.

**Bẫy hay gặp**: nhảy vào code ngay; một class `ParkingLot` làm mọi thứ; nhồi pattern để "trông có thiết kế"; quên đồng thời; dùng `double` cho tiền.

## Deep

- **[[check-then-act|Check-then-act]] khi cấp chỗ**: `if (spot.isFree()) spot.occupy(ticket)` từ hai thread là [[race-condition|race condition]]. Trong một JVM: `AtomicReference<Ticket>` với `compareAndSet(null, ticket)` ([[cas|CAS]]), hoặc một `BlockingQueue<Spot>` chỗ trống cho mỗi loại. Nhiều instance: chốt ở database (`update spots set ticket_id = ? where id = ? and ticket_id is null` kiểm tra số dòng đổi) hoặc Redis `SET NX`. Nói được bước chuyển từ một máy sang nhiều máy là điểm cộng lớn.
- **`LinkedHashMap` thứ tự truy cập**: cờ `accessOrder = true` làm `get` **đổi cấu trúc** (chuyển entry về cuối danh sách). Hệ quả: duyệt `keySet()` mà gọi `get` là `ConcurrentModificationException`; và bảo vệ bằng read lock của `ReadWriteLock` là sai, vì `get` cũng cần khoá ghi. Bọc bằng `Collections.synchronizedMap` (duyệt view như `keySet()` vẫn phải tự `synchronized (map)`) hoặc `synchronized` cả `get` lẫn `put`. Production thì dùng [[caffeine|Caffeine]]: đồng thời tốt và có TTL; thay vì LRU thuần, nó dùng W-TinyLFU, cho hit rate tốt hơn khi gặp truy cập quét một lần.
- **LRU không dùng `LinkedHashMap`**: người phỏng vấn hay yêu cầu tự viết. `HashMap<K, Node>` cộng danh sách liên kết đôi có hai node canh (sentinel) `head` và `tail` để không phải xử lý `null` ở hai đầu; `get` chuyển node về đầu, `put` thêm ở đầu và bỏ node trước `tail` khi vượt dung lượng. Node phải lưu cả key, để khi bỏ node cuối còn xoá được nó khỏi map. TTL: lưu `expiresAt` trong node, xoá lười khi `get` gặp entry hết hạn, cộng một lần dọn định kỳ; hoặc dùng `expireAfterWrite` của Caffeine.
- **Tiền và thời gian**: tiền là `BigDecimal` hoặc `long` đơn vị nhỏ nhất (đồng, cent), kèm quy tắc làm tròn rõ ràng. Thời gian lấy từ `Clock` được inject, để test được "đỗ 2 giờ 59 phút" mà không phải chờ. Thời lượng tính bằng `Duration.between(entry, exit)`.
- **Kế thừa hay dữ liệu**: chỉ tạo lớp con khi hành vi khác nhau. `Motorbike`, `Car`, `Truck` chỉ khác kích thước thì một `enum` kèm thuộc tính là đủ, và thêm loại xe không cần class mới. Xem bài Coupling, cohesion (composition over inheritance).
- **Mở rộng dần**: thiết kế cho yêu cầu hiện tại, chỉ đặt interface ở 1–2 chỗ đã biết sẽ đổi. Khi người phỏng vấn thêm yêu cầu ("thêm xe điện cần chỗ có sạc"), chỉ ra thiết kế đổi ở đâu: `SpotAllocator` lọc theo `features`, không phải sửa `ParkingLot`.
- **Elevator sâu hơn**: tách bộ điều phối (dispatcher, chọn thang cho một lời gọi) khỏi từng thang (xử lý hàng đợi tầng của nó). Mỗi thang có thể chạy trên một thread hoặc vòng lặp sự kiện; giao tiếp qua hàng đợi thay vì khoá chung. Bàn về [[starvation|starvation]]: tầng ít người gọi vẫn phải được phục vụ trong thời gian giới hạn.
- **Kiểm thử thiết kế**: đề xuất vài unit test quan trọng (hết chỗ, trả vé hai lần, tính tiền qua nửa đêm) cho thấy bạn nghĩ tới edge case mà không cần viết hết.
- **LLD khác HLD**: low-level design dừng ở class, interface và đồng thời trong một service. Khi câu hỏi chuyển sang nhiều service, database, cache, đó là system design (track System Design).
