## Quick

[[flaky-test|Test chập chờn]] lúc xanh lúc đỏ với cùng một code. Nguyên nhân luôn là một thứ **không xác định** mà test vô tình phụ thuộc: giờ hệ thống và múi giờ, thứ tự chạy test, state dùng chung giữa các test, thứ tự duyệt `Set`/`Map`, chờ bằng `sleep`, cổng hay dịch vụ bên ngoài, và lịch xen kẽ giữa các thread. **Sửa bằng cách đưa thứ đó vào tầm kiểm soát của test** (tiêm `Clock`, cô lập dữ liệu, chờ theo điều kiện), không bằng cách chạy lại cho tới khi xanh.

## Interview

**Vì sao nghiêm trọng**: một suite có vài test chập chờn làm mọi người quen bấm "chạy lại". Từ đó, màu đỏ của bug thật cũng bị bỏ qua.

**Nguồn hay gặp và cách sửa**:
- **Thời gian**: `LocalDate.now()`, `Instant.now()`, múi giờ máy CI khác máy dev, nửa đêm, cuối tháng, DST. Tiêm [[clock|`Clock`]] vào code và dùng `Clock.fixed(...)` trong test; đặt `-Duser.timezone` cố định cho JVM test.
- **Thứ tự và state dùng chung**: field `static`, singleton, cache, dữ liệu database còn lại từ test trước. Test đúng khi chạy riêng nhưng sai khi chạy sau một test khác. Dọn state sau mỗi test, mỗi test tự tạo dữ liệu của nó.
- **Thứ tự duyệt**: `Set.of`, `Map.of` đổi thứ tự mỗi lần chạy JVM; assert theo thứ tự trên `HashMap` gắn với cài đặt của JDK. So sánh không theo thứ tự (`containsExactlyInAnyOrder`) hoặc sắp xếp trước.
- **Bất đồng bộ**: `Thread.sleep(500)` để "chờ xử lý xong". Chờ theo điều kiện với [[awaitility|Awaitility]]: `await().atMost(5, SECONDS).untilAsserted(...)`.
- **Môi trường**: cổng cố định đã bị chiếm, gọi dịch vụ thật qua mạng, locale làm dấu thập phân thành dấu phẩy. Cổng ngẫu nhiên, stub HTTP, locale cố định.
- **Đồng thời**: [[race-condition|race condition]] thật trong code; xem bài Kiểm thử code đồng thời.

**Quy trình**: phát hiện (rerun ghi nhận test "flake" thay vì giấu), [[test-quarantine|cách ly]] để không chặn merge, giao người sở hữu và hạn sửa, tái hiện bằng cách chạy lặp, đổi seed thứ tự, đổi múi giờ, rồi sửa nguyên nhân.

## Deep

- **Đo `Set.of` trên JDK 27**: in `Set.of("VIP", "NEW", "BLOCKED", "TRIAL")` ở năm lần chạy JVM cho bốn thứ tự khác nhau, ví dụ `[NEW, TRIAL, VIP, BLOCKED]` rồi `[BLOCKED, VIP, TRIAL, NEW]`; `Map.of` cũng vậy. Các collection bất biến này cố ý trộn thứ tự theo một salt ngẫu nhiên mỗi lần khởi động JVM. `HashSet` cùng phần tử in cùng một thứ tự ở cả năm lần, nhưng thứ tự đó vẫn là chi tiết cài đặt có thể đổi giữa các bản JDK.
- **Múi giờ, ví dụ cụ thể**: service tính "đơn hôm nay" theo `Asia/Ho_Chi_Minh` (UTC+7), test tạo đơn lúc `Instant.now()` rồi hỏi báo cáo cho `LocalDate.now()` theo múi giờ máy. Máy dev ở Việt Nam luôn xanh. CI chạy UTC: từ 17:00 tới 23:59 UTC, ngày ở Việt Nam đã sang hôm sau, test đỏ; tức khoảng 7/24 số lần chạy nếu lịch chạy đều trong ngày.
- **Tiêm `Clock` đúng cách**: bean `Clock` (`Clock.system(zone)` ở production), code dùng `LocalDate.now(clock)`, `Instant.now(clock)`; test dùng `Clock.fixed(Instant.parse("2026-11-02T17:00:00Z"), zone)` và viết thêm test ngay tại biên 16:59:59Z và 17:00:00Z. Với code cần thời gian trôi (timeout, TTL), dùng một `MutableClock` tự viết hoặc virtual time (`StepVerifier.withVirtualTime` cho Reactor).
- **Thứ tự chạy ngẫu nhiên để lộ phụ thuộc**: đặt `junit.jupiter.testmethod.order.default=org.junit.jupiter.api.MethodOrderer$Random` (và `junit.jupiter.testclass.order.default` cho class) cùng `junit.jupiter.execution.order.random.seed`. Seed sinh tự động không hiện ở log mặc định, nên đặt seed tường minh (ví dụ số build) để tái hiện được thứ tự gây lỗi.
- **Rerun để ghi nhận chứ không để che**: `-Dsurefire.rerunFailingTestsCount=2` chạy lại test đỏ; test xanh ở lần sau được đếm vào `Flakes: N` trong tổng kết và XML báo cáo, build vẫn xanh. Chỉ dùng kèm việc thu thập và xử lý danh sách flake; nếu không, đó chỉ là cách giấu.
- **Cách ly**: gắn `@Tag("quarantine")` và loại khỏi bộ chặn merge, nhưng vẫn chạy ở job riêng để biết khi nào nó hết chập chờn. Đặt hạn (ví dụ 2 tuần) rồi sửa hoặc xoá; danh sách cách ly chỉ được phép ngắn.
- **Tái hiện**: `@RepeatedTest(500)` hoặc chạy lặp class trên CI; chạy với `TZ` và `-Duser.timezone` khác, `-Duser.language`/`-Duser.country` khác; chạy class đơn lẻ rồi chạy cùng class nghi ngờ đứng trước nó; bật chạy song song (bài JUnit 5 & 6 chuyên sâu) để lộ state `static`.
- **Awaitility**: `await().atMost(Duration.ofSeconds(5)).pollInterval(Duration.ofMillis(100)).untilAsserted(() -> assertThat(repo.findStatus(id)).isEqualTo(PAID))`. Mặc định Awaitility thăm dò mỗi 100 ms và chờ tối đa 10 giây; assert ném trong lúc chờ được nuốt cho tới khi hết giờ rồi báo lỗi cuối cùng. Kiểm cả "không xảy ra" bằng `during(...)` cẩn thận, vì nó luôn tốn trọn khoảng chờ.
- **Dữ liệu database**: test dựa vào số dòng (`count() == 1`) vỡ khi test khác để lại dữ liệu; kiểm theo dữ liệu chính mình tạo (`findById(id)`), hoặc dọn bảng trước mỗi test (bài Testcontainers, Spring Boot Test).
- **Ngẫu nhiên có chủ đích**: dữ liệu test sinh ngẫu nhiên (Faker, property-based) phải in seed khi fail để tái hiện; jqwik làm sẵn việc này.
- **Số thực, locale, encoding**: `String.format("%.2f", 1234.5)` ra `1234,50` với locale `vi_VN`; so `double` bằng `assertEquals(expected, actual, delta)`; đọc file bằng charset ghi rõ. Lỗi kiểu này trông như chập chờn vì chỉ lộ trên máy có cấu hình khác.
- **Hạ tầng thật sự chập chờn**: kéo image Docker hết lượt, runner thiếu RAM, mạng tới registry. Tách thống kê lỗi hạ tầng khỏi lỗi test, và đừng vội đổ cho hạ tầng: trong phần lớn trường hợp, test hoặc code có một phụ thuộc chưa kiểm soát.
