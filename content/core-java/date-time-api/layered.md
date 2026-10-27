## Quick

`java.time` (Java 8, JSR 310) thay `Date`/`Calendar`: mọi class đều **bất biến và [[thread-safe]]**, mỗi class biểu diễn đúng một khái niệm. **Chọn class theo ý nghĩa dữ liệu**: `Instant` cho thời điểm đã xảy ra, `LocalDate` cho ngày không gắn giờ, `ZonedDateTime` khi cần tính theo lịch của một nơi. Khái niệm [[utc|UTC]], [[time-zone|múi giờ]], [[dst|DST]] xem bài Thời gian & mã hoá ký tự.

## Interview

Các class chính và khi nào dùng:

- `Instant`: điểm trên trục thời gian, dùng cho `createdAt`, log, sự kiện.
- `LocalDate`: ngày sinh, ngày hiệu lực hợp đồng, ngày lễ. Không có giờ nên không lệch múi giờ.
- `LocalTime`, `LocalDateTime`: giờ mở cửa, lịch hẹn chưa gắn nơi chốn.
- `ZonedDateTime`: tính toán theo lịch của một zone ID (cộng ngày qua DST, "9h sáng mỗi thứ Hai ở New York").
- `OffsetDateTime`: thời điểm kèm offset cố định, hợp với [[iso-8601|ISO 8601]] trong API và cột `timestamptz`.

`Duration` đo bằng giây và nano (`PT24H`), dùng với `Instant` và giờ; `Period` đo bằng năm, tháng, ngày theo lịch (`P1D`), dùng với `LocalDate`. Dùng sai cặp chỉ lỗi lúc chạy: `Instant.plus(1, ChronoUnit.MONTHS)` và `Duration.between` hai `LocalDate` đều ném `UnsupportedTemporalTypeException`. Khác biệt của hai loại khi cộng qua đêm chuyển giờ ở bài Thời gian & mã hoá ký tự.

Bẫy hay gặp:

- **Quên gán kết quả**: `date.plusDays(1);` không đổi `date`, vì object bất biến; phải viết `date = date.plusDays(1)`.
- **Cộng tháng ở cuối tháng**: `2026-01-31` cộng một tháng ra `2026-02-28`; cộng tiếp một tháng ra `2026-03-28`, còn cộng thẳng hai tháng ra `2026-03-31`. Kỳ thanh toán hàng tháng phải tính từ ngày gốc, không cộng dồn.
- **`Period.between` trả `P2M5D`**, không phải tổng số ngày; muốn số ngày dùng `ChronoUnit.DAYS.between` (64 ngày).
- **`SimpleDateFormat` dùng chung** giữa nhiều thread cho ngày sai hoặc ngoại lệ vô lý. `DateTimeFormatter` thì bất biến, khai báo `static final` được.
- **`LocalDate.now()` không truyền zone** lấy múi giờ mặc định của JVM: máy UTC và máy giờ Việt Nam cho "hôm nay" khác nhau từ 0h tới 7h sáng. Truyền `Clock` hoặc `ZoneId` rõ ràng.

Cách làm đúng: `Instant` hoặc `OffsetDateTime` ở biên lưu trữ và API, `LocalDate` cho dữ liệu chỉ có ngày, chỉ chuyển sang `ZonedDateTime` với zone ID rõ ràng khi hiển thị hoặc tính theo lịch.

## Deep

- **Pattern `yyyy` và `uuuu`**: `y` là year-of-era, `u` là năm tuyệt đối. Với `ResolverStyle.STRICT`, `dd/MM/yyyy` không parse được `15/03/2026` vì thiếu era (`Unable to obtain LocalDate from TemporalAccessor`); dùng `uuuu`. Còn `YYYY` là năm theo tuần, sai vào cuối tháng 12 (bài Thời gian & mã hoá ký tự).
- **Formatter có sẵn**: `DateTimeFormatter.ISO_INSTANT`, `ISO_OFFSET_DATE_TIME`, `ISO_LOCAL_DATE` khớp ISO 8601 và không phụ thuộc locale. Pattern có tên tháng hay thứ (`MMM`, `EEE`) phụ thuộc locale; luôn truyền `Locale` rõ ràng khi format cho máy đọc.
- **Độ chính xác**: `Instant.now()` chỉ có mili giây ở Java 8; từ Java 9 tuỳ OS có tới micro hoặc nano giây (Linux lên nano từ JDK 15). Trên JDK 27 macOS là micro giây (`...29.199729Z`). PostgreSQL lưu micro giây, MySQL `DATETIME` mặc định chỉ tới giây (`DATETIME(6)` mới có micro) và **làm tròn** chứ không cắt, nên 23:59:59.7 thành 0h ngày hôm sau. Test so `equals` giữa object trước và sau khi lưu có thể trượt; cắt bớt bằng `truncatedTo(ChronoUnit.MICROS)`.
- **Chuyển đổi với API cũ**: `date.toInstant()`, `Date.from(instant)`, `timestamp.toLocalDateTime()`, `Timestamp.valueOf(localDateTime)`. `java.sql.Timestamp.valueOf(LocalDateTime)` diễn giải theo múi giờ mặc định của JVM: cùng code chạy ở máy `Asia/Ho_Chi_Minh` và máy UTC cho `Instant` lệch 7 giờ.
- **JDBC 4.2** chuẩn hoá `LocalDate` (DATE), `LocalTime`, `LocalDateTime` (TIMESTAMP) và `OffsetDateTime` (TIMESTAMP WITH TIME ZONE) qua `setObject`/`getObject(col, X.class)`. `Instant` và `ZonedDateTime` không nằm trong bảng ánh xạ chuẩn nên driver hỗ trợ không đồng đều; Hibernate (5.2+) ánh xạ được `Instant`. Đặt `hibernate.jdbc.time_zone=UTC` để Hibernate không phụ thuộc múi giờ JVM khi đọc ghi cột không có múi giờ; ở Hibernate 6.2+ cách lưu offset của `OffsetDateTime`/`ZonedDateTime` còn do `hibernate.timezone.default_storage` quyết định.
- **`LocalDateTime` cho thời điểm là sai kiểu**: cột `created_at` kiểu `LocalDateTime` mất thông tin múi giờ; hai service ở hai region ghi vào cùng bảng sẽ không so sánh được. Dùng `Instant`/`OffsetDateTime` với `timestamptz`.
- **Jackson**: Jackson 2 cần module `JavaTimeModule` và tắt `WRITE_DATES_AS_TIMESTAMPS` để ra chuỗi ISO thay vì mảng số; Spring Boot (2.x, 3.x) tự đăng ký module và tắt sẵn cờ này. Chi tiết ở bài JSON & Jackson.
- **Dữ liệu ngày không hợp lệ**: `LocalDate.parse("2026-02-30")` ném `DateTimeParseException: Invalid date 'FEBRUARY 30'`; nhưng formatter tự tạo với resolver mặc định `SMART` sẽ lặng lẽ kéo `31/02` về `28/02`. `SimpleDateFormat` mặc định lenient còn tệ hơn: `2026-02-30` thành 2/3/2026.
- **`ChronoUnit.between` cắt phần lẻ**: `HOURS.between(9:59, 10:58)` là 0. Tính phí theo giờ bắt đầu thì làm tròn lên rõ ràng.
- **Đo thời gian chạy** dùng `System.nanoTime()`, không dùng `Instant.now()`, vì đồng hồ hệ thống có thể nhảy khi NTP chỉnh (xem bài Đồng hồ, thứ tự & sinh ID).
